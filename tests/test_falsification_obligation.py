import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "falsification_obligation.py"


def canonical_hash(value):
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def profile(*, domain="machine-learning", study_type="ml-benchmark", **overrides):
    spec = importlib.util.spec_from_file_location(
        "publication_profiles_fixture", ROOT / "scripts" / "publication_profiles.py"
    )
    assert spec and spec.loader
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    registry = json.loads(
        (ROOT / "assets" / "registry" / "publication_profiles.json").read_text(
            encoding="utf-8"
        )
    )
    value = runtime.resolve_profile(
        {"domain": domain, "study_type": study_type}, registry["profiles"]
    )
    value.update(overrides)
    if overrides:
        unsigned = {key: item for key, item in value.items() if key != "canonical_output_hash"}
        value["canonical_output_hash"] = canonical_hash(unsigned)
    return value


def claim(**overrides):
    value = {
        "claim_id": "C-001",
        "text": "The method generalizes beyond the development benchmark.",
        "strength": "HIGH",
        "load_bearing": True,
    }
    value.update(overrides)
    return value


def evidence_for(artifact, *, include=None):
    include = include or {
        "confirmation_test",
        "falsification_attempt",
        "boundary_condition_test",
        "strongest_surviving_alternative",
        "residual_confidence",
    }
    checks = {}
    for field in include:
        checks[field] = {
            "status": "OBSERVED",
            "evidence_hash": "sha256:" + field.encode("utf-8").hex().ljust(64, "0")[:64],
            "summary": f"Recorded evidence for {field}",
        }
    return {
        "claim_hash": artifact["claim_hash"],
        "profile_hash": artifact["profile_hash"],
        "obligation_hash": artifact["obligation_hash"],
        "checks": checks,
    }


def rehash_profile(value):
    value["canonical_output_hash"] = canonical_hash(
        {key: item for key, item in value.items() if key != "canonical_output_hash"}
    )
    return value


def make_project(root, claims=None):
    project = root / "project"
    state = project / ".research-state"
    state.mkdir(parents=True)
    (state / "project.json").write_text(
        json.dumps(
            {
                "schema_version": 3,
                "skill_version": "4.1.0",
                "project_dir": str(project.resolve()),
                "domain": "machine-learning",
                "study_type": "ml-benchmark",
            }
        ),
        encoding="utf-8",
    )
    (state / "research_contract.json").write_text(
        json.dumps(
            {
                "schema_version": 3,
                "skill_version": "4.1.0",
                "project": {
                    "domain": "machine-learning",
                    "study_type": "ml-benchmark",
                },
            }
        ),
        encoding="utf-8",
    )
    (state / "claims.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "skill_version": "4.1.0",
                "claims": claims
                or [
                    {
                        "id": "C-001",
                        "text": "The method generalizes beyond the development benchmark.",
                        "strength": "HIGH",
                        "load_bearing": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return project


def authority_context(runtime):
    with tempfile.TemporaryDirectory() as directory:
        project = make_project(Path(directory))
        return runtime._load_authority_context(project, "C-001")


class FalsificationObligationTests(unittest.TestCase):
    def runtime(self):
        self.assertTrue(MODULE.is_file(), "falsification_obligation.py is not implemented")
        spec = importlib.util.spec_from_file_location("falsification_obligation", MODULE)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_caller_constructed_authority_cannot_reach_verified_status(self):
        runtime = self.runtime()
        seal_context = getattr(runtime, "_sealed_context", None)
        check_with_context = getattr(runtime, "_check_obligation_with_context", None)
        if not callable(seal_context) or not callable(check_with_context):
            return
        context = seal_context(
            claim(claim_id="C-ATTACKER"),
            profile(),
            canonical_hash({"attacker": "selected snapshot"}),
        )
        artifact = runtime._derive_obligation_with_context(
            context,
            producer_id="provider:falsification",
        )
        result = check_with_context(
            artifact,
            evidence_for(artifact),
            producer_id="provider:falsification",
            checker_id="checker:falsification",
            authority_context=context,
        )

        self.assertNotEqual(result["status"], "OBLIGATION_VERIFIED")

    def test_high_strength_or_load_bearing_claim_requires_obligation(self):
        runtime = self.runtime()
        for value in (
            claim(load_bearing=False, strength="HIGH"),
            claim(load_bearing=True, strength="BOUNDED"),
        ):
            with self.subTest(value=value):
                artifact = runtime.derive_obligation(
                    value, profile(), producer_id="provider:falsification"
                )
                self.assertEqual(artifact["status"], "OBLIGATION_REQUIRED")
                self.assertEqual(artifact["claim_hash"], canonical_hash(value))
                self.assertEqual(
                    artifact["profile_hash"], profile()["canonical_output_hash"]
                )
                for field in (
                    "confirmation_test",
                    "falsification_attempt",
                    "boundary_condition_test",
                    "strongest_surviving_alternative",
                    "residual_confidence",
                ):
                    self.assertIn(field, artifact)

    def test_ordinary_claim_is_not_required(self):
        runtime = self.runtime()
        artifact = runtime.derive_obligation(
            claim(strength="BOUNDED", load_bearing=False),
            profile(),
            producer_id="provider:falsification",
        )
        self.assertEqual(artifact["status"], "NOT_REQUIRED")
        self.assertFalse(artifact["required"])

    def test_checks_are_profile_aware_with_conservative_fallback(self):
        runtime = self.runtime()
        cases = [
            ("machine-learning", "ml-benchmark", "MACHINE_LEARNING", "ML-HELD-OUT"),
            ("software-engineering", "empirical", "SOFTWARE_ENGINEERING", "SE-MATCHED-WORKFLOW"),
            ("systems", "engineering-system", "SYSTEMS", "SYS-MATCHED-WORKLOAD"),
            ("theory", "theory", "THEORY", "THEORY-INDEPENDENT-DERIVATION"),
            ("hci", "human-study", "HUMAN_STUDY", "HUMAN-CONSTRUCT-CHECK"),
            ("unknown", "unknown", "GENERIC_CONSERVATIVE", "GENERIC-INDEPENDENT-CHECK"),
        ]
        for domain, study_type, family, confirmation_id in cases:
            with self.subTest(domain=domain, study_type=study_type):
                artifact = runtime.derive_obligation(
                    claim(),
                    profile(domain=domain, study_type=study_type),
                    producer_id="provider:falsification",
                )
                self.assertEqual(artifact["profile_family"], family)
                self.assertEqual(
                    artifact["confirmation_test"]["check_id"], confirmation_id
                )

    def test_accepts_native_resolver_hash_format(self):
        runtime = self.runtime()
        native = profile()
        native["canonical_output_hash"] = native["canonical_output_hash"].removeprefix("sha256:")
        artifact = runtime.derive_obligation(
            claim(), native, producer_id="provider:falsification"
        )
        self.assertEqual(artifact["status"], "OBLIGATION_REQUIRED")

    def test_accepts_actual_resolver_artifact(self):
        runtime = self.runtime()
        profile_spec = importlib.util.spec_from_file_location(
            "publication_profiles", ROOT / "scripts" / "publication_profiles.py"
        )
        profile_runtime = importlib.util.module_from_spec(profile_spec)
        self.assertIsNotNone(profile_spec.loader)
        profile_spec.loader.exec_module(profile_runtime)
        registry = json.loads(
            (ROOT / "assets" / "registry" / "publication_profiles.json").read_text(
                encoding="utf-8"
            )
        )
        resolved = profile_runtime.resolve_profile(
            {"domain": "machine-learning", "study_type": "ml-benchmark"},
            registry["profiles"],
        )
        self.assertEqual(resolved["status"], "PROFILE_RESOLVED", resolved)
        artifact = runtime.derive_obligation(
            claim(), resolved, producer_id="provider:falsification"
        )
        self.assertEqual(artifact["status"], "OBLIGATION_REQUIRED", artifact)
        self.assertEqual(artifact["profile_family"], "MACHINE_LEARNING")

    def test_producer_identity_is_required_keyword_only_context(self):
        runtime = self.runtime()
        with self.assertRaises(TypeError):
            runtime.derive_obligation(claim(), profile())
        with self.assertRaises(TypeError):
            runtime.derive_obligation(
                claim(), profile(), "provider:falsification"
            )
        for producer_id in ("", "   ", None):
            with self.subTest(producer_id=producer_id):
                result = runtime.derive_obligation(
                    claim(), profile(), producer_id=producer_id
                )
                self.assertEqual(result["status"], "OBLIGATION_REJECTED")

    def test_claim_payload_cannot_choose_or_forge_producer_identity(self):
        runtime = self.runtime()
        forged_claim = claim(obligation_producer_id="attacker:producer")
        artifact = runtime.derive_obligation(
            forged_claim,
            profile(),
            producer_id="trusted:producer",
        )
        self.assertEqual(artifact["status"], "OBLIGATION_REQUIRED")
        self.assertEqual(artifact["producer_id"], "trusted:producer")

    def test_conflicted_stale_or_invalid_profile_is_rejected(self):
        runtime = self.runtime()
        conflicted = profile()
        conflicted["status"] = "PROFILE_CONFLICT"
        stale = profile()
        stale["recommended"].append("changed-after-resolution")
        invalid = profile()
        invalid["canonical_output_hash"] = "not-a-hash"
        for value in (conflicted, stale, invalid):
            with self.subTest(value=value):
                artifact = runtime.derive_obligation(
                    claim(), value, producer_id="provider:falsification"
                )
                self.assertEqual(artifact["status"], "OBLIGATION_REJECTED")
                self.assertFalse(artifact["required"])

    def test_self_signed_profile_cannot_replace_trusted_family_or_required_dimensions(self):
        runtime = self.runtime()
        trusted = profile(domain="theory", study_type="theory")
        family_swap = copy.deepcopy(trusted)
        family_swap["domain"] = "systems"
        family_swap["study_type"] = "engineering-system"
        family_swap["canonical_output_hash"] = canonical_hash(
            {key: value for key, value in family_swap.items() if key != "canonical_output_hash"}
        )
        deleted_requirement = copy.deepcopy(trusted)
        deleted_requirement["required"] = []
        deleted_requirement["canonical_output_hash"] = canonical_hash(
            {key: value for key, value in deleted_requirement.items() if key != "canonical_output_hash"}
        )
        forged_source = copy.deepcopy(trusted)
        forged_source["source_profile_id"] = "attacker:profile"
        forged_source["canonical_output_hash"] = canonical_hash(
            {key: value for key, value in forged_source.items() if key != "canonical_output_hash"}
        )
        for candidate in (family_swap, deleted_requirement, forged_source):
            with self.subTest(candidate=candidate):
                result = runtime.derive_obligation(
                    claim(), candidate, producer_id="provider:falsification"
                )
                self.assertEqual(result["status"], "OBLIGATION_REJECTED")

    def test_forged_or_stale_registry_snapshot_is_rejected(self):
        runtime = self.runtime()
        trusted = profile()
        forged_id = copy.deepcopy(trusted)
        forged_id["applied_profile_ids"] = ["attacker:profile"]
        rehash_profile(forged_id)

        stale_snapshot = copy.deepcopy(trusted)
        stale_snapshot["canonical_input"]["profiles"][0]["source_hash"] = "0" * 64
        stale_snapshot["canonical_input_hash"] = canonical_hash(
            stale_snapshot["canonical_input"]
        ).removeprefix("sha256:")
        rehash_profile(stale_snapshot)

        for candidate in (forged_id, stale_snapshot):
            with self.subTest(candidate=candidate):
                result = runtime.derive_obligation(
                    claim(), candidate, producer_id="provider:falsification"
                )
                self.assertEqual(result["status"], "OBLIGATION_REJECTED")

    def test_self_consistent_registry_rewrite_without_manifest_update_is_rejected(self):
        runtime = self.runtime()
        resolver_spec = importlib.util.spec_from_file_location(
            "publication_profiles_registry_attack",
            ROOT / "scripts" / "publication_profiles.py",
        )
        self.assertIsNotNone(resolver_spec)
        self.assertIsNotNone(resolver_spec.loader)
        resolver = importlib.util.module_from_spec(resolver_spec)
        resolver_spec.loader.exec_module(resolver)

        registry_path = ROOT / "assets" / "registry" / "publication_profiles.json"
        forged_registry = json.loads(registry_path.read_text(encoding="utf-8"))
        fallback = next(
            item
            for item in forged_registry["profiles"]
            if item["profile_id"] == "fallback:full-paper"
        )
        fallback["required"] = []
        fallback["source_payload"]["required"] = []
        forged_source_hash = canonical_hash(fallback["source_payload"]).removeprefix(
            "sha256:"
        )
        fallback["source_hash"] = forged_source_hash
        fallback["provenance"]["source_hash"] = forged_source_hash
        forged_profile = resolver.resolve_profile(
            {"domain": "machine-learning", "study_type": "ml-benchmark"},
            forged_registry["profiles"],
        )
        self.assertEqual(forged_profile["status"], "PROFILE_RESOLVED")

        forged_registry_bytes = json.dumps(forged_registry).encode("utf-8")
        original_read_text = Path.read_text
        original_read_bytes = Path.read_bytes

        def forged_read_text(path, *args, **kwargs):
            if path.resolve() == registry_path.resolve():
                return forged_registry_bytes.decode("utf-8")
            return original_read_text(path, *args, **kwargs)

        def forged_read_bytes(path, *args, **kwargs):
            if path.resolve() == registry_path.resolve():
                return forged_registry_bytes
            return original_read_bytes(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", new=forged_read_text), mock.patch.object(
            Path, "read_bytes", new=forged_read_bytes
        ):
            result = runtime.derive_obligation(
                claim(), forged_profile, producer_id="provider:falsification"
            )
        self.assertEqual(result["status"], "OBLIGATION_REJECTED")
        self.assertEqual(result["error_code"], "UNTRUSTED_PROFILE")

    def test_joint_registry_manifest_and_provenance_rewrite_is_rejected(self):
        runtime = self.runtime()
        resolver_spec = importlib.util.spec_from_file_location(
            "publication_profiles_joint_attack",
            ROOT / "scripts" / "publication_profiles.py",
        )
        self.assertIsNotNone(resolver_spec)
        self.assertIsNotNone(resolver_spec.loader)
        resolver = importlib.util.module_from_spec(resolver_spec)
        resolver_spec.loader.exec_module(resolver)

        registry_path = ROOT / "assets" / "registry" / "publication_profiles.json"
        manifest_path = ROOT / "SHA256SUMS.txt"
        forged_registry = json.loads(registry_path.read_text(encoding="utf-8"))
        fallback = next(
            item
            for item in forged_registry["profiles"]
            if item["profile_id"] == "fallback:full-paper"
        )
        fallback["required"] = []
        fallback["source_payload"]["required"] = []
        forged_source_hash = resolver.canonical_hash(fallback["source_payload"])
        fallback["source_hash"] = forged_source_hash
        fallback["provenance"]["source_hash"] = forged_source_hash
        forged_registry_bytes = (
            json.dumps(forged_registry, indent=2, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        forged_registry_hash = hashlib.sha256(forged_registry_bytes).hexdigest()
        forged_manifest = "\n".join(
            forged_registry_hash + "  assets/registry/publication_profiles.json"
            if line.endswith("  assets/registry/publication_profiles.json")
            else line
            for line in manifest_path.read_text(encoding="utf-8").splitlines()
        ) + "\n"
        forged_profile = resolver.resolve_profile(
            {"domain": "machine-learning", "study_type": "ml-benchmark"},
            forged_registry["profiles"],
        )
        self.assertEqual(forged_profile["status"], "PROFILE_RESOLVED")

        original_read_text = Path.read_text
        original_read_bytes = Path.read_bytes

        def forged_read_text(path, *args, **kwargs):
            if path.resolve() == registry_path.resolve():
                return forged_registry_bytes.decode("utf-8")
            if path.resolve() == manifest_path.resolve():
                return forged_manifest
            return original_read_text(path, *args, **kwargs)

        def forged_read_bytes(path, *args, **kwargs):
            if path.resolve() == registry_path.resolve():
                return forged_registry_bytes
            return original_read_bytes(path, *args, **kwargs)

        with mock.patch.object(Path, "read_text", new=forged_read_text), mock.patch.object(
            Path, "read_bytes", new=forged_read_bytes
        ):
            result = runtime.derive_obligation(
                claim(), forged_profile, producer_id="provider:falsification"
            )
        attack_record = {
            "registry_sha256": forged_registry_hash,
            "manifest_sha256": hashlib.sha256(
                forged_manifest.encode("utf-8")
            ).hexdigest(),
            "actual_status": result.get("status"),
            "actual_error_code": result.get("error_code"),
        }
        self.assertEqual(
            result["status"],
            "OBLIGATION_REJECTED",
            json.dumps(attack_record, sort_keys=True),
        )
        self.assertEqual(result["error_code"], "UNTRUSTED_PROFILE")

    def test_profile_cannot_be_reused_across_claim_research_scope(self):
        runtime = self.runtime()
        result = runtime.derive_obligation(
            claim(domain="systems", study_type="engineering-system"),
            profile(domain="theory", study_type="theory"),
            producer_id="provider:falsification",
        )
        self.assertEqual(result["status"], "OBLIGATION_REJECTED")

    def test_public_core_default_path_remains_available(self):
        runtime = self.runtime()
        artifact = runtime.derive_obligation(
            claim(), profile(), producer_id="PUBLIC_CORE:falsification"
        )
        self.assertEqual(artifact["status"], "OBLIGATION_REQUIRED")
        self.assertEqual(artifact["producer_id"], "PUBLIC_CORE:falsification")

    def test_non_mapping_public_inputs_are_structured_rejections(self):
        runtime = self.runtime()
        valid_claim = claim()
        valid_profile = profile()
        for value in (None, "text", 7, False, [], ["x"]):
            with self.subTest(input_name="claim", value=value):
                result = runtime.derive_obligation(
                    value, valid_profile, producer_id="provider:falsification"
                )
                self.assertEqual(result["status"], "OBLIGATION_REJECTED")
            with self.subTest(input_name="profile", value=value):
                result = runtime.derive_obligation(
                    valid_claim, value, producer_id="provider:falsification"
                )
                self.assertEqual(result["status"], "OBLIGATION_REJECTED")

        artifact = runtime.derive_obligation(
            valid_claim, valid_profile, producer_id="provider:falsification"
        )
        evidence = evidence_for(artifact)
        for value in (None, "text", 7, False, [], ["x"]):
            with self.subTest(input_name="artifact", value=value):
                result = runtime.check_obligation(
                    value,
                    evidence,
                    producer_id="provider:falsification",
                    checker_id="checker:falsification",
                )
                self.assertEqual(result["status"], "OBLIGATION_REJECTED")
            with self.subTest(input_name="evidence", value=value):
                result = runtime.check_obligation(
                    artifact,
                    value,
                    producer_id="provider:falsification",
                    checker_id="checker:falsification",
                )
                self.assertEqual(result["status"], "OBLIGATION_REJECTED")

    def test_invalid_nested_claim_fields_are_structured_rejections(self):
        runtime = self.runtime()
        for candidate in (
            claim(claim_id=""),
            claim(load_bearing=[]),
            claim(strength={}),
        ):
            with self.subTest(candidate=candidate):
                result = runtime.derive_obligation(
                    candidate, profile(), producer_id="provider:falsification"
                )
                self.assertEqual(result["status"], "OBLIGATION_REJECTED")
                self.assertEqual(result["error_code"], "INVALID_CLAIM")

    def test_checker_is_distinct_and_does_not_mutate_inputs(self):
        runtime = self.runtime()
        context = authority_context(runtime)
        artifact = runtime._derive_obligation_with_context(
            context, producer_id="provider:falsification"
        )
        evidence = evidence_for(artifact)
        artifact_before = copy.deepcopy(artifact)
        evidence_before = copy.deepcopy(evidence)
        result = runtime._check_obligation_with_context(
            artifact,
            evidence,
            producer_id="provider:falsification",
            checker_id="provider:falsification",
            authority_context=context,
        )
        self.assertEqual(result["status"], "OBLIGATION_REJECTED")
        self.assertEqual(artifact, artifact_before)
        self.assertEqual(evidence, evidence_before)

    def test_missing_evidence_fails_and_partial_evidence_is_conditional(self):
        runtime = self.runtime()
        context = authority_context(runtime)
        artifact = runtime._derive_obligation_with_context(
            context, producer_id="provider:falsification"
        )
        missing = runtime._check_obligation_with_context(
            artifact,
            {},
            producer_id="provider:falsification",
            checker_id="checker:falsification",
            authority_context=context,
        )
        partial = runtime._check_obligation_with_context(
            artifact,
            evidence_for(artifact, include={"confirmation_test"}),
            producer_id="provider:falsification",
            checker_id="checker:falsification",
            authority_context=context,
        )
        self.assertEqual(missing["status"], "OBLIGATION_FAILED")
        self.assertEqual(partial["status"], "OBLIGATION_CONDITIONAL")
        self.assertIn("falsification_attempt", partial["missing_evidence"])

    def test_observed_evidence_requires_a_nonempty_summary(self):
        runtime = self.runtime()
        context = authority_context(runtime)
        artifact = runtime._derive_obligation_with_context(
            context, producer_id="provider:falsification"
        )
        for summary in ("", "   ", None, 7, False, [], {}):
            with self.subTest(summary=summary):
                evidence = evidence_for(artifact)
                evidence["checks"]["confirmation_test"]["summary"] = summary
                result = runtime._check_obligation_with_context(
                    artifact,
                    evidence,
                    producer_id="provider:falsification",
                    checker_id="checker:falsification",
                    authority_context=context,
                )
                self.assertEqual(result["status"], "OBLIGATION_CONDITIONAL")
                self.assertIn("confirmation_test", result["missing_evidence"])

    def test_checker_rejects_rehashed_semantic_artifact_tampering(self):
        runtime = self.runtime()
        context = authority_context(runtime)
        artifact = runtime._derive_obligation_with_context(
            context, producer_id="provider:falsification"
        )
        mutations = {
            "status": lambda value: value.__setitem__("status", "NOT_REQUIRED"),
            "required": lambda value: value.__setitem__("required", False),
            "operation": lambda value: value.__setitem__("operation", "attacker-operation"),
            "claim_id": lambda value: value.__setitem__("claim_id", ""),
        }
        for field in (
            "confirmation_test",
            "falsification_attempt",
            "boundary_condition_test",
            "strongest_surviving_alternative",
            "residual_confidence",
        ):
            mutations[f"{field}.description"] = (
                lambda value, field=field: value[field].__setitem__(
                    "description", "Attacker-rewritten check."
                )
            )

        for path, mutate in mutations.items():
            with self.subTest(path=path):
                tampered = copy.deepcopy(artifact)
                mutate(tampered)
                unsigned = {
                    key: value
                    for key, value in tampered.items()
                    if key != "obligation_hash"
                }
                tampered["obligation_hash"] = canonical_hash(unsigned)
                result = runtime._check_obligation_with_context(
                    tampered,
                    evidence_for(tampered),
                    producer_id="provider:falsification",
                    checker_id="checker:falsification",
                    authority_context=context,
                )
                self.assertEqual(result["status"], "OBLIGATION_REJECTED")

    def test_checker_rejects_rehashed_claim_and_profile_rebinding(self):
        runtime = self.runtime()
        context = authority_context(runtime)
        artifact = runtime._derive_obligation_with_context(
            context, producer_id="provider:falsification"
        )
        replacements = {
            "claim_id": "C-ATTACKER",
            "claim_hash": canonical_hash(claim(claim_id="C-ATTACKER")),
            "profile_hash": "sha256:" + "a" * 64,
        }
        for field, replacement in replacements.items():
            with self.subTest(field=field):
                tampered = copy.deepcopy(artifact)
                tampered[field] = replacement
                unsigned = {
                    key: value
                    for key, value in tampered.items()
                    if key != "obligation_hash"
                }
                tampered["obligation_hash"] = canonical_hash(unsigned)
                result = runtime._check_obligation_with_context(
                    tampered,
                    evidence_for(tampered),
                    producer_id="provider:falsification",
                    checker_id="checker:falsification",
                    authority_context=context,
                )
                self.assertEqual(result["status"], "OBLIGATION_REJECTED")

    def test_original_reviewer_payload_fails_closed_without_control_plane_context(self):
        runtime = self.runtime()
        trusted_claim = claim()
        trusted_profile = profile()
        artifact = runtime.derive_obligation(
            trusted_claim,
            trusted_profile,
            producer_id="provider:falsification",
        )
        self.assertEqual(
            artifact["obligation_hash"],
            "sha256:88c03979b0a94f057f0934616565405daf4fdf959c556a7820483f4593dce625",
        )
        baseline_result = runtime.check_obligation(
            artifact,
            evidence_for(artifact),
            producer_id="provider:falsification",
            checker_id="checker:falsification",
        )
        self.assertEqual(baseline_result["status"], "OBLIGATION_REJECTED")
        self.assertEqual(
            baseline_result["error_code"], "UNTRUSTED_CHECK_CONTEXT"
        )
        attacks = {
            "status": (
                lambda value: (
                    value.__setitem__("status", "NOT_REQUIRED"),
                    value.__setitem__("required", False),
                ),
                "sha256:1cefc900c1ab003929d1b2f93cefcf4c041db79ad33f8b3b5d6cb2e7f9d58ce9",
            ),
            "operation": (
                lambda value: value.__setitem__("operation", "attacker-operation"),
                "sha256:bd36ee668c86e2ee791e7c27599a6d06e132b36623969800fff7453bf971414b",
            ),
            "check_id": (
                lambda value: value["confirmation_test"].__setitem__(
                    "check_id", ""
                ),
                "sha256:dd32864f97cad7b8b2015a9af1a7a481b8425729a32c3119c25e9a5f852c3e39",
            ),
            "description": (
                lambda value: value["confirmation_test"].__setitem__(
                    "description", ""
                ),
                "sha256:0765a9a3336fc80736620793bcd01a70df84f9886bc63fab852a365f46533fc8",
            ),
            "claim_id": (
                lambda value: value.__setitem__("claim_id", ""),
                "sha256:33bd2ecdf3988dcae452872be8bb61584b9298b31c0ceb42859ddf5c425cbd07",
            ),
        }
        for label, (mutate, expected_hash) in attacks.items():
            with self.subTest(label=label):
                tampered = copy.deepcopy(artifact)
                mutate(tampered)
                unsigned = {
                    key: value
                    for key, value in tampered.items()
                    if key != "obligation_hash"
                }
                tampered["obligation_hash"] = canonical_hash(unsigned)
                self.assertEqual(tampered["obligation_hash"], expected_hash)
                result = runtime.check_obligation(
                    tampered,
                    evidence_for(tampered),
                    producer_id="provider:falsification",
                    checker_id="checker:falsification",
                )
                self.assertEqual(result["status"], "OBLIGATION_REJECTED")
                self.assertEqual(result["error_code"], "UNTRUSTED_CHECK_CONTEXT")

    def test_complete_bound_evidence_is_verified_without_truth_authority(self):
        runtime = self.runtime()
        context = authority_context(runtime)
        artifact = runtime._derive_obligation_with_context(
            context, producer_id="provider:falsification"
        )
        result = runtime._check_obligation_with_context(
            artifact,
            evidence_for(artifact),
            producer_id="provider:falsification",
            checker_id="checker:falsification",
            authority_context=context,
        )
        self.assertEqual(result["status"], "OBLIGATION_VERIFIED")
        self.assertEqual(result["checker_id"], "checker:falsification")
        self.assertFalse(result["claim_status_change_authorized"])
        self.assertFalse(result["evidence_upgrade_authorized"])
        self.assertFalse(result["graph_transition_authorized"])
        self.assertFalse(result["publication_pass"])
        self.assertNotIn("PASS", json.dumps(result, sort_keys=True))

    def test_checker_requires_trusted_claim_and_profile_context(self):
        runtime = self.runtime()
        artifact = runtime.derive_obligation(
            claim(), profile(), producer_id="provider:falsification"
        )
        evidence = evidence_for(artifact)
        for trusted_claim, trusted_profile in (
            (None, profile()),
            (claim(), None),
            ("claim", profile()),
            (claim(), ["profile"]),
        ):
            with self.subTest(
                trusted_claim=trusted_claim, trusted_profile=trusted_profile
            ):
                result = runtime.check_obligation(
                    artifact,
                    evidence,
                    producer_id="provider:falsification",
                    checker_id="checker:falsification",
                    trusted_claim=trusted_claim,
                    trusted_profile=trusted_profile,
                )
                self.assertEqual(result["status"], "OBLIGATION_REJECTED")
                self.assertEqual(result["error_code"], "UNTRUSTED_CHECK_CONTEXT")

    def test_checker_does_not_accept_caller_named_dicts_as_authority(self):
        runtime = self.runtime()
        trusted_profile = profile()
        forged_claim = claim(claim_id="C-ATTACKER")
        artifact = runtime.derive_obligation(
            forged_claim,
            trusted_profile,
            producer_id="provider:falsification",
        )
        result = runtime.check_obligation(
            artifact,
            evidence_for(artifact),
            producer_id="provider:falsification",
            checker_id="checker:falsification",
            trusted_claim=forged_claim,
            trusted_profile=trusted_profile,
        )
        self.assertEqual(result["status"], "OBLIGATION_REJECTED")
        self.assertEqual(result["error_code"], "UNTRUSTED_CHECK_CONTEXT")

    def test_public_checker_does_not_accept_caller_constructed_sealed_context(self):
        runtime = self.runtime()
        forged_claim = claim(claim_id="C-ATTACKER")
        trusted_profile = profile()
        artifact = runtime.derive_obligation(
            forged_claim,
            trusted_profile,
            producer_id="provider:falsification",
        )
        forged_context = runtime._sealed_context(
            forged_claim,
            trusted_profile,
            runtime.canonical_hash({"attacker": "controlled"}),
        )
        result = runtime.check_obligation(
            artifact,
            evidence_for(artifact),
            producer_id="provider:falsification",
            checker_id="checker:falsification",
            authority_context=forged_context,
        )
        self.assertEqual(result["status"], "OBLIGATION_REJECTED")
        self.assertEqual(result["error_code"], "UNTRUSTED_CHECK_CONTEXT")

    def test_formal_project_entry_loads_context_and_rejects_real_claim_rebinding(self):
        runtime = self.runtime()
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            state = project / ".research-state"
            state.mkdir(parents=True)
            (state / "project.json").write_text(
                json.dumps(
                    {
                        "schema_version": 3,
                        "skill_version": "4.1.0",
                        "project_dir": str(project.resolve()),
                        "domain": "machine-learning",
                        "study_type": "ml-benchmark",
                    }
                ),
                encoding="utf-8",
            )
            (state / "research_contract.json").write_text(
                json.dumps(
                    {
                        "schema_version": 3,
                        "skill_version": "4.1.0",
                        "project": {
                            "domain": "machine-learning",
                            "study_type": "ml-benchmark",
                        },
                    }
                ),
                encoding="utf-8",
            )
            claims = {
                "schema_version": 1,
                "skill_version": "4.1.0",
                "claims": [
                    {
                        "id": "C-001",
                        "text": "The method generalizes beyond the development benchmark.",
                        "strength": "HIGH",
                        "load_bearing": True,
                    },
                    {
                        "id": "C-002",
                        "text": "A different real claim in the same project.",
                        "strength": "HIGH",
                        "load_bearing": True,
                    },
                ],
            }
            claims_path = state / "claims.json"
            claims_path.write_text(json.dumps(claims), encoding="utf-8")

            baseline = runtime.derive_project_obligation(
                project,
                "C-001",
                producer_id="provider:falsification",
            )
            self.assertRegex(
                baseline.get("authority_snapshot_hash", ""),
                r"^sha256:[0-9a-f]{64}$",
            )
            baseline_evidence = evidence_for(baseline)
            baseline_result = runtime.check_project_obligation(
                project,
                "C-001",
                baseline,
                baseline_evidence,
                producer_id="provider:falsification",
                checker_id="checker:falsification",
            )
            self.assertEqual(baseline_result["status"], "OBLIGATION_VERIFIED")

            for malformed_artifact, malformed_evidence in (
                (None, baseline_evidence),
                (baseline, None),
            ):
                with self.subTest(
                    malformed_artifact=malformed_artifact,
                    malformed_evidence=malformed_evidence,
                ):
                    malformed_result = runtime.check_project_obligation(
                        project,
                        "C-001",
                        malformed_artifact,
                        malformed_evidence,
                        producer_id="provider:falsification",
                        checker_id="checker:falsification",
                    )
                    self.assertEqual(
                        malformed_result["status"], "OBLIGATION_REJECTED"
                    )
                    self.assertEqual(
                        malformed_result["error_code"], "INVALID_INPUT_TYPE"
                    )

            malformed_artifact = copy.deepcopy(baseline)
            malformed_artifact["confirmation_test"] = []
            malformed_artifact["obligation_hash"] = runtime.canonical_hash(
                {
                    key: value
                    for key, value in malformed_artifact.items()
                    if key != "obligation_hash"
                }
            )
            malformed_artifact_result = runtime.check_project_obligation(
                project,
                "C-001",
                malformed_artifact,
                evidence_for(malformed_artifact),
                producer_id="provider:falsification",
                checker_id="checker:falsification",
            )
            self.assertEqual(
                malformed_artifact_result["status"], "OBLIGATION_REJECTED"
            )

            malformed_evidence = copy.deepcopy(baseline_evidence)
            malformed_evidence["checks"] = []
            malformed_evidence_result = runtime.check_project_obligation(
                project,
                "C-001",
                baseline,
                malformed_evidence,
                producer_id="provider:falsification",
                checker_id="checker:falsification",
            )
            self.assertEqual(
                malformed_evidence_result["status"], "OBLIGATION_FAILED"
            )

            replacements = {
                "claim_id": "C-ATTACKER-NONEMPTY",
                "claim_hash": runtime.canonical_hash(
                    claim(claim_id="C-ATTACKER-NONEMPTY")
                ),
                "profile_hash": profile(
                    domain="software-engineering", study_type="empirical"
                )["canonical_output_hash"],
            }
            for field, replacement in replacements.items():
                with self.subTest(rebinding_field=field):
                    tampered = copy.deepcopy(baseline)
                    tampered[field] = replacement
                    tampered["obligation_hash"] = runtime.canonical_hash(
                        {
                            key: value
                            for key, value in tampered.items()
                            if key != "obligation_hash"
                        }
                    )
                    rebound_field = runtime.check_project_obligation(
                        project,
                        "C-001",
                        tampered,
                        evidence_for(tampered),
                        producer_id="provider:falsification",
                        checker_id="checker:falsification",
                    )
                    self.assertEqual(
                        rebound_field["status"], "OBLIGATION_REJECTED"
                    )
                    self.assertEqual(
                        rebound_field["error_code"],
                        "OBLIGATION_BINDING_MISMATCH",
                    )

            other_claim = runtime.derive_project_obligation(
                project,
                "C-002",
                producer_id="provider:falsification",
            )
            rebound = runtime.check_project_obligation(
                project,
                "C-001",
                other_claim,
                evidence_for(other_claim),
                producer_id="provider:falsification",
                checker_id="checker:falsification",
            )
            self.assertEqual(rebound["status"], "OBLIGATION_REJECTED")
            self.assertEqual(rebound["error_code"], "OBLIGATION_BINDING_MISMATCH")

            claims["claims"][1]["text"] = "Unrelated authoritative state changed."
            claims_path.write_text(json.dumps(claims), encoding="utf-8")
            stale = runtime.check_project_obligation(
                project,
                "C-001",
                baseline,
                evidence_for(baseline),
                producer_id="provider:falsification",
                checker_id="checker:falsification",
            )
            self.assertEqual(stale["status"], "OBLIGATION_REJECTED")
            self.assertEqual(stale["error_code"], "OBLIGATION_BINDING_MISMATCH")

    def test_checker_requires_nonblank_matching_producer_context(self):
        runtime = self.runtime()
        artifact = runtime.derive_obligation(
            claim(), profile(), producer_id="trusted:producer"
        )
        evidence = evidence_for(artifact)
        with self.assertRaises(TypeError):
            runtime.check_obligation(
                artifact, evidence, checker_id="checker:falsification"
            )
        for producer_id in ("", "   ", "forged:producer", None):
            with self.subTest(producer_id=producer_id):
                result = runtime.check_obligation(
                    artifact,
                    evidence,
                    producer_id=producer_id,
                    checker_id="checker:falsification",
                )
                self.assertEqual(result["status"], "OBLIGATION_REJECTED")

    def test_checker_rejects_every_non_false_authority_field(self):
        runtime = self.runtime()
        context = authority_context(runtime)
        artifact = runtime._derive_obligation_with_context(
            context, producer_id="provider:falsification"
        )
        evidence = evidence_for(artifact)
        fields = (
            "claim_status_change_authorized",
            "evidence_upgrade_authorized",
            "graph_transition_authorized",
            "publication_pass",
        )
        for field in fields:
            for value in (True, 0, "false", None):
                with self.subTest(field=field, value=value):
                    tampered = copy.deepcopy(artifact)
                    tampered[field] = value
                    unsigned = {
                        key: item
                        for key, item in tampered.items()
                        if key != "obligation_hash"
                    }
                    tampered["obligation_hash"] = canonical_hash(unsigned)
                    bound_evidence = evidence_for(tampered)
                    result = runtime._check_obligation_with_context(
                        tampered,
                        bound_evidence,
                        producer_id="provider:falsification",
                        checker_id="checker:falsification",
                        authority_context=context,
                    )
                    self.assertEqual(result["status"], "OBLIGATION_REJECTED")

        missing = copy.deepcopy(artifact)
        missing.pop("publication_pass")
        unsigned = {
            key: value for key, value in missing.items() if key != "obligation_hash"
        }
        missing["obligation_hash"] = canonical_hash(unsigned)
        self.assertEqual(
            runtime._check_obligation_with_context(
                missing,
                evidence_for(missing),
                producer_id="provider:falsification",
                checker_id="checker:falsification",
                authority_context=context,
            )["status"],
            "OBLIGATION_REJECTED",
        )

    def test_tampered_artifact_or_evidence_binding_is_rejected(self):
        runtime = self.runtime()
        context = authority_context(runtime)
        artifact = runtime._derive_obligation_with_context(
            context, producer_id="provider:falsification"
        )
        tampered_artifact = copy.deepcopy(artifact)
        tampered_artifact["confirmation_test"]["description"] = "weakened"
        evidence = evidence_for(artifact)
        wrong_binding = copy.deepcopy(evidence)
        wrong_binding["claim_hash"] = "sha256:" + "0" * 64
        self.assertEqual(
            runtime._check_obligation_with_context(
                tampered_artifact,
                evidence,
                checker_id="checker:falsification",
                producer_id="provider:falsification",
                authority_context=context,
            )["status"],
            "OBLIGATION_REJECTED",
        )
        self.assertEqual(
            runtime._check_obligation_with_context(
                artifact,
                wrong_binding,
                checker_id="checker:falsification",
                producer_id="provider:falsification",
                authority_context=context,
            )["status"],
            "OBLIGATION_REJECTED",
        )

    def test_schema_and_template_preserve_authority_boundaries(self):
        schema_path = ROOT / "assets" / "schemas" / "falsification_obligation.schema.json"
        template_path = ROOT / "assets" / "templates" / "falsification_obligation.json"
        self.assertTrue(schema_path.is_file())
        self.assertTrue(template_path.is_file())
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        template = json.loads(template_path.read_text(encoding="utf-8"))
        defined = next(
            branch
            for branch in schema["oneOf"]
            if branch["properties"]["status"].get("const") == "OBLIGATION_REQUIRED"
        )
        for field in (
            "confirmation_test",
            "falsification_attempt",
            "boundary_condition_test",
            "strongest_surviving_alternative",
            "residual_confidence",
            "claim_id",
            "claim_hash",
            "profile_hash",
            "obligation_hash",
            "producer_id",
        ):
            self.assertIn(field, defined["required"])
            self.assertIn(field, template)
        for field in (
            "claim_status_change_authorized",
            "evidence_upgrade_authorized",
            "graph_transition_authorized",
            "publication_pass",
        ):
            self.assertIn(field, schema["required"])
            self.assertEqual(schema["properties"][field]["const"], False)
            self.assertEqual(template[field], False)


if __name__ == "__main__":
    unittest.main()
