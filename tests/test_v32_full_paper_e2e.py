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


full_paper_e2e = load("full_paper_e2e")


class FullPaperE2ETests(unittest.TestCase):
    def test_full_paper_e2e_is_a_real_harness_self_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "paper"
            project.mkdir()
            result = full_paper_e2e.run(root=project)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["evaluation_class"], "HARNESS_SELF_TEST")
            self.assertEqual(result["model_behavior"], "NOT_RUN")
            self.assertGreaterEqual(result["anchor_count"], 1)
            self.assertEqual(result["completion"]["status"], "PASS")
            self.assertTrue(result["execution_record"]["outputs"][0]["produced_by_command"])
            self.assertNotIn(".v32-e2e-", json.dumps(result))

    def test_full_paper_e2e_semantic_result_is_repeatable_and_stale_commit_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "paper"
            project.mkdir()
            first = full_paper_e2e.run(root=project)
            second = full_paper_e2e.run(root=project)
            self.assertEqual(first["workflow"], second["workflow"])
            self.assertEqual(first["evaluation_class"], second["evaluation_class"])
            self.assertEqual(first["anchor_count"], second["anchor_count"])
            self.assertEqual(full_paper_e2e.validate({**first, "skill_commit": "0" * 40}, project)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
