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


publication = load("publication_sufficiency")


def make_thin_project(root: Path) -> Path:
    """Create a portable thin-paper fixture; do not couple tests to a user path."""
    state = root / ".research-state"
    state.mkdir(parents=True)
    (state / "project.json").write_text(json.dumps({"submission_targeted": True}), encoding="utf-8")
    (state / "research_contract.json").write_text(json.dumps({"formal_workflow": True}), encoding="utf-8")
    (state / "claims.json").write_text(json.dumps({"claims": [{"status": "SUPPORTED"}, {"status": "WITHDRAWN_PROSPECTIVE_MECHANISM"}]}), encoding="utf-8")
    (state / "evidence_ledger.json").write_text(json.dumps({"anchors": [{"id": "EA-1"}]}), encoding="utf-8")
    (state / "experiment_registry.json").write_text(json.dumps({"experiments": []}), encoding="utf-8")
    (state / "review_finding.json").write_text(json.dumps({"findings": []}), encoding="utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "formal_protocol.md").write_text("Dataset: sklearn digits 8x8. Model: two-layer MLP. Tier 2 is deferred.", encoding="utf-8")
    (root / "paper").mkdir()
    (root / "paper" / "main.tex").write_text("\\section{Related Work}\n\\cite{one}", encoding="utf-8")
    return root


class V4PublicationSufficiencyTests(unittest.TestCase):
    def test_strong_narrow_evidence_does_not_imply_publication_sufficiency(self):
        profile = {
            "scientific_validity": "PASS",
            "evidence_sufficiency": "PASS",
            "dataset_count": 1,
            "dataset_kinds": ["toy"],
            "model_count": 1,
            "modern_baseline_count": 1,
            "ablation_dimension_count": 0,
            "external_validation_count": 0,
            "mechanism_test_count": 0,
            "reviewer_roles_completed": ["methods", "statistics"],
            "manuscript_pages": 7,
            "related_work_depth": "THIN",
        }
        result = publication.assess(profile)
        self.assertEqual(result["scientific_validity"]["status"], "PASS")
        self.assertEqual(result["evidence_sufficiency"]["status"], "PASS")
        self.assertEqual(result["publication_sufficiency"]["status"], "FAIL")
        self.assertEqual(result["reviewer_completeness"]["status"], "FAIL")
        self.assertEqual(result["submission_readiness"]["status"], "FAIL")
        self.assertEqual(result["disposition"], "EXPAND_RESEARCH")

    def test_repetitions_do_not_count_as_research_breadth(self):
        depth = publication.research_depth_profile({
            "dataset_count": 1,
            "model_count": 1,
            "formal_run_count": 960,
            "modern_baseline_count": 1,
            "ablation_dimension_count": 0,
            "external_validation_count": 0,
            "mechanism_test_count": 0,
            "manuscript_pages": 7,
            "related_work_depth": "THIN",
        })
        self.assertEqual(depth["breadth"], "INSUFFICIENT")
        self.assertNotIn("formal_run_count", depth["breadth_dimensions"])

    def test_expansion_plan_targets_missing_scientific_dimensions(self):
        result = publication.assess({
            "scientific_validity": "CONDITIONAL",
            "evidence_sufficiency": "PASS",
            "dataset_count": 1,
            "dataset_kinds": ["toy"],
            "model_count": 1,
            "modern_baseline_count": 1,
            "ablation_dimension_count": 0,
            "external_validation_count": 0,
            "mechanism_test_count": 0,
            "reviewer_roles_completed": [],
            "manuscript_pages": 7,
            "related_work_depth": "THIN",
        })
        actions = " ".join(item["action"] for item in result["research_expansion_plan"])
        self.assertIn("dataset", actions.lower())
        self.assertIn("baseline", actions.lower())
        self.assertIn("ablation", actions.lower())
        self.assertIn("mechanism", actions.lower())
        self.assertIn("related work", actions.lower())

    def test_tta_field_regression_is_not_ready_for_submission(self):
        with tempfile.TemporaryDirectory() as td:
            project = make_thin_project(Path(td))
            result = publication.audit_project(project)
        self.assertIn(result["scientific_validity"]["status"], {"PASS", "CONDITIONAL"})
        self.assertEqual(result["publication_sufficiency"]["status"], "FAIL")
        self.assertEqual(result["disposition"], "EXPAND_RESEARCH")
        self.assertNotEqual(result["disposition"], "READY_FOR_SUBMISSION")
        findings = set(result["finding_ids"])
        self.assertTrue({
            "ONE_TOY_DATASET", "ONE_SMALL_MLP", "INCOMPLETE_MODERN_TTA_BASELINES",
            "INSUFFICIENT_EXTERNAL_VALIDITY", "INVALID_PROSPECTIVE_MECHANISM_PREDICTOR",
            "THIN_RELATED_WORK", "INSUFFICIENT_ABLATIONS", "MANUSCRIPT_TOO_THIN",
        }.issubset(findings), result)

    def test_submission_requires_every_gate(self):
        complete = {
            "scientific_validity": "PASS",
            "evidence_sufficiency": "PASS",
            "dataset_count": 3,
            "dataset_kinds": ["benchmark", "real-world"],
            "model_count": 3,
            "modern_baseline_count": 4,
            "ablation_dimension_count": 3,
            "external_validation_count": 2,
            "mechanism_test_count": 2,
            "reviewer_roles_completed": list(publication.REQUIRED_REVIEWERS),
            "manuscript_pages": 12,
            "related_work_depth": "ADEQUATE",
        }
        result = publication.assess(complete)
        self.assertEqual(result["submission_readiness"]["status"], "PASS", result)
        self.assertEqual(result["disposition"], "READY_FOR_SUBMISSION")

    def test_completion_contract_cannot_bypass_publication_gates(self):
        completion = load("completion_contract")
        with tempfile.TemporaryDirectory() as td:
            project = make_thin_project(Path(td))
            result = completion.evaluate(project)
        self.assertIn("publication_sufficiency", result["checks"])
        self.assertIn("reviewer_completeness", result["checks"])
        self.assertEqual(result["checks"]["publication_sufficiency"]["status"], "FAIL")
        self.assertEqual(result["checks"]["reviewer_completeness"]["status"], "FAIL")
        self.assertEqual(result["project_disposition"], "EXPAND_RESEARCH")

    def test_director_submission_gate_reopens_underpowered_research(self):
        director = load("director_loop")
        with tempfile.TemporaryDirectory() as td:
            project = make_thin_project(Path(td))
            result = director.submission_gate(project)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["disposition"], "EXPAND_RESEARCH")
        self.assertEqual(result["publication_sufficiency"]["status"], "FAIL")
        self.assertEqual(result["reviewer_completeness"]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
