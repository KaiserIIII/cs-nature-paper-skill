import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_runtime():
    spec = importlib.util.spec_from_file_location(
        "formal_campaign_admission", ROOT / "scripts" / "formal_campaign_admission.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FormalCampaignAdmissionTests(unittest.TestCase):
    def valid_record(self):
        return {
            "campaign_id": "fixture-formal-v2",
            "planned_jobs": 1000,
            "semantic_canary": {
                "status": "PASS",
                "coverage": {
                    "methods": ["source", "adaptive-a", "recovery-a"],
                    "method_classes": ["SOURCE", "ADAPTIVE", "RECOVERY"],
                    "trajectories": ["A-B-A", "A-B-C-A"],
                    "seeds": [0, 1],
                    "shifts": ["noise:1"],
                },
                "source_immutability": {
                    "state_dict_identical": True,
                    "bn_running_mean_identical": True,
                    "bn_running_var_identical": True,
                    "optimizer_step_count": 0,
                    "trainable_parameter_delta": 0.0,
                    "entered_mutating_train_mode": False,
                },
            },
            "method_state_contracts": {
                "status": "PASS",
                "methods": {
                    "source": {"unexpected_mutations": []},
                    "adaptive-a": {"unexpected_mutations": []},
                    "recovery-a": {"unexpected_mutations": []},
                },
            },
            "temporal_availability": {
                "status": "PASS",
                "prospective_events_checked": 6,
                "all_measurement_steps_precede_outcomes": True,
            },
            "provenance_binding": {
                "status": "PASS",
                "frozen_hashes": {
                    name: "sha256:" + str(index) * 64
                    for index, name in enumerate(
                        ("runner", "manifest", "dataset", "checkpoints", "environment", "protocol"), 1
                    )
                },
                "all_shards_bound": True,
            },
            "early_sanity_audit": {
                "status": "PASS",
                "completed_jobs_checked": 10,
                "metric_ranges_valid": True,
                "event_order_valid": True,
                "provenance_valid": True,
                "state_mutations_valid": True,
            },
        }

    def test_complete_scientific_canary_authorizes_scale_out(self):
        result = load_runtime().evaluate(self.valid_record())
        self.assertEqual(result["status"], "FORMAL_ADMISSION_PASS", result["findings"])
        self.assertTrue(result["scale_out_authorized"])

    def test_source_mutation_or_temporal_leakage_fails_closed(self):
        runtime = load_runtime()
        record = self.valid_record()
        record["semantic_canary"]["source_immutability"]["bn_running_mean_identical"] = False
        record["temporal_availability"]["all_measurement_steps_precede_outcomes"] = False
        result = runtime.evaluate(record)
        self.assertEqual(result["status"], "FORMAL_ADMISSION_FAIL")
        self.assertTrue(any("BatchNorm" in item for item in result["findings"]), result)
        self.assertTrue(any("measurement_time < outcome_time" in item for item in result["findings"]), result)

    def test_canary_requires_source_adaptive_recovery_trajectories_and_two_seeds(self):
        record = self.valid_record()
        record["semantic_canary"]["coverage"]["method_classes"] = ["SOURCE", "ADAPTIVE"]
        record["semantic_canary"]["coverage"]["trajectories"] = ["A-B-A"]
        record["semantic_canary"]["coverage"]["seeds"] = [0]
        result = load_runtime().evaluate(record)
        self.assertEqual(result["status"], "FORMAL_ADMISSION_FAIL")
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_formal_v1_is_preserved_as_an_invalid_primary_evidence_fixture(self):
        fixture = json.loads(
            (ROOT / "assets" / "evals" / "v4" / "regressions" / "formal_v1_invalid.json").read_text(encoding="utf-8")
        )
        self.assertEqual(fixture["disposition"], "INVALID_FOR_PRIMARY_EVIDENCE")
        self.assertEqual(fixture["observed_jobs"], 1000)
        self.assertEqual(
            set(fixture["reason_codes"]),
            {
                "SOURCE_BN_STATE_CONTAMINATION",
                "DRIFT_TEMPORAL_MISLABELING",
                "INCOMPLETE_RUNNER_DATASET_PROVENANCE",
            },
        )

    def test_skill_requires_formal_campaign_admission_before_scale_out(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("FORMAL_CAMPAIGN_ADMISSION_GATE", skill)
        self.assertIn("references/core/formal-campaign-admission.md", skill)


if __name__ == "__main__":
    unittest.main()
