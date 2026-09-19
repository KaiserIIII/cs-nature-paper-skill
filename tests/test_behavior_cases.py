import json
import unittest
from pathlib import Path


CASES_PATH = Path(__file__).resolve().parents[1] / "assets" / "evals" / "behavior_cases.json"
DEPARTMENTS = {
    "literature",
    "innovation",
    "implementation",
    "figures",
    "writing",
    "validation",
    "review",
}


class BehaviorCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    def test_cases_have_unique_ids_and_complete_rubrics(self):
        cases = self.value["cases"]
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))
        for case in cases:
            self.assertTrue(case["departments"])
            self.assertTrue(set(case["departments"]) <= DEPARTMENTS)
            for field in (
                "prompt",
                "required_behaviors",
                "forbidden_behaviors",
                "required_artifacts",
            ):
                self.assertTrue(case[field], f"{case['id']} lacks {field}")

    def test_all_departments_and_pressure_failures_are_covered(self):
        cases = self.value["cases"]
        covered = {department for case in cases for department in case["departments"]}
        self.assertEqual(covered, DEPARTMENTS)
        pressure_departments = {
            department
            for case in cases
            if case["type"] == "pressure"
            for department in case["departments"]
        }
        self.assertTrue({"literature", "implementation", "figures", "validation", "review"} <= pressure_departments)

    def test_cumcm_pressure_cases_cover_clock_model_and_freeze_failures(self):
        by_id = {case["id"]: case for case in self.value["cases"]}
        expected = {
            "CUMCM-CLOCK-AUTHORITY",
            "CUMCM-COMPLEXITY-PRESSURE",
            "CUMCM-HARD-FREEZE-PRESSURE",
        }

        self.assertTrue(expected <= set(by_id))
        self.assertIn(
            "uses runtime-computed remaining time",
            by_id["CUMCM-CLOCK-AUTHORITY"]["required_behaviors"],
        )
        self.assertIn(
            "guesses the remaining time",
            by_id["CUMCM-CLOCK-AUTHORITY"]["forbidden_behaviors"],
        )
        self.assertIn(
            "starts from the simplest defensible baseline",
            by_id["CUMCM-COMPLEXITY-PRESSURE"]["required_behaviors"],
        )
        self.assertIn(
            "estimates the remaining job runtime and safety margin",
            by_id["CUMCM-HARD-FREEZE-PRESSURE"]["required_behaviors"],
        )


if __name__ == "__main__":
    unittest.main()
