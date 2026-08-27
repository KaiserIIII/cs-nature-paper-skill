import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "competition_smoke_run.py"
FIXTURE = ROOT / "assets" / "fixtures" / "cumcm" / "synthetic_problem.json"


class CompetitionE2ETests(unittest.TestCase):
    def test_synthetic_fixture_runs_through_clock_router_graph_and_provenance(self):
        self.assertTrue(RUNNER.exists(), "competition smoke runner is missing")
        self.assertTrue(FIXTURE.exists(), "synthetic CUMCM fixture is missing")
        spec = importlib.util.spec_from_file_location("competition_smoke_run", RUNNER)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        result = module.run()

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["competition"], "CUMCM")
        self.assertEqual(result["evaluation_class"], "HARNESS_SELF_TEST")
        self.assertIn("NOT_RUN", result["model_behavior"])
        self.assertEqual(result["baseline"]["method"], "exhaustive enumeration")
        self.assertEqual(result["baseline"]["selected_site"], "B")
        self.assertEqual(result["execution"]["exit_status"], 0)
        self.assertTrue(result["execution"]["output_sha256"].startswith("sha256:"))
        self.assertEqual(result["clock_checks"]["normal"], "NORMAL")
        self.assertEqual(
            result["clock_checks"]["finalization"], "FINALIZATION_MODE"
        )
        self.assertEqual(result["clock_checks"]["hard_freeze"], "HARD_FREEZE")
        self.assertEqual(result["evidence_validation"], "PASS")
        self.assertGreater(result["graph_events"], 0)
        self.assertEqual(result["graph_validation"], "PASS")


if __name__ == "__main__":
    unittest.main()
