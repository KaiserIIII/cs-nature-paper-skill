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


router = load("skill_router")


class SpecialistRoutingHotfixTests(unittest.TestCase):
    def test_baseline_writing_cannot_staff_load_bearing_work(self):
        result = router.resolve("evidence-bound-writing", purpose="formal", load_bearing=True, criticality="high")
        self.assertTrue(result["specialist_required"])
        self.assertEqual(result["provider_quality"], "BASELINE")
        self.assertIn(result["execution_mode"], {"SPECIALIST_DISCOVERY", "HOST_EXECUTION_REQUIRED"})
        self.assertEqual(result["selected"], [])

    def test_deterministic_review_is_not_formal_novelty_review(self):
        result = router.resolve("adversarial-review", purpose="formal", load_bearing=True, criticality="high")
        self.assertTrue(result["specialist_required"])
        self.assertFalse(result["formal_eligible"])
        self.assertEqual(result["provider_quality"], "BASELINE")

    def test_basic_descriptive_stats_can_use_native_provider(self):
        result = router.resolve("statistical-modeling", purpose="exploratory", task="mean variance descriptive statistics")
        self.assertFalse(result["specialist_required"])
        self.assertEqual(result["execution_mode"], "NATIVE")

    def test_specialized_statistics_triggers_specialist_routing(self):
        result = router.resolve(
            "statistical-modeling",
            purpose="formal",
            load_bearing=True,
            criticality="critical",
            task="conformal inference with distribution shift and risk control",
        )
        self.assertTrue(result["specialist_required"])
        self.assertEqual(result["execution_mode"], "SPECIALIST_DISCOVERY")

    def test_qualified_installed_specialist_wins_for_matching_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry_dir = Path(tmp)
            (registry_dir / "capabilities.json").write_text((ROOT / "assets/registry/capabilities.json").read_text(encoding="utf-8"), encoding="utf-8")
            catalog = {
                "schema_version": 1,
                "skill_version": router.SKILL_VERSION,
                "skills": [{
                    "skill_id": "formal-stats-specialist",
                    "source": "https://example.invalid/specialist",
                    "exact_ref": "a" * 40,
                    "runtime_status": "SPECIALIST",
                    "provider_quality": "FORMAL_QUALIFIED",
                    "qualification_state": "FORMAL_QUALIFIED",
                    "capabilities": ["statistical-modeling"],
                    "behavior_trials": ["PASS"],
                    "allowed_activation_scope": ["formal"],
                    "permissions": {},
                }],
            }
            (registry_dir / "skill_catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
            result = router.resolve("statistical-modeling", registry_dir=registry_dir, purpose="formal", load_bearing=True, criticality="critical", task="mixed effects")
            self.assertEqual(result["selected"][0]["skill_id"], "formal-stats-specialist")
            self.assertEqual(result["execution_mode"], "INSTALLED_SPECIALIST")

    def test_failed_discovery_exposes_host_execution_contract(self):
        result = router.resolve("evidence-bound-writing", purpose="formal", load_bearing=True, criticality="high")
        self.assertEqual(result["host_fallback"], "HOST_EXECUTION_REQUIRED")
        self.assertTrue(result["checker_required"])
        self.assertTrue(result["evidence_required"])
        self.assertTrue(result["handoff_required"])

    def test_auto_hire_remains_fail_closed(self):
        director = load("director_loop")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            state = project / ".research-state"
            state.mkdir()
            (state / "employee_registry.json").write_text(json.dumps({"employees": []}), encoding="utf-8")
            result = director.resolve_capability(project, "formal-writing", candidate_pool=None, policy=None)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["recovery"], "AUTO_HIRE")

    def test_legacy_evidence_and_provenance_routes_remain_available(self):
        evidence = load("evidence_anchor")
        value = {
            "anchor_id": "A",
            "claim_id": "C",
            "result_id": "R",
            "source_artifact": "x",
            "exact_region": "line 1",
            "transformation": "none",
            "uncertainty": "u",
            "scope": "s",
            "status": "OBSERVED",
            "config_hash": "sha256:config",
            "input_hash": "sha256:input",
        }
        self.assertIn(evidence.validate_anchor(value)["status"], {"PASS", "CONDITIONAL"})


if __name__ == "__main__":
    unittest.main()
