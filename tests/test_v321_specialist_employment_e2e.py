import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"employment_e2e_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class SpecialistEmploymentE2ETests(unittest.TestCase):
    def _candidate(self, source: Path, capability: str, **changes):
        tokens = capability.replace("-", " ")
        (source / "SKILL.md").write_text(
            f"---\nname: audited-specialist\ndescription: {tokens} worker for formal research.\n---\n",
            encoding="utf-8",
        )
        (source / "worker.py").write_text(
            "import json, sys\n"
            "from pathlib import Path\n"
            "payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))\n"
            "Path(sys.argv[2]).write_text(json.dumps({'external_value': payload.get('node', 'missing')}), encoding='utf-8')\n",
            encoding="utf-8",
        )
        value = {
            "id": "audited-specialist",
            "repo": "fixture/audited-specialist",
            "repo_url": "https://github.com/fixture/audited-specialist.git",
            "exact_ref": "a" * 40,
            "license": "MIT",
            "license_compatible": True,
            "capabilities": [capability],
            "files": {
                "SKILL.md": (source / "SKILL.md").read_text(encoding="utf-8"),
                "worker.py": (source / "worker.py").read_text(encoding="utf-8"),
            },
            "source_path": str(source),
            "entrypoint": "worker.py",
            "semantic_audit": {
                "status": "CONFIRMED",
                "actor": "fixture-independent-auditor",
                "evidence": ["SKILL.md", "worker.py"],
            },
            "behavior_trial": {
                "status": "PASS",
                "checker": "fixture-checker",
                "output_contract": "PASS",
            },
            "dependencies": [],
            "credentials": False,
            "network_runtime": False,
            "external_writes": False,
            "install_hooks": False,
            "system_writes": False,
            "tests": True,
        }
        value.update(changes)
        return value

    def _research_project(self, root: Path):
        state = load("research_state")
        project = root / "paper"
        project.mkdir()
        state.init_state(project, "empirical", "maximum-autonomy", "machine-learning")
        (project / "inputs").mkdir()
        (project / "inputs" / "research_brief.json").write_text(
            json.dumps({"question": "formal evidence-bound writing", "load_bearing_nodes": ["writing"]}),
            encoding="utf-8",
        )
        return project

    def _competition_project(self, root: Path):
        state = load("research_state")
        project = root / "contest"
        project.mkdir()
        state.init_state(project, "algorithmic", "competition-autopilot", "mathematical-modeling")
        (project / ".research-state" / "competition_input.json").write_text(
            json.dumps({
                "competition": "Fixture Contest",
                "specialist_nodes": ["model_validation"],
                "problems": [{"id": "Q1", "questions": [{"id": "Q1", "goal": "validate a model"}]}],
            }),
            encoding="utf-8",
        )
        return project

    def test_research_successful_hire_re_resolves_and_executes_external_skill(self):
        executor = load("research_executor")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = self._research_project(root)
            source = root / "candidate"
            source.mkdir()
            candidate = self._candidate(source, "evidence-bound-writing")
            discovery = {"operation": "skill-discovery", "status": "PASS", "capability": "evidence-bound-writing", "candidates": [candidate]}
            with patch.object(executor.skill_discovery_provider, "discover_capability", return_value=discovery) as discover, \
                 patch.object(executor.host_research_provider, "request_or_consume", side_effect=AssertionError("Host must not execute after successful hire")):
                result = executor.execute_node(project, "writing")

            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["provider_route"]["provider"]["type"], "EXTERNAL_SKILL")
            self.assertEqual(result["provider_route"]["provider"]["provider_id"], "audited-specialist")
            self.assertEqual(result["specialist_hire"]["status"], "ACCEPTED")
            self.assertEqual(discover.call_count, 1)
            self.assertTrue(any(stage in result["specialist_hire"]["provider_lifecycle"] for stage in ("QUALIFY", "EXECUTE", "CHECK", "ACCEPT")))
            self.assertEqual(
                result["employment_lifecycle"],
                [
                    "SPECIALIST_DISCOVERY", "AUTO_HIRE", "CONFIRMED", "STATIC_AUDITED",
                    "PINNED", "MATERIALIZED", "BEHAVIOR_TESTED", "QUALIFIED", "EMPLOYED",
                    "RE-RESOLVE", "EXTERNAL_SKILL_EXECUTED", "CHECKED", "ACCEPTED",
                ],
            )
            employee = json.loads((project / ".research-state" / "employee_registry.json").read_text(encoding="utf-8"))
            record = next(item for item in employee["employees"] if item.get("id") == "audited-specialist")
            self.assertEqual(record["qualification_state"], "FORMAL_QUALIFIED")
            self.assertEqual(record["exact_ref"], "a" * 40)
            self.assertEqual(result["provider_route"]["provider"]["type"], "EXTERNAL_SKILL")
            self.assertTrue((project / ".research-state" / ".autonomy-audit.jsonl").is_file())
            self.assertIn("audited-specialist", (project / ".research-state" / "decision_log.md").read_text(encoding="utf-8"))
            provider_registry = json.loads((project / ".research-state" / "provider_registry.json").read_text(encoding="utf-8"))
            self.assertTrue(any(item.get("provider_id") == "audited-specialist" and item.get("type") == "EXTERNAL_SKILL" for item in provider_registry["providers"]))
            registry_checker = load("employee_registry")
            self.assertEqual(registry_checker.audit_registry(employee)["status"], "PASS")

    def test_audit_failure_falls_back_without_employment(self):
        executor = load("research_executor")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = self._research_project(root)
            source = root / "candidate"
            source.mkdir()
            candidate = self._candidate(source, "evidence-bound-writing", license="UNKNOWN")
            discovery = {"operation": "skill-discovery", "status": "PASS", "capability": "evidence-bound-writing", "candidates": [candidate]}
            with patch.object(executor.skill_discovery_provider, "discover_capability", return_value=discovery):
                result = executor.execute_node(project, "writing")
            self.assertEqual(result["status"], "HOST_EXECUTION_REQUIRED")
            self.assertEqual(result["specialist_hire"]["status"], "BLOCKED")
            self.assertIn("audited-specialist", json.dumps(result["specialist_hire"]))
            self.assertIn("REJECTED", (project / ".research-state" / "specialist_hire.json").read_text(encoding="utf-8"))
            employee = json.loads((project / ".research-state" / "employee_registry.json").read_text(encoding="utf-8"))
            self.assertFalse(any(item.get("id") == "audited-specialist" for item in employee["employees"]))

    def test_partial_capability_is_rejected_and_falls_back(self):
        executor = load("research_executor")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = self._research_project(root)
            source = root / "candidate"
            source.mkdir()
            candidate = self._candidate(source, "evidence-bound-writing", semantic_audit={"status": "PARTIAL", "actor": "fixture", "evidence": ["SKILL.md"]})
            discovery = {"operation": "skill-discovery", "status": "PASS", "capability": "evidence-bound-writing", "candidates": [candidate]}
            with patch.object(executor.skill_discovery_provider, "discover_capability", return_value=discovery):
                result = executor.execute_node(project, "writing")
            self.assertEqual(result["status"], "HOST_EXECUTION_REQUIRED")
            self.assertEqual(result["specialist_hire"]["status"], "BLOCKED")

    def test_failed_behavior_trial_is_rejected_and_falls_back(self):
        executor = load("research_executor")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = self._research_project(root)
            source = root / "candidate"
            source.mkdir()
            candidate = self._candidate(source, "evidence-bound-writing", behavior_trial={"status": "FAIL", "checker": "fixture", "output_contract": "FAIL"})
            discovery = {"operation": "skill-discovery", "status": "PASS", "capability": "evidence-bound-writing", "candidates": [candidate]}
            with patch.object(executor.skill_discovery_provider, "discover_capability", return_value=discovery):
                result = executor.execute_node(project, "writing")
            self.assertEqual(result["status"], "HOST_EXECUTION_REQUIRED")
            self.assertEqual(result["specialist_hire"]["status"], "BLOCKED")

    def test_auto_hire_disabled_uses_host_without_installation(self):
        executor = load("research_executor")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = self._research_project(root)
            policy_path = project / ".research-state" / "autonomy_policy.json"
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            policy["permissions"]["auto_hire"] = False
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            source = root / "candidate"
            source.mkdir()
            candidate = self._candidate(source, "evidence-bound-writing")
            discovery = {"operation": "skill-discovery", "status": "PASS", "capability": "evidence-bound-writing", "candidates": [candidate]}
            with patch.object(executor.skill_discovery_provider, "discover_capability", return_value=discovery) as discover:
                result = executor.execute_node(project, "writing")
            self.assertEqual(result["status"], "HOST_EXECUTION_REQUIRED")
            self.assertEqual(discover.call_count, 1)
            employee = json.loads((project / ".research-state" / "employee_registry.json").read_text(encoding="utf-8"))
            self.assertFalse(employee["employees"])

    def test_installed_specialist_skips_discovery_and_rehire(self):
        executor = load("research_executor")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = self._research_project(root)
            source = root / "candidate"
            source.mkdir()
            candidate = self._candidate(source, "evidence-bound-writing")
            discovery = {"operation": "skill-discovery", "status": "PASS", "capability": "evidence-bound-writing", "candidates": [candidate]}
            with patch.object(executor.skill_discovery_provider, "discover_capability", return_value=discovery) as discover:
                first = executor.execute_node(project, "writing")
                second = executor.execute_node(project, "writing")
            self.assertEqual(first["status"], "PASS")
            self.assertEqual(second["status"], "PASS")
            self.assertEqual(second["provider_route"]["provider"]["type"], "EXTERNAL_SKILL")
            self.assertEqual(discover.call_count, 1)

    def test_competition_successful_hire_re_resolves_and_executes_external_skill(self):
        executor = load("competition_executor")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = self._competition_project(root)
            source = root / "candidate"
            source.mkdir()
            candidate = self._candidate(source, "model-validation")
            discovery = {"operation": "skill-discovery", "status": "PASS", "capability": "model-validation", "candidates": [candidate]}
            with patch.object(executor.skill_discovery_provider, "discover_capability", return_value=discovery) as discover, \
                 patch.object(executor.competition_host_provider, "request_specialist", side_effect=AssertionError("Host must not execute after successful hire")):
                result = executor.execute_node(project, "model_validation")
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["provider_route"]["provider"]["type"], "EXTERNAL_SKILL")
            self.assertEqual(result["provider_route"]["provider"]["provider_id"], "audited-specialist")
            self.assertEqual(result["specialist_hire"]["status"], "ACCEPTED")
            self.assertEqual(discover.call_count, 1)
            self.assertIn("EMPLOYED", result["employment_lifecycle"])
            self.assertIn("EXTERNAL_SKILL_EXECUTED", result["employment_lifecycle"])


if __name__ == "__main__":
    unittest.main()
