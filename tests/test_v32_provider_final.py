import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"provider_final_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ProviderRuntimeContractTests(unittest.TestCase):
    def test_registry_schema_and_template_are_complete(self):
        schema = json.loads((ROOT / "assets" / "schemas" / "provider_registry.schema.json").read_text(encoding="utf-8"))
        template = json.loads((ROOT / "assets" / "templates" / "v3" / "provider_registry.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertTrue(template["providers"])
        required = {
            "provider_id", "type", "capabilities", "input_contract", "output_contract",
            "permissions", "network", "credentials_required", "cost_class",
            "formal_eligible", "checker_required", "qualification", "failure_modes",
        }
        for provider in template["providers"]:
            self.assertTrue(required <= set(provider))

    def test_router_priority_fallback_and_formal_gate(self):
        runtime = load_script("provider_runtime")
        providers = [
            runtime.provider("host", "HOST_LLM", ["analysis"], qualification="QUALIFIED", formal_eligible=True),
            runtime.provider("installed", "EXTERNAL_SKILL", ["analysis"], qualification="QUALIFIED", formal_eligible=True),
            runtime.provider("native", "NATIVE", ["analysis"], qualification="QUALIFIED", formal_eligible=True),
        ]
        result = runtime.resolve_provider("analysis", {}, True, "LOW", {"execute", "local_read"}, providers)
        self.assertEqual(result["provider"]["provider_id"], "native")
        result = runtime.resolve_provider("analysis", {}, True, "LOW", {"execute", "local_read"}, providers[0:2])
        self.assertEqual(result["provider"]["provider_id"], "installed")
        provisional = [runtime.provider("p", "HOST_LLM", ["analysis"], qualification="PROVISIONAL", formal_eligible=True)]
        result = runtime.resolve_provider("analysis", {}, True, "LOW", {"auto_hire"}, provisional)
        self.assertEqual(result["status"], "AUTO_HIRE")
        unavailable = [runtime.provider("n", "NATIVE", ["analysis"], qualification="QUALIFIED", status="UNAVAILABLE")]
        result = runtime.resolve_provider("analysis", {}, False, "LOW", set(), unavailable)
        self.assertEqual(result["status"], "FALLBACK")

    def test_host_output_needs_an_independent_checker(self):
        runtime = load_script("provider_runtime")
        request = runtime.host_request(
            task_id="T1", capability="analysis", purpose="analyze observed output", formal=True,
            inputs=["results.json"], constraints=["no invented values"], required_outputs=["analysis.json"],
            forbidden_claims=["unsupported causality"], evidence_requirements=["source hash"],
            budget={"money": 0}, permissions={"local_read": True},
        )
        output = {
            "status": "PASS", "artifacts": ["analysis.json"], "claims": [], "uncertainties": [],
            "actions_taken": ["read results"], "tool_calls": [], "handoff": {},
        }
        unchecked = runtime.check_host_handoff(request, output, producer_id="host:1", checker_id="host:1")
        limited = runtime.check_host_handoff(request, output, producer_id="host:1", checker_id="host:2")
        self.assertEqual(unchecked["status"], "FAIL")
        self.assertEqual(limited["status"], "PASS")
        self.assertEqual(limited["checker_independence"], "LIMITED")

    def test_freshness_invalidates_downstream_artifacts(self):
        runtime = load_script("provider_runtime")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            upstream = project / "data.csv"
            upstream.write_text("x\n1\n", encoding="utf-8")
            record = runtime.artifact_record(project, project / "result.json", "native", "1", [upstream], [])
            upstream.write_text("x\n2\n", encoding="utf-8")
            self.assertEqual(runtime.check_freshness(project, record)["status"], "STALE")
            graph = {"nodes": [{"id": "formal_experiment", "status": "PASS"}, {"id": "analysis", "status": "PASS", "dependencies": ["formal_experiment"]}, {"id": "writing", "status": "PASS", "dependencies": ["analysis"]}]}
            changed = runtime.invalidate_downstream(graph, "formal_experiment")
            self.assertEqual(changed, ["analysis", "writing"])
            self.assertEqual(graph["nodes"][1]["status"], "STALE")


class SkillDiscoveryProviderTests(unittest.TestCase):
    def _candidate(self, **changes):
        value = {
            "id": "stats-worker", "repo": "example/stats-worker", "repo_url": "https://github.com/example/stats-worker.git",
            "exact_ref": "a" * 40, "license": "MIT", "capabilities": ["statistical-analysis"],
            "files": {"SKILL.md": "---\nname: stats-worker\ndescription: Analyze data.\n---\n", "LICENSE": "MIT License"},
            "dependencies": [], "credentials": False, "network_runtime": False, "external_writes": False,
            "install_hooks": False, "system_writes": False, "tests": True, "maintainer_activity": "ACTIVE",
        }
        value.update(changes)
        return value

    def test_vacancy_drives_mocked_github_discovery_and_exact_pin(self):
        discovery = load_script("skill_discovery_provider")

        class Backend:
            def search(self, query):
                self.query = query
                return [self_candidate]

        self_candidate = self._candidate()
        backend = Backend()
        result = discovery.discover_capability("statistical-analysis", backends=[backend])
        self.assertEqual(result["status"], "PASS")
        self.assertIn("statistical-analysis", backend.query)
        self.assertEqual(result["candidates"][0]["exact_ref"], "a" * 40)

    def test_mutable_ref_unsafe_license_and_dangerous_hook_fail_closed(self):
        discovery = load_script("skill_discovery_provider")
        self.assertEqual(discovery.static_audit(self._candidate(exact_ref="main"))["status"], "FAIL")
        self.assertEqual(discovery.static_audit(self._candidate(license="UNKNOWN"))["status"], "FAIL")
        hook = discovery.static_audit(self._candidate(install_hooks=True))
        self.assertEqual(hook["risk"], "HIGH")
        self.assertEqual(hook["authorization"], "ASK_AUTHOR")

    def test_low_materializes_medium_logs_and_high_stops(self):
        discovery = load_script("skill_discovery_provider")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            source = Path(tmp) / "source"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: stats-worker\ndescription: Analyze data.\n---\n", encoding="utf-8")
            low = self._candidate(source_path=str(source))
            low_result = discovery.materialize(project, low)
            self.assertEqual(low_result["status"], "MATERIALIZED")
            self.assertTrue(Path(low_result["path"]).is_dir())
            medium = discovery.static_audit(self._candidate(network_runtime=True))
            self.assertEqual((medium["risk"], medium["authorization"]), ("MEDIUM", "AUTO_WITH_AUDIT"))
            high = discovery.static_audit(self._candidate(credentials=True))
            self.assertEqual((high["risk"], high["authorization"]), ("HIGH", "ASK_AUTHOR"))

    def test_missing_capability_runs_discovery_through_acceptance(self):
        marketplace = load_script("skill_marketplace_runtime")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            source = Path(tmp) / "source"
            project.mkdir()
            source.mkdir()
            (source / "SKILL.md").write_text("---\nname: stats-worker\ndescription: Analyze data.\n---\n", encoding="utf-8")
            (source / "worker.py").write_text(
                "import json,sys\nfrom pathlib import Path\n"
                "value=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))\n"
                "Path(sys.argv[2]).write_text(json.dumps({'checked_value': value['value'] * 2}), encoding='utf-8')\n",
                encoding="utf-8",
            )
            candidate = self._candidate(source_path=str(source), entrypoint="worker.py")

            class Backend:
                def search(self, query):
                    return [candidate]

            policy = json.loads((ROOT / "assets" / "templates" / "v3" / "autonomy_policy.json").read_text(encoding="utf-8"))
            result = marketplace.auto_hire_missing_capability(
                project, "statistical-analysis", {"value": 4}, policy=policy, discovery_backends=[Backend()]
            )
            self.assertEqual(result["status"], "ACCEPTED")
            self.assertEqual(result["result"]["checked_value"], 8)
            self.assertEqual(result["provider_lifecycle"], ["DISCOVERY", "AUDIT", "PIN", "MATERIALIZE", "QUALIFY", "EXECUTE", "CHECK", "ACCEPT"])


class GenericExecutionTests(unittest.TestCase):
    def test_generic_research_orchestration_uses_input_derived_results(self):
        harness = load_script("generic_research_orchestration_e2e")
        result = harness.run()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["evaluation_class"], "GENERIC_RESEARCH_ORCHESTRATION_E2E")
        self.assertEqual(result["ordinary_author_prompts"], 0)
        self.assertEqual(result["model_behavior"], "NOT_RUN")
        self.assertTrue(result["actual_command"]["exit_status"] == 0)
        self.assertTrue(result["input_derived"])
        self.assertEqual(result["review_repair"], "PASS")
        self.assertNotEqual(result["provider_id"], "native-fixture")

    def test_generic_competition_provider_covers_three_structural_families(self):
        harness = load_script("generic_competition_orchestration_e2e")
        result = harness.run()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["evaluation_class"], "GENERIC_COMPETITION_ORCHESTRATION_E2E")
        self.assertEqual(set(result["fixtures"]), {"A", "B", "C"})
        self.assertTrue(all(item["status"] == "PASS" for item in result["fixtures"].values()))
        self.assertIn("optimization", result["fixtures"]["A"]["families"])
        self.assertIn("clustering", result["fixtures"]["B"]["families"])
        self.assertTrue({"simulation", "ode"} & set(result["fixtures"]["C"]["families"]))
        self.assertTrue(all(item["actual_execution"]["exit_status"] == 0 for item in result["fixtures"].values()))

    def test_production_modules_do_not_embed_old_fixtures(self):
        forbidden_research = ("deterministic fixture", "evidence-bound autonomous research fixture")
        forbidden_competition = ("demand_history", "fixed_cost", "selected_site", "CUMCM 合成赛题论文")
        for name in ("research_executor.py", "literature_provider.py", "coding_provider.py", "analysis_provider.py", "writing_provider.py", "review_provider.py"):
            text = ((ROOT / "scripts" / name) if name == "research_executor.py" else (ROOT / "providers" / name)).read_text(encoding="utf-8")
            self.assertFalse(any(token in text for token in forbidden_research), name)
        for name in ("competition_executor.py", "competition_modeling_provider.py", "competition_coding_provider.py", "competition_analysis_provider.py", "competition_writing_provider.py"):
            text = ((ROOT / "scripts" / name) if name == "competition_executor.py" else (ROOT / "providers" / name)).read_text(encoding="utf-8")
            self.assertFalse(any(token in text for token in forbidden_competition), name)
        self.assertTrue((ROOT / "providers" / "native_fixture_provider.py").is_file())
        self.assertTrue((ROOT / "providers" / "competition_fixture_provider.py").is_file())


if __name__ == "__main__":
    unittest.main()
