import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "research_expansion", ROOT / "scripts" / "research_expansion.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


expansion = load_module()


def load_director():
    spec = importlib.util.spec_from_file_location(
        "director_with_expansion", ROOT / "scripts" / "director_loop.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


THIN_ASSESSMENT = {
    "disposition": "EXPAND_RESEARCH",
    "findings": [
        "ONE_TOY_DATASET",
        "ONE_SMALL_MLP",
        "INCOMPLETE_MODERN_TTA_BASELINES",
        "INVALID_PROSPECTIVE_MECHANISM_PREDICTOR",
        "INSUFFICIENT_ABLATIONS",
        "MANUSCRIPT_TOO_THIN",
    ],
}


class V4ResearchExpansionTests(unittest.TestCase):
    def test_thin_tta_assessment_becomes_executable_campaign(self):
        campaign = expansion.build_campaign(THIN_ASSESSMENT, project_id="ccta_tta")
        packages = {item["id"]: item for item in campaign["work_packages"]}
        self.assertTrue(
            {
                "dataset_benchmark_expansion",
                "model_architecture_expansion",
                "modern_baseline_expansion",
                "mechanism_timing_repair",
                "ablation_matrix",
                "statistical_analysis",
                "publication_figures",
                "adversarial_review",
                "manuscript_revision",
            }.issubset(packages)
        )
        for package in packages.values():
            self.assertTrue(package["command"])
            self.assertTrue(package["expected_artifacts"])
            self.assertTrue(package["checker"])
            self.assertTrue(package["claim_impact"])
        self.assertEqual(campaign["status"], "PLANNED")
        self.assertEqual(campaign["submission_readiness"], "FAIL")

    def test_planned_or_started_campaign_is_not_complete(self):
        campaign = expansion.build_campaign(THIN_ASSESSMENT, project_id="ccta_tta")
        with tempfile.TemporaryDirectory() as td:
            result = expansion.verify_campaign(campaign, Path(td))
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["disposition"], "EXPAND_RESEARCH")
        self.assertTrue(result["missing_artifacts"])

    def test_verified_artifacts_unlock_dependents_but_not_future_packages(self):
        campaign = expansion.build_campaign(THIN_ASSESSMENT, project_id="ccta_tta")
        first = [item for item in campaign["work_packages"] if not item["depends_on"]]
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            for package in first:
                for relative in package["expected_artifacts"]:
                    artifact = project / relative
                    artifact.parent.mkdir(parents=True, exist_ok=True)
                    artifact.write_text("real output\n", encoding="utf-8")
                receipt = project / package["checker_receipt"]
                receipt.parent.mkdir(parents=True, exist_ok=True)
                hashes = {
                    relative: "sha256:" + hashlib.sha256((project / relative).read_bytes()).hexdigest()
                    for relative in package["expected_artifacts"]
                }
                receipt.write_text(
                    json.dumps({"status": "PASS", "artifact_sha256": hashes}),
                    encoding="utf-8",
                )
            result = expansion.verify_campaign(campaign, project)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(set(item["id"] for item in first).issubset(result["completed_packages"]))
        self.assertTrue(result["ready_packages"])
        self.assertEqual(result["disposition"], "EXPAND_RESEARCH")

    def test_director_persists_idempotent_campaign_from_failed_gate(self):
        director = load_director()
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "paper"
            (project / ".research-state").mkdir(parents=True)
            assessment = {
                "disposition": "EXPAND_RESEARCH",
                "finding_ids": THIN_ASSESSMENT["findings"],
            }
            first = director.ensure_expansion_campaign(project, assessment)
            first_bytes = Path(first["path"]).read_bytes()
            second = director.ensure_expansion_campaign(project, assessment)
            self.assertTrue(Path(first["path"]).is_file())
            self.assertEqual(first_bytes, Path(second["path"]).read_bytes())
        self.assertEqual(first["status"], "EXPAND_RESEARCH")
        self.assertEqual(first["sha256"], second["sha256"])


if __name__ == "__main__":
    unittest.main()
