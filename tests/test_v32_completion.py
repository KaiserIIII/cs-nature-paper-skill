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
completion_contract = load("completion_contract")


class CompletionContractTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "paper"
        self.project.mkdir()
        research_state.init_state(self.project, "engineering-system", "maximum-autonomy", "systems")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_maximum_autonomy_init_adds_additive_state_files(self):
        state = self.project / ".research-state"
        self.assertTrue((state / "autonomy_policy.json").exists())
        self.assertTrue((state / "completion_contract.json").exists())
        self.assertTrue((state / "director_session.json").exists())
        self.assertEqual(json.loads((state / "research_contract.json").read_text(encoding="utf-8"))["skill_version"], "3.1.1")

    def test_completion_is_fail_closed_without_scientific_and_audit_evidence(self):
        result = completion_contract.evaluate(self.project)
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("graph", result["checks"])
        self.assertNotEqual(result["release_disposition"], "V3.2.1 RELEASE CANDIDATE READY")
        self.assertTrue(result["critical_failures"])

    def test_completion_rejects_stale_or_wrong_e2e_class(self):
        result = completion_contract.evaluate(self.project, e2e_result=self.project / "e2e.json")
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("e2e" in item.lower() for item in result["critical_failures"]))

    def test_project_completion_uses_submission_semantics(self):
        result = completion_contract.evaluate(self.project)
        self.assertEqual(result["project_disposition"], "BLOCKED")
        self.assertNotIn("RELEASE", result["project_disposition"])

    def test_manuscript_figure_and_review_are_fail_closed(self):
        result = completion_contract.evaluate(self.project)
        for name in ("manuscript_complete", "figure_traceability", "review_resolution", "risk_resolution"):
            self.assertIn(name, result["checks"])
            self.assertEqual(result["checks"][name]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
