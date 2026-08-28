import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import competition_orchestration_e2e


class CompetitionOrchestrationE2ETests(unittest.TestCase):
    def test_normal_director_reaches_submission_ready_with_real_outputs(self):
        result = competition_orchestration_e2e.run()

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["evaluation_class"], "COMPETITION_ORCHESTRATION_E2E")
        self.assertEqual(result["model_behavior"], "NOT_RUN")
        self.assertEqual(result["selected_problem"], "B")
        self.assertEqual(result["submission_readiness"], "COMPETITION_SUBMISSION_READY")
        self.assertEqual(result["executed_nodes"], 16)
        self.assertEqual(result["ordinary_author_prompts"], 0)
        self.assertEqual(result["automatic_repair"], "PASS")
        self.assertEqual(result["completion_contract"], "PASS")
        self.assertEqual(result["failure_case_count"], 10)
        self.assertTrue(all(value == "PASS" for value in result["failure_cases"].values()))
        self.assertTrue(all(value.startswith("sha256:") for value in result["artifacts"].values()))


if __name__ == "__main__":
    unittest.main()
