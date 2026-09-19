import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ROOT / "providers"
if str(PROVIDERS) not in sys.path:
    sys.path.insert(0, str(PROVIDERS))


def load_provider(name):
    spec = importlib.util.spec_from_file_location(name, PROVIDERS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


review_provider = load_provider("review_provider")
writing_provider = load_provider("writing_provider")


def finding(finding_id, role, status="OPEN"):
    return {
        "id": finding_id,
        "role": role,
        "severity": "MAJOR",
        "location": "whole manuscript",
        "why": "typed test finding",
        "evidence": "artifacts/manuscript.md",
        "alternative": "retain scope",
        "smallest_sufficient_fix": "apply the bounded fix",
        "residual_risk": "specialist review remains necessary",
        "status": status,
    }


class ReviewWritingHotfixTests(unittest.TestCase):
    def test_review_defers_scientific_judgments(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            artifacts = project / "artifacts"
            artifacts.mkdir()
            (artifacts / "figure.svg").write_text("<svg />", encoding="utf-8")
            (artifacts / "manuscript.md").write_text(
                "# A bounded study\n\n## Abstract\n\n## Related Work\n\n## Method\n\n"
                "## Results\n\nFigure: artifacts/figure.svg.\n\n## Limitations\n",
                encoding="utf-8",
            )
            result = review_provider.execute(project)
            self.assertEqual(result["status"], "PASS")
            value = json.loads((artifacts / "review_findings.json").read_text(encoding="utf-8"))
            self.assertEqual(value["scientific_review"]["status"], "REQUIRED")
            self.assertFalse(value["scientific_review"]["completed"])
            self.assertFalse(any(item.get("role") in review_provider.SCIENTIFIC_REVIEW_ROLES for item in value["findings"]))
            self.assertFalse(any(item.get("id", "").startswith("CHECK-") for item in value["findings"]))
            self.assertTrue(any(item.get("id") == "RF-001" for item in value["findings"]))

    def test_validate_findings_rejects_scientific_role(self):
        result = review_provider.validate_findings([finding("N-1", "novelty")])
        self.assertEqual(result["status"], "FAIL")
        self.assertIn("non-deterministic", result["findings"][0])

    def test_revision_resolves_only_actual_reproducibility_fix(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            artifacts = project / "artifacts"
            artifacts.mkdir()
            (artifacts / "manuscript.md").write_text("# Draft\n\n## Limitations\n", encoding="utf-8")
            payload = {
                "status": "PASS",
                "findings": [finding("RF-001", "reproducibility"), finding("N-1", "novelty")],
                "scientific_review_required": True,
            }
            (artifacts / "review_findings.json").write_text(json.dumps(payload), encoding="utf-8")
            result = writing_provider.execute(project, "revision")
            self.assertEqual(result["status"], "PASS")
            revised = (artifacts / "revised_manuscript.md").read_text(encoding="utf-8")
            self.assertIn("## Reproducibility", revised)
            updated = json.loads((artifacts / "review_findings.json").read_text(encoding="utf-8"))
            statuses = {item["id"]: item["status"] for item in updated["findings"]}
            self.assertEqual(statuses["RF-001"], "RESOLVED")
            self.assertEqual(statuses["N-1"], "OPEN")
            self.assertEqual(result["unresolved_scientific_findings"], 1)
            self.assertTrue(result["scientific_review_required"])


if __name__ == "__main__":
    unittest.main()
