import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


research_state = load("research_state")


def seed(project):
    inputs = project / "inputs"
    inputs.mkdir()
    (inputs / "research_brief.json").write_text(
        json.dumps(
            {
                "title": "Deterministic provenance study",
                "question": "Does a deterministic fixture preserve output provenance?",
                "scope": "public synthetic fixture only",
                "source_title": "Synthetic provenance source",
                "provider_mode": "fixture",
            }
        ),
        encoding="utf-8",
    )
    (inputs / "literature_source.txt").write_text(
        "Deterministic execution records connect commands to content-addressed outputs.\n",
        encoding="utf-8",
    )


class ResearchExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "paper"
        self.project.mkdir()
        research_state.init_state(self.project, "engineering-system", "maximum-autonomy", "systems")
        seed(self.project)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_director_executes_nodes_and_reaches_submission_ready(self):
        director = load("director_loop")
        result = director.run(self.project, max_iterations=40, now="2026-08-28T00:00:00Z")
        self.assertEqual(result["status"], "READY_FOR_SUBMISSION")
        self.assertEqual(result["ordinary_author_prompts"], 0)
        for relative in (
            "artifacts/literature.json",
            "experiments/run_experiment.py",
            "artifacts/formal_results.json",
            "artifacts/analysis.json",
            "artifacts/figure.svg",
            "artifacts/manuscript.md",
            "artifacts/review_findings.json",
            "artifacts/package_manifest.json",
        ):
            self.assertTrue((self.project / relative).exists(), relative)
        execution = json.loads((self.project / "artifacts" / "formal_execution.json").read_text(encoding="utf-8"))
        self.assertEqual(execution["exit_status"], 0)
        self.assertTrue(execution["outputs"][0]["produced_by_command"])

    def test_implementation_repairs_invalid_existing_code(self):
        executor = load("research_executor")
        implementation = self.project / "experiments" / "run_experiment.py"
        implementation.parent.mkdir()
        implementation.write_text("this is invalid python !!!", encoding="utf-8")
        result = executor.execute_node(self.project, "implementation")
        self.assertEqual(result["status"], "PASS")
        self.assertIn("repaired_invalid_implementation", result["actions"])
        self.assertIn("changed_files", result)

    def test_repeated_identical_failure_is_bounded_per_node(self):
        director = load("director_loop")
        decisions = [
            director.recovery_decision(self.project, "implementation", "SyntaxError:same", previous_result="FAIL")
            for _ in range(4)
        ]
        self.assertEqual(decisions[0]["strategy"], "REPAIR")
        self.assertEqual(decisions[-1]["status"], "BLOCKED")
        self.assertEqual(decisions[-1]["reason"], "repeated identical failure")

    def test_full_paper_harness_uses_normal_director_runtime(self):
        text = (ROOT / "scripts" / "full_paper_e2e.py").read_text(encoding="utf-8")
        self.assertNotIn("_fill_contract", text)
        self.assertNotIn("_advance_graph", text)
        harness = load("full_paper_e2e")
        result = harness.run(root=self.project / "harness")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["evaluation_class"], "HARNESS_SELF_TEST")
        self.assertEqual(result["director_orchestration"]["evaluation_class"], "DIRECTOR_ORCHESTRATION_E2E")
        self.assertEqual(result["director_orchestration"]["status"], "PASS")
        self.assertEqual(result["model_behavior"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
