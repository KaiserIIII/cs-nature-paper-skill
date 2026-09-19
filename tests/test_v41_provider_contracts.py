import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "v41_provider_contracts", ROOT / "scripts" / "v41_provider_contracts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record(**overrides):
    value = {
        "provider_id": "external:paper-specialist",
        "type": "EXTERNAL_SKILL",
        "capabilities": ["publication-argument"],
        "exact_commit": "a" * 40,
        "source_hash": "sha256:" + "b" * 64,
        "license_decision": "CLEAR",
        "qualification_status": "QUALIFIED",
        "comparison_decision": "EXTERNAL_BETTER",
        "utility_status": "PASS",
        "security_status": "PASS",
        "behavior_trial": {"status": "PASS", "output_contract": "PASS"},
        "checker_id": "checker:publication",
        "input_contract": {"type": "object"},
        "output_contract": {"type": "object", "typed_artifact": True},
        "permissions": ["local_read"],
        "network": False,
        "credentials_required": False,
        "cost_class": "FREE",
        "fallback_provider_id": "internal-specialist:publication-editor",
    }
    value.update(overrides)
    return value


def public_core():
    return {
        "provider_id": "internal-specialist:publication-editor",
        "type": "INTERNAL_SPECIALIST",
        "capabilities": ["publication-argument"],
        "source_kind": "VENDORED_BUILT_IN_TEAM",
    }


class V41ProviderContractTests(unittest.TestCase):
    def test_missing_exact_commit_is_invalid(self):
        runtime = load_module()
        result = runtime.validate_provider_record(record(exact_commit=""))
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("exact_commit" in item for item in result["findings"]))

    def test_not_run_comparison_cannot_be_formally_eligible(self):
        runtime = load_module()
        value = record(comparison_decision="NOT_RUN", eligibility="FORMAL_ELIGIBLE")
        self.assertNotEqual(
            runtime.derive_eligibility(value, formal=True, capability="publication-argument"),
            "FORMAL_ELIGIBLE",
        )

    def test_security_failure_disables_provider(self):
        runtime = load_module()
        value = record(security_status="FAIL")
        self.assertEqual(
            runtime.derive_eligibility(value, formal=True, capability="publication-argument"),
            "DISABLED",
        )

    def test_behavior_qualified_external_better_provider_is_selected(self):
        runtime = load_module()
        result = runtime.resolve_provider(
            record(), public_core(), formal=True, capability="publication-argument"
        )
        self.assertEqual(result["route"], "EXTERNAL_PROVIDER")
        self.assertEqual(result["provider"]["provider_id"], "external:paper-specialist")
        self.assertEqual(result["eligibility"], "FORMAL_ELIGIBLE")

    def test_unqualified_candidate_falls_back_to_public_core(self):
        runtime = load_module()
        result = runtime.resolve_provider(
            record(behavior_trial={"status": "NOT_RUN"}),
            public_core(),
            formal=True,
            capability="publication-argument",
        )
        self.assertEqual(result["route"], "FALLBACK_BUILT_IN")
        self.assertEqual(result["provider"]["provider_id"], "internal-specialist:publication-editor")
        self.assertNotEqual(result["candidate_eligibility"], "FORMAL_ELIGIBLE")

    def test_capability_mismatch_falls_back(self):
        runtime = load_module()
        result = runtime.resolve_provider(
            record(capabilities=["figure-audit"]),
            public_core(),
            formal=True,
            capability="publication-argument",
        )
        self.assertEqual(result["route"], "FALLBACK_BUILT_IN")
        self.assertEqual(result["reason"], "CAPABILITY_MISMATCH")

    def test_hand_edited_eligibility_is_not_authoritative(self):
        runtime = load_module()
        value = record(qualification_status="PROVISIONAL", eligibility="FORMAL_ELIGIBLE")
        self.assertEqual(
            runtime.derive_eligibility(value, formal=True, capability="publication-argument"),
            "NON_LOAD_BEARING",
        )

    def test_schema_declares_three_independent_states(self):
        import json

        schema = json.loads(
            (ROOT / "assets" / "schemas" / "v41_provider_contract.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            set(schema["required"]),
            {
                "provider_id",
                "capabilities",
                "exact_commit",
                "source_hash",
                "license_decision",
                "qualification_status",
                "comparison_decision",
                "utility_status",
                "security_status",
            },
        )


if __name__ == "__main__":
    unittest.main()
