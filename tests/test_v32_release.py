import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class V32ReleaseTests(unittest.TestCase):
    def test_release_manifest_declares_v3_2_and_candidate_disposition(self):
        value = json.loads((ROOT / "release_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(value["source_version"], "3.2.0")
        self.assertIn("V3.2.0 RELEASE CANDIDATE READY", value["release_disposition"])

    def test_v31_tag_and_baseline_are_untouched(self):
        tagged = subprocess.run(["git", "show", "v3.1.1:SKILL.md"], cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertIn("3.1.1", tagged.stdout)
        merge_base = subprocess.run(["git", "merge-base", "v3.2", "6b34dcba551bdf200c2d7dd49bcb6b6057ef67c4"], cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual(merge_base.stdout.strip(), "6b34dcba551bdf200c2d7dd49bcb6b6057ef67c4")

    def test_ci_runs_and_uploads_v32_full_paper_e2e(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("python scripts/full_paper_e2e.py --output .full-paper-e2e.json", workflow)
        self.assertIn(".full-paper-e2e.json", workflow)


if __name__ == "__main__":
    unittest.main()
