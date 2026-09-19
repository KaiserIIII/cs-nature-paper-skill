import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PROVIDERS = ROOT / "providers"
for folder in (str(SCRIPTS), str(PROVIDERS)):
    if folder not in sys.path:
        sys.path.insert(0, folder)


def load_script(name):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"host_generalization_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_provider(name):
    path = PROVIDERS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"host_generalization_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def request(task_id="T1", node="implementation", capability="code-generation"):
    return {
        "task_id": task_id,
        "node": node,
        "capability": capability,
        "formal": False,
        "inputs": ["inputs/research_brief.json"],
        "constraints": ["use project evidence"],
        "required_outputs": ["problem-specific code", "execution contract"],
        "evidence_requirements": ["artifact hash", "independent checker"],
        "forbidden_claims": ["unexecuted code works"],
        "permissions": {"local_read": True, "local_write": True, "execute": True},
        "budget": {"money": 0},
    }


def handoff(task_id="T1", artifact="src/model.py", provider_id="recorded-host"):
    return {
        "task_id": task_id,
        "provider_id": provider_id,
        "status": "PASS",
        "artifacts": [artifact],
        "claims": [],
        "uncertainties": ["recorded handoff is not a live model evaluation"],
        "actions_taken": ["inspected repository", "created problem-specific code"],
        "tool_calls": [{"kind": "write", "path": artifact}],
        "commands": [
            {
                "argv": ["{python}", artifact],
                "cwd": ".",
                "expected_outputs": [],
            }
        ],
        "checker_notes": ["syntax and artifact containment must be checked independently"],
        "changed_files": [artifact],
        "entrypoint": artifact,
        "config": None,
        "tests": ["python -m py_compile " + artifact],
        "expected_outputs": [],
        "limitations": ["recorded deterministic fixture for lifecycle validation"],
    }


class HostProviderLifecycleTests(unittest.TestCase):
    def test_host_llm_cannot_pass_without_a_received_handoff(self):
        runtime = load_script("host_provider_runtime")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            created = runtime.create_request(project, request())
            self.assertEqual(created["status"], "HOST_EXECUTION_REQUIRED")
            self.assertEqual(created["state"], "HOST_EXECUTION_REQUIRED")
            unresolved = runtime.resolve(project, "T1")
            self.assertEqual(unresolved["status"], "HOST_EXECUTION_REQUIRED")
            self.assertNotEqual(unresolved["status"], "PASS")

    def test_recorded_handoff_runs_receive_check_accept_lifecycle(self):
        runtime = load_script("host_provider_runtime")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            runtime.create_request(project, request())
            artifact = project / "src" / "model.py"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("print('observed')\n", encoding="utf-8")
            received = runtime.receive(project, handoff())
            self.assertEqual(received["state"], "HOST_HANDOFF_RECEIVED")
            accepted = runtime.check(project, "T1", checker_id="deterministic-output-checker")
            self.assertEqual(accepted["status"], "ACCEPTED")
            self.assertEqual(accepted["state"], "ACCEPTED")
            self.assertEqual(runtime.resolve(project, "T1")["status"], "ACCEPTED")
            self.assertEqual(
                accepted["lifecycle"],
                ["REQUEST_CREATED", "HOST_EXECUTION_REQUIRED", "HOST_HANDOFF_RECEIVED", "CHECKING", "ACCEPTED"],
            )

    def test_invalid_or_self_checked_handoff_is_rejected(self):
        runtime = load_script("host_provider_runtime")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            runtime.create_request(project, request())
            artifact = project / "src" / "model.py"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("print('observed')\n", encoding="utf-8")
            value = handoff(provider_id="same-host")
            value["commands"] = []
            received = runtime.receive(project, value)
            self.assertEqual(received["state"], "HOST_HANDOFF_RECEIVED")
            rejected = runtime.check(project, "T1", checker_id="same-host")
            self.assertEqual(rejected["status"], "REJECTED")

    def test_rejected_handoff_can_be_corrected_without_abandoning_running_node(self):
        runtime = load_script("host_provider_runtime")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            runtime.create_request(project, request())
            artifact = project / "src" / "model.py"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("print('observed')\n", encoding="utf-8")
            invalid = handoff(provider_id="same-host")
            invalid["commands"] = []
            runtime.receive(project, invalid)
            self.assertEqual(runtime.check(project, "T1", checker_id="same-host")["status"], "REJECTED")
            corrected = runtime.receive(project, handoff(provider_id="recorded-host"))
            self.assertEqual(corrected["state"], "HOST_HANDOFF_RECEIVED")
            accepted = runtime.check(project, "T1", checker_id="deterministic-output-checker")
            self.assertEqual(accepted["status"], "ACCEPTED")

    def test_host_unavailable_triggers_auto_hire_instead_of_fake_output(self):
        provider = load_script("provider_runtime")
        candidates = [
            provider.provider(
                "host-code", "HOST_LLM", ["code-generation"],
                status="UNAVAILABLE", qualification="HOST_REQUEST_CAPABLE",
            )
        ]
        result = provider.resolve_provider(
            "code-generation", {}, True, "LOW", {"auto_hire"}, candidates
        )
        self.assertEqual(result["status"], "AUTO_HIRE")

    def test_accepted_code_change_reopens_completed_descendants(self):
        runtime = load_script("host_provider_runtime")
        state = load_script("research_state")
        director = load_script("director_loop")
        graph = load_script("research_graph")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            state.init_state(project, "engineering-system", "maximum-autonomy", "systems")
            inputs = project / "inputs"
            inputs.mkdir()
            (inputs / "research_brief.json").write_text(json.dumps({
                "question": "Does the fixture preserve dependency invalidation?",
                "provider_mode": "fixture",
            }), encoding="utf-8")
            (inputs / "literature_source.txt").write_text(
                "Recorded fixture source for dependency invalidation.\n", encoding="utf-8"
            )
            complete = director.run(project, max_iterations=40, now="2026-08-29T00:00:00Z")
            self.assertEqual(complete["status"], "READY_FOR_SUBMISSION")
            runtime.create_request(project, request(task_id="CHANGE-1"))
            artifact = project / "src" / "model.py"
            artifact.parent.mkdir(parents=True)
            artifact.write_text("print('changed')\n", encoding="utf-8")
            runtime.receive(project, handoff(task_id="CHANGE-1"))
            accepted = runtime.check(project, "CHANGE-1", checker_id="deterministic-output-checker")
            self.assertEqual(accepted["status"], "ACCEPTED")
            statuses = {item["id"]: item["status"] for item in graph.load_graph(project)[1]["nodes"]}
            for node in ("formal_experiment", "analysis", "figures", "writing", "review"):
                self.assertEqual(statuses[node], "REOPENED", node)


class GeneralizationRoutingTests(unittest.TestCase):
    def test_native_unsupported_research_routes_to_host_request(self):
        state = load_script("research_state")
        executor = load_script("research_executor")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            state.init_state(project, "ml-benchmark", "maximum-autonomy", "machine-learning")
            inputs = project / "inputs"
            inputs.mkdir()
            (inputs / "research_brief.json").write_text(json.dumps({
                "question": "Can a classifier separate the two observed classes?",
                "domain": "machine learning",
                "study_type": "ml-benchmark",
                "data_file": "inputs/classes.csv",
                "outcome": "label",
                "method_candidates": ["classification"],
            }), encoding="utf-8")
            (inputs / "classes.csv").write_text("x,label\n0,0\n1,0\n8,1\n9,1\n", encoding="utf-8")
            result = executor.execute_node(project, "implementation")
            self.assertEqual(result["status"], "HOST_EXECUTION_REQUIRED")
            self.assertTrue(result["host_request_created"])
            self.assertFalse((project / "experiments" / "run_research.py").exists())

    def test_native_unsupported_competition_routes_to_host_modeling(self):
        state = load_script("research_state")
        executor = load_script("competition_executor")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            state.init_state(project, "algorithmic", "competition-autopilot", "mathematical-modeling")
            state_dir = project / ".research-state"
            source = {
                "competition": "Generic Contest",
                "problems": [{
                    "id": "GRAPH",
                    "title": "Network routing",
                    "questions": [{"id": "Q1", "goal": "Find a shortest path in a weighted graph."}],
                }],
            }
            (state_dir / "competition_input.json").write_text(json.dumps(source), encoding="utf-8")
            (state_dir / "competition_state.json").write_text(json.dumps({
                "modeling_plan": [{
                    "question_id": "Q1", "routing_status": "UNRESOLVED",
                    "candidate_families": [], "problem_formulation": "shortest path",
                }]
            }), encoding="utf-8")
            result = executor.execute_node(project, "method_candidates")
            self.assertEqual(result["status"], "HOST_EXECUTION_REQUIRED")
            self.assertEqual(result["capability"], "competition-modeling")

    def test_host_research_and_competition_recorded_e2es_execute_real_code(self):
        research = load_script("generic_host_research_e2e").run()
        competition = load_script("generic_host_competition_e2e").run()
        for result in (research, competition):
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["host_request_created"])
            self.assertTrue(result["host_handoff_received"])
            self.assertTrue(result["deterministic_execution"])
            self.assertEqual(result["checker"], "PASS")
            self.assertEqual(result["ordinary_author_prompts"], 0)
            self.assertEqual(result["model_behavior"], "RECORDED_HANDOFF")


class CapabilityVerificationTests(unittest.TestCase):
    def test_search_hit_unrelated_skill_is_mismatch(self):
        discovery = load_script("skill_discovery_provider")
        candidate = {
            "files": {"SKILL.md": "---\nname: image-helper\ndescription: Resize images.\n---\n"},
            "behavior_trial": {"status": "PASS"},
        }
        result = discovery.verify_capability(candidate, "statistical-analysis")
        self.assertEqual(result["status"], "MISMATCH")

    def test_partial_mention_is_not_formally_qualified(self):
        discovery = load_script("skill_discovery_provider")
        candidate = {
            "files": {"README.md": "This helper prints an analysis summary."},
            "behavior_trial": {"status": "PASS"},
        }
        result = discovery.verify_capability(candidate, "statistical-analysis")
        self.assertEqual(result["status"], "PARTIAL")
        self.assertFalse(result["formal_eligible"])

    def test_clear_declaration_semantic_audit_and_behavior_trial_confirm(self):
        discovery = load_script("skill_discovery_provider")
        candidate = {
            "files": {
                "SKILL.md": "---\nname: stats\ndescription: Perform statistical analysis on supplied datasets.\n---\n",
                "tests/test_worker.py": "def test_statistical_analysis_output_contract(): pass\n",
                "worker.py": "def statistical_analysis(data): return {'status': 'PASS'}\n",
            },
            "semantic_audit": {
                "status": "CONFIRMED",
                "actor": "host-semantic-audit:1",
                "evidence": ["SKILL.md", "tests/test_worker.py", "worker.py"],
            },
            "behavior_trial": {
                "status": "PASS", "checker": "deterministic-output-checker",
                "output_contract": "PASS",
            },
        }
        result = discovery.verify_capability(candidate, "statistical-analysis")
        self.assertEqual(result["status"], "CONFIRMED")
        self.assertTrue(result["formal_eligible"])


class LiteratureSufficiencyTests(unittest.TestCase):
    def test_metadata_only_is_not_load_bearing_eligible(self):
        literature = load_provider("literature_provider")
        record = literature.classify_retrieval({
            "stable_identifier": "10.1/example", "identity": "VERIFIED_METADATA",
            "retrieved": False, "exact_region": "UNRESOLVED",
        })
        self.assertEqual(record["retrieval_status"], "METADATA_ONLY")
        self.assertFalse(record["load_bearing_eligible"])

    def test_full_text_without_exact_region_is_not_verified(self):
        literature = load_provider("literature_provider")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "paper.txt"
            source.write_text("one\ntwo\nthree\n", encoding="utf-8")
            record = literature.classify_retrieval({
                "stable_identifier": "local:paper", "identity": "VERIFIED_LOCAL",
                "full_text_path": str(source), "exact_region": "UNRESOLVED",
            })
            self.assertEqual(record["retrieval_status"], "FULLTEXT_RETRIEVED")
            self.assertFalse(record["load_bearing_eligible"])

    def test_full_text_exact_region_and_independent_checker_are_eligible(self):
        literature = load_provider("literature_provider")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "paper.txt"
            source.write_text("one\nverified method claim\nthree\n", encoding="utf-8")
            record = literature.classify_retrieval({
                "stable_identifier": "local:paper", "identity": "VERIFIED_LOCAL",
                "full_text_path": str(source), "exact_region": "line 2",
                "inspection_actor": "literature-producer", "checker": "literature-checker",
            })
            self.assertEqual(record["retrieval_status"], "EXACT_REGION_VERIFIED")
            self.assertTrue(record["load_bearing_eligible"])
            self.assertTrue(record["region_sha256"].startswith("sha256:"))

    def test_metadata_only_novelty_claim_blocks_completion(self):
        completion = load_script("completion_contract")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            artifact = project / "artifacts" / "literature.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(json.dumps({
                "load_bearing_claims": [{"claim_id": "NOVELTY-1", "kind": "novelty"}],
                "retrieval_records": [{
                    "claim_id": "NOVELTY-1", "retrieval_status": "METADATA_ONLY",
                    "load_bearing_eligible": False,
                }],
                "claim_relations": [{
                    "claim_id": "NOVELTY-1", "relation": "BACKGROUND_ONLY",
                    "verification_status": "NOT_VERIFIED",
                }],
            }), encoding="utf-8")
            result = completion.literature_sufficiency(project)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["novelty_status"], "CONDITIONAL")

    def test_exact_region_verified_load_bearing_claim_may_pass_completion(self):
        completion = load_script("completion_contract")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            artifact = project / "artifacts" / "literature.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(json.dumps({
                "load_bearing_claims": [{"claim_id": "NOVELTY-1", "kind": "novelty"}],
                "retrieval_records": [{
                    "source_id": "S1", "retrieval_status": "EXACT_REGION_VERIFIED",
                    "load_bearing_eligible": True,
                }],
                "claim_relations": [{
                    "claim_id": "NOVELTY-1", "source_id": "S1", "relation": "SUPPORTS",
                    "verification_status": "EXACT_REGION_VERIFIED",
                }],
            }), encoding="utf-8")
            result = completion.literature_sufficiency(project)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["novelty_status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
