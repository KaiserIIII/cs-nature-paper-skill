import hashlib
import importlib.util
import json
import tempfile
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


def canonical_hash(value):
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def write_artifact(root, name, value):
    path = root / name
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    path.write_bytes(payload)
    return {
        "path": name,
        "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
    }


def verified_bundle(root, provider_record=None, behavior_value=None, **changes):
    provider_record = provider_record or record()
    producer_id = "qualification:runner"
    checker_id = "qualification:independent-checker"
    values = {
        "source_integrity": {
            "status": "PASS",
            "provider_id": provider_record["provider_id"],
            "exact_commit": provider_record["exact_commit"],
            "source_hash": provider_record["source_hash"],
        },
        "license": {
            "status": "PASS",
            "license_decision": provider_record["license_decision"],
        },
        "security": {"status": "PASS"},
        "utility": {"status": "PASS"},
        "output_contract": {"status": "PASS", "typed_artifact": True},
        "behavior_comparison": behavior_value or {
            "status": "PASS",
            "decision": "EXTERNAL_BETTER",
            "baseline_provider_id": "PUBLIC_CORE",
            "counterbalanced": True,
            "provider_id": provider_record["provider_id"],
            "exact_commit": provider_record["exact_commit"],
            "source_hash": provider_record["source_hash"],
            "run_ids": ["run-candidate-1", "run-public-core-1"],
            "candidate_output_hashes": ["sha256:" + "d" * 64],
            "public_core_output_hashes": ["sha256:" + "e" * 64],
            "judge_id": "judge:fixed-v41",
            "checker_id": checker_id,
            "judge_config_hash": "sha256:" + "f" * 64,
            "artifact_manifest_hash": "sha256:" + "1" * 64,
            "failures": [],
        },
    }
    checks = {
        name: write_artifact(root, name + ".json", value)
        for name, value in values.items()
    }
    evidence_set = {
        "provider_id": provider_record["provider_id"],
        "exact_commit": provider_record["exact_commit"],
        "source_hash": provider_record["source_hash"],
        "producer_id": producer_id,
        "artifacts": {name: checks[name]["sha256"] for name in sorted(checks)},
    }
    checker_value = {
        "status": "PASS",
        "provider_id": provider_record["provider_id"],
        "producer_id": producer_id,
        "checker_id": checker_id,
        "evidence_set_hash": canonical_hash(evidence_set),
    }
    bundle = {
        "bundle_id": "qualification:paper-specialist:v1",
        "provider_id": provider_record["provider_id"],
        "exact_commit": provider_record["exact_commit"],
        "source_hash": provider_record["source_hash"],
        "producer_id": producer_id,
        "checker_id": checker_id,
        "checks": checks,
        "checker_artifact": write_artifact(root, "checker.json", checker_value),
    }
    bundle.update(changes)
    return bundle


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

    def test_caller_self_reported_qualification_is_not_selected(self):
        runtime = load_module()
        result = runtime.resolve_provider(
            record(), public_core(), formal=True, capability="publication-argument"
        )
        self.assertEqual(result["route"], "FALLBACK_BUILT_IN")
        self.assertEqual(result["provider"]["provider_id"], "internal-specialist:publication-editor")
        self.assertNotEqual(result.get("candidate_eligibility"), "FORMAL_ELIGIBLE")

    def test_qualification_is_derived_from_real_checked_artifacts(self):
        runtime = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = record()
            result = runtime.derive_qualification(
                value, verified_bundle(root, value), root=root
            )
        self.assertEqual(result["qualification_status"], "QUALIFIED")
        self.assertEqual(result["comparison_decision"], "EXTERNAL_BETTER")
        self.assertEqual(result["utility_status"], "PASS")
        self.assertEqual(result["security_status"], "PASS")
        self.assertEqual(result["eligibility"], "FORMAL_ELIGIBLE")

    def test_rebound_validation_bundle_is_rejected(self):
        runtime = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = record()
            bundle = verified_bundle(root, value)
            bundle["source_hash"] = "sha256:" + "c" * 64
            result = runtime.derive_qualification(value, bundle, root=root)
        self.assertEqual(result["qualification_status"], "REJECTED")
        self.assertNotEqual(result["eligibility"], "FORMAL_ELIGIBLE")

    def test_comparison_without_run_artifacts_is_not_qualified(self):
        runtime = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = record()
            result = runtime.derive_qualification(
                value,
                verified_bundle(
                    root,
                    value,
                    behavior_value={
                        "status": "PASS",
                        "decision": "EXTERNAL_BETTER",
                        "baseline_provider_id": "PUBLIC_CORE",
                        "counterbalanced": True,
                    },
                ),
                root=root,
            )
        self.assertNotEqual(result["qualification_status"], "QUALIFIED")
        self.assertNotEqual(result["eligibility"], "FORMAL_ELIGIBLE")

    def test_non_independent_qualification_checker_is_rejected(self):
        runtime = load_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = record()
            bundle = verified_bundle(
                root, value, checker_id="qualification:runner"
            )
            result = runtime.derive_qualification(value, bundle, root=root)
        self.assertEqual(result["qualification_status"], "REJECTED")
        self.assertNotEqual(result["eligibility"], "FORMAL_ELIGIBLE")

    def test_shipped_external_provider_has_no_formal_qualification(self):
        runtime = load_module()
        result = runtime.resolve_provider(
            "external:paper-specialist",
            public_core(),
            formal=True,
            capability="publication-argument",
        )
        self.assertEqual(result["route"], "FALLBACK_BUILT_IN")
        self.assertNotEqual(result.get("candidate_eligibility"), "FORMAL_ELIGIBLE")

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
            "DISABLED",
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
                "type",
                "capabilities",
                "exact_commit",
                "source_hash",
                "license_decision",
                "validation_bundle_id",
                "fallback_provider_id",
                "discovery_only",
            },
        )
        for authored_state in (
            "qualification_status",
            "comparison_decision",
            "utility_status",
            "security_status",
            "eligibility",
        ):
            self.assertNotIn(authored_state, schema["properties"])


if __name__ == "__main__":
    unittest.main()
