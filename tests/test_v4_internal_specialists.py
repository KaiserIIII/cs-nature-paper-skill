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


internal = load("internal_specialists")
router = load("skill_router")
provider_runtime = load("provider_runtime")


class V4InternalSpecialistTests(unittest.TestCase):
    def test_builtin_pack_contains_the_complete_publication_grade_team(self):
        result = internal.validate_pack()
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["architecture_version"], "4.0.0")
        self.assertEqual(
            set(result["specialist_ids"]),
            {
                "research-director", "literature-evidence", "innovation-prior-art",
                "theory-mechanism", "data-dataset", "experimental-design",
                "research-engineering-compute", "implementation", "statistics",
                "scientific-visualization", "scientific-writing", "reproducibility-integrity",
                "adversarial-review-board", "publication-editor",
            },
        )
        self.assertEqual(result["quality_tier"], "PUBLICATION_GRADE")

    def test_builtin_contracts_are_operating_contracts_not_empty_templates(self):
        pack = internal.load_pack()
        for specialist in pack["specialists"]:
            self.assertGreaterEqual(len(specialist["decision_rules"]), 3, specialist["id"])
            self.assertGreaterEqual(len(specialist["quality_criteria"]), 3, specialist["id"])
            self.assertGreaterEqual(len(specialist["forbidden_actions"]), 2, specialist["id"])
            for path in specialist["contract_files"]:
                text = (ROOT / "references" / "internal-specialists" / path).read_text(encoding="utf-8")
                self.assertIn("Decision rules", text)
                self.assertIn("Output contract", text)

    def test_quality_upgrade_discovery_triggers_for_specialized_writing(self):
        decision = internal.provider_decision(
            "evidence-bound-writing",
            task="publication-quality full paper with claim-evidence traceability",
            purpose="formal",
            load_bearing=True,
            criticality="high",
            internal_available=True,
        )
        self.assertEqual(decision["decision"], "QUALITY_UPGRADE_DISCOVERY")
        self.assertEqual(decision["status"], "TRIGGERED")
        self.assertTrue(decision["fallback_available"])

    def test_ordinary_paired_bootstrap_skips_external_discovery(self):
        decision = internal.provider_decision(
            "statistical-modeling",
            task="ordinary paired bootstrap mean and confidence interval",
            purpose="formal",
            load_bearing=True,
            criticality="high",
            internal_available=True,
        )
        self.assertEqual(decision["decision"], "INTERNAL_BETTER")
        self.assertEqual(decision["status"], "SKIPPED")
        self.assertEqual(decision["external_discovery"], "SKIPPED")

    def test_discovery_failure_falls_back_to_builtin_specialist(self):
        decision = internal.provider_decision(
            "novelty-analysis",
            task="closest work and prior art audit",
            purpose="formal",
            load_bearing=True,
            criticality="high",
            internal_available=True,
            discovery_status="UNAVAILABLE",
            discovery_attempted=True,
        )
        self.assertEqual(decision["decision"], "FALLBACK_BUILT_IN")
        self.assertEqual(decision["status"], "FALLBACK")
        self.assertEqual(decision["selected_provider"], "BUILT_IN_SPECIALIST")

    def test_router_exposes_builtin_fallback_and_decision(self):
        result = router.resolve(
            "evidence-bound-writing",
            purpose="formal",
            load_bearing=True,
            criticality="high",
            task="publication-quality manuscript",
        )
        self.assertEqual(result["execution_mode"], "SPECIALIST_DISCOVERY")
        self.assertEqual(result["fallback_provider"]["type"], "INTERNAL_SPECIALIST")
        self.assertEqual(result["provider_decision"]["decision"], "QUALITY_UPGRADE_DISCOVERY")

        fallback = router.resolve(
            "evidence-bound-writing",
            purpose="formal",
            load_bearing=True,
            criticality="high",
            task="publication-quality manuscript",
            discovery_attempted=True,
        )
        self.assertEqual(fallback["execution_mode"], "BUILT_IN_SPECIALIST")
        self.assertEqual(fallback["selected"][0]["type"], "INTERNAL_SPECIALIST")

    def test_provider_runtime_accepts_builtin_and_keeps_discovery_nonblocking(self):
        builtin = provider_runtime.internal_specialist_provider("statistics")
        result = provider_runtime.resolve_provider(
            "statistical-analysis",
            {"task": "ordinary paired bootstrap", "load_bearing": True},
            True,
            "HIGH",
            {"local_read", "local_write", "execute", "auto_hire"},
            [builtin],
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["provider"]["type"], "INTERNAL_SPECIALIST")
        self.assertEqual(result["provider_decision"]["decision"], "INTERNAL_BETTER")

    def test_provider_decision_is_serializable_for_project_audit(self):
        value = internal.provider_decision("data-dataset", task="dataset leakage audit", internal_available=True)
        json.dumps(value)


if __name__ == "__main__":
    unittest.main()
