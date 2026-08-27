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
director_loop = load("director_loop")
dashboard = load("dashboard")


class DirectorLoopTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.project = Path(self.tempdir.name) / "paper"
        self.project.mkdir()
        research_state.init_state(self.project, "engineering-system", "maximum-autonomy", "systems")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_director_persists_session_and_resumes_same_policy_and_graph(self):
        first = director_loop.run(self.project, max_iterations=1, now="2026-08-28T00:00:00Z")
        self.assertIn(first["status"], {"PAUSED", "BLOCKED", "PASS"})
        self.assertTrue((self.project / ".research-state" / "director_session.json").exists())
        second = director_loop.resume(self.project, now="2026-08-28T00:00:01Z")
        self.assertEqual(second["session_id"], first["session_id"])

    def test_director_refuses_policy_or_graph_identity_drift(self):
        director_loop.run(self.project, max_iterations=1, now="2026-08-28T00:00:00Z")
        policy_path = self.project / ".research-state" / "autonomy_policy.json"
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        policy["risk_cap"] = "LOW"
        policy_path.write_text(json.dumps(policy), encoding="utf-8")
        self.assertEqual(director_loop.resume(self.project)["status"], "BLOCKED")

    def test_recovery_reopens_failed_node_without_claiming_pass(self):
        result = director_loop.recover(self.project, "implementation", reason="job exit 1")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["to"], "REOPENED")
        self.assertNotEqual(result["to"], "PASS")

    def test_recovery_budget_blocks_repeated_attempts(self):
        for _ in range(3):
            director_loop.recover(self.project, "implementation", reason="job exit 1")
        result = director_loop.recover(self.project, "implementation", reason="job exit 1")
        self.assertEqual(result["status"], "BLOCKED")

    def test_dashboard_exposes_v32_projection_without_mutating_state(self):
        before = (self.project / ".research-state" / "director_session.json").read_bytes()
        value = dashboard.build(self.project)
        self.assertIn("AUTONOMY", value)
        self.assertIn("COMPLETION", value)
        self.assertEqual(before, (self.project / ".research-state" / "director_session.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
