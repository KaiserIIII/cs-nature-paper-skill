import json
import importlib.util
import tempfile
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class V32ReleaseTests(unittest.TestCase):
    def test_release_manifest_declares_v3_2_and_candidate_disposition(self):
        value = json.loads((ROOT / "release_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(value["source_version"], "3.2.0")
        self.assertIn("V3.2.0 RELEASE BLOCKED", value["release_disposition"])
        self.assertIsInstance(value["hosted_ci"], dict)
        self.assertIsNone(value["hosted_ci"]["run_id"])

    def test_v31_tag_and_baseline_are_untouched(self):
        tagged = subprocess.run(["git", "show", "v3.1.1:SKILL.md"], cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertIn("3.1.1", tagged.stdout)
        baseline_ref = next(
            (
                ref
                for ref in ("v3.2", "refs/remotes/origin/v3.2")
                if subprocess.run(
                    ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                ).returncode == 0
            ),
            None,
        )
        self.assertIsNotNone(baseline_ref, "v3.2 baseline ref is unavailable")
        merge_base = subprocess.run(["git", "merge-base", baseline_ref, "6b34dcba551bdf200c2d7dd49bcb6b6057ef67c4"], cwd=ROOT, capture_output=True, text=True, check=True)
        self.assertEqual(merge_base.stdout.strip(), "6b34dcba551bdf200c2d7dd49bcb6b6057ef67c4")

    def test_ci_runs_and_uploads_v32_full_paper_e2e(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("fetch-tags: true", workflow)
        self.assertIn("python scripts/full_paper_e2e.py --output .full-paper-e2e.json", workflow)
        self.assertIn(".full-paper-e2e.json", workflow)

    def test_release_validator_checks_v32_e2e_result(self):
        spec = importlib.util.spec_from_file_location("validate_release", ROOT / "scripts" / "validate_release.py")
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "e2e.json"
            path.write_text(json.dumps({"status": "PASS", "evaluation_class": "HARNESS_SELF_TEST", "model_behavior": "NOT_RUN", "skill_commit": commit, "completion": {"status": "PASS"}, "director_orchestration": {"status": "PASS", "evaluation_class": "DIRECTOR_ORCHESTRATION_E2E"}}), encoding="utf-8")
            self.assertEqual(module.validate_v32_e2e(path, ROOT), [])

    def test_hosted_ci_binding_rejects_wrong_sha_branch_version_and_matrix(self):
        spec = importlib.util.spec_from_file_location("validate_release", ROOT / "scripts" / "validate_release.py")
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        sha = "a" * 40
        base = {
            "source_version": "3.2.0",
            "source_commit": sha,
            "source_commit_mode": "resolved",
            "generated_at": "2026-08-28T00:00:00Z",
            "deterministic_tests": {},
            "hosted_ci": {
                "run_id": 1,
                "workflow": "cs-nature-paper-v3.2",
                "branch": "v3.2",
                "head_sha": sha,
                "conclusion": "success",
                "matrix": {name: "PASS" for name in module.REQUIRED_CI_MATRIX},
            },
            "model_behavior_eval": "NOT_RUN",
            "e2e_status": "PASS",
            "known_limitations": [],
            "release_disposition": "V3.2.0 RELEASE READY",
        }
        cases = (
            ({**base, "source_version": "3.1.1"}, "HOSTED_CI_WRONG_VERSION"),
            ({**base, "hosted_ci": {**base["hosted_ci"], "head_sha": "b" * 40}}, "HOSTED_CI_WRONG_SHA"),
            ({**base, "hosted_ci": {**base["hosted_ci"], "branch": "other"}}, "HOSTED_CI_WRONG_BRANCH"),
            ({**base, "hosted_ci": {**base["hosted_ci"], "matrix": {}}}, "HOSTED_CI_MATRIX_INCOMPLETE"),
        )
        for manifest, code in cases:
            findings = module.validate_release_manifest_value(
                manifest,
                expected_commit=sha,
                expected_branch="v3.2",
                expected_workflow="cs-nature-paper-v3.2",
            )
            self.assertTrue(any(item.startswith(code) for item in findings), code)


if __name__ == "__main__":
    unittest.main()
