import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


publication = load("publication_sufficiency")
profiles = load("publication_profiles")


def publication_layer(layer_name, profile_id, *, overrides=None, **fields):
    overrides = overrides or []
    payload = {
        "required": sorted(set(fields.get("required", []))),
        "recommended": sorted(set(fields.get("recommended", []))),
        "not_applicable": sorted(set(fields.get("not_applicable", []))),
        "overrides": sorted(
            overrides,
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        ),
        **(
            {"na_justifications": fields["na_justifications"]}
            if "na_justifications" in fields
            else {}
        ),
    }
    source_hash = profiles.canonical_hash(payload)
    return {
        "profile_id": profile_id,
        "layer": layer_name,
        "version": "1.0.0",
        "status": "PROFILE_ACTIVE",
        "source_hash": source_hash,
        "source_payload": payload,
        "provenance": {
            "source_id": profile_id,
            "source_hash": source_hash,
            "profile_version": "1.0.0",
        },
        "required": fields.get("required", []),
        "recommended": fields.get("recommended", []),
        "not_applicable": fields.get("not_applicable", []),
        "overrides": [
            {
                **item,
                "source_id": profile_id,
                "source_hash": source_hash,
                "profile_version": "1.0.0",
            }
            for item in overrides
        ],
        **({"scope": fields["scope"]} if "scope" in fields else {}),
        **(
            {"na_justifications": fields["na_justifications"]}
            if "na_justifications" in fields
            else {}
        ),
    }


def trusted_profiles():
    registry = json.loads(
        (ROOT / "assets" / "registry" / "publication_profiles.json").read_text(
            encoding="utf-8"
        )
    )
    return registry["profiles"]


def resolved_registered_profile():
    result = profiles.resolve_profile(
        {"design": "registered-replication"}, trusted_profiles()
    )
    assert result["status"] == "PROFILE_RESOLVED", result
    return result


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
    def test_joint_registry_and_manifest_rewrite_cannot_authorize_submission(self):
        dimensions = list(publication.DEPTH_DIMENSIONS)
        forged_fallback = publication_layer(
            "fallback",
            "fallback:forged-empty",
            not_applicable=dimensions,
            na_justifications={
                dimension: "attacker-authored exemption" for dimension in dimensions
            },
        )
        forged_registry = {"profiles": [forged_fallback]}
        forged_registry_bytes = (
            json.dumps(forged_registry, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
        registry_path = ROOT / "assets" / "registry" / "publication_profiles.json"
        manifest_path = ROOT / "SHA256SUMS.txt"
        forged_digest = __import__("hashlib").sha256(forged_registry_bytes).hexdigest()
        forged_manifest = "\n".join(
            forged_digest + "  assets/registry/publication_profiles.json"
            if line.endswith("  assets/registry/publication_profiles.json")
            else line
            for line in manifest_path.read_text(encoding="utf-8").splitlines()
        ) + "\n"
        artifact = profiles.resolve_profile({}, forged_registry["profiles"])
        self.assertEqual(artifact["status"], "PROFILE_RESOLVED", artifact)

        real_read_bytes = Path.read_bytes
        real_read_text = Path.read_text

        def attacked_read_bytes(path):
            if path.resolve() == registry_path.resolve():
                return forged_registry_bytes
            return real_read_bytes(path)

        def attacked_read_text(path, *args, **kwargs):
            if path.resolve() == registry_path.resolve():
                return forged_registry_bytes.decode("utf-8")
            if path.resolve() == manifest_path.resolve():
                return forged_manifest
            return real_read_text(path, *args, **kwargs)

        with mock.patch.object(Path, "read_bytes", attacked_read_bytes), mock.patch.object(
            Path, "read_text", attacked_read_text
        ):
            result = publication.assess(
                {
                    "scientific_validity": "PASS",
                    "evidence_sufficiency": "PASS",
                    "reviewer_roles_completed": list(publication.REQUIRED_REVIEWERS),
                    "publication_profile": artifact,
                }
            )

        self.assertEqual(result["profile_resolution"]["status"], "PROFILE_CONFLICT")
        self.assertEqual(result["publication_sufficiency"]["status"], "FAIL")
        self.assertEqual(result["submission_readiness"]["status"], "FAIL")
        self.assertNotEqual(result["disposition"], "READY_FOR_SUBMISSION")

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

    def test_registered_non_fallback_profile_is_authoritatively_consumed(self):
        resolved_profile = resolved_registered_profile()
        complete = {
            "scientific_validity": "PASS", "evidence_sufficiency": "PASS",
            "dataset_count": 3, "dataset_kinds": ["benchmark", "real-world"],
            "model_count": 3, "modern_baseline_count": 4,
            "ablation_dimension_count": 3, "external_validation_count": 2,
            "mechanism_test_count": 2, "related_work_depth": "ADEQUATE",
            "manuscript_pages": 12, "reviewer_roles_completed": list(publication.REQUIRED_REVIEWERS),
            "publication_profile": resolved_profile,
        }
        result = publication.assess(complete)
        self.assertEqual(result["profile_resolution"]["status"], "PROFILE_RESOLVED")
        self.assertEqual(result["publication_sufficiency"]["status"], "FAIL")
        self.assertIn(
            "domain_specific_replication",
            result["research_depth_profile"]["failed_dimensions"],
        )

    def test_self_hashed_profile_without_replayable_provenance_is_rejected(self):
        forged = {
            "status": "PROFILE_RESOLVED",
            "required": ["mechanism_tests", "related_work", "manuscript_depth"],
            "recommended": [],
            "not_applicable": [
                "dataset_coverage",
                "model_coverage",
                "modern_baselines",
                "ablations",
                "external_validation",
            ],
            "na_justifications": {
                key: "self-authored exemption"
                for key in (
                    "dataset_coverage",
                    "model_coverage",
                    "modern_baselines",
                    "ablations",
                    "external_validation",
                )
            },
            "conflicts": [],
        }
        forged["canonical_output_hash"] = profiles.canonical_hash(forged)
        result = publication.assess(
            {
                "scientific_validity": "PASS",
                "evidence_sufficiency": "PASS",
                "mechanism_test_count": 1,
                "related_work_depth": "ADEQUATE",
                "manuscript_pages": 12,
                "reviewer_roles_completed": list(publication.REQUIRED_REVIEWERS),
                "publication_profile": forged,
            }
        )
        self.assertEqual(result["publication_sufficiency"]["status"], "FAIL")
        self.assertEqual(result["profile_resolution"]["status"], "PROFILE_CONFLICT")
        self.assertTrue(
            any(
                item["code"] == "UNREPLAYABLE_PROFILE_PROVENANCE"
                for item in result["profile_resolution"]["conflicts"]
            )
        )

    def test_replayed_profile_requires_the_shipped_trusted_fallback(self):
        untrusted = publication_layer(
            "fallback", "attacker:fallback", required=["mechanism_tests"]
        )
        artifact = profiles.resolve_profile({}, [untrusted])
        self.assertEqual(artifact["status"], "PROFILE_RESOLVED", artifact)
        result = publication.assess(
            {
                "scientific_validity": "PASS",
                "evidence_sufficiency": "PASS",
                "mechanism_test_count": 1,
                "reviewer_roles_completed": list(publication.REQUIRED_REVIEWERS),
                "publication_profile": artifact,
            }
        )
        self.assertEqual(result["profile_resolution"]["status"], "PROFILE_CONFLICT")
        self.assertTrue(
            any(
                item["code"] == "UNTRUSTED_FALLBACK"
                for item in result["profile_resolution"]["conflicts"]
            )
        )

    def test_trusted_fallback_does_not_trust_self_signed_design_exemptions(self):
        dimensions = list(publication.DEPTH_DIMENSIONS)
        overrides = [
            {
                "dimension": dimension,
                "from": "required",
                "to": "not_applicable",
                "justification": "self-signed exemption",
                "scope": {"design": "attacker-controlled"},
            }
            for dimension in dimensions
        ]
        design = publication_layer(
            "design",
            "design:self-signed-exemption",
            overrides=overrides,
            scope={"design": "attacker-controlled"},
        )
        artifact = profiles.resolve_profile(
            {"design": "attacker-controlled"}, trusted_profiles() + [design]
        )
        self.assertEqual(artifact["status"], "PROFILE_RESOLVED", artifact)
        self.assertEqual(artifact["required"], [])
        self.assertEqual(sorted(artifact["not_applicable"]), sorted(dimensions))

        result = publication.assess(
            {
                "scientific_validity": "PASS",
                "evidence_sufficiency": "PASS",
                "reviewer_roles_completed": list(publication.REQUIRED_REVIEWERS),
                "publication_profile": artifact,
            }
        )
        self.assertEqual(result["profile_resolution"]["status"], "PROFILE_CONFLICT")
        self.assertTrue(
            any(
                item["code"] == "UNTRUSTED_APPLIED_PROFILE"
                for item in result["profile_resolution"]["conflicts"]
            )
        )
        self.assertEqual(result["publication_sufficiency"]["status"], "FAIL")
        self.assertEqual(result["submission_readiness"]["status"], "FAIL")
        self.assertEqual(result["disposition"], "EXPAND_RESEARCH")

    def test_every_applied_non_fallback_profile_must_be_in_shipped_registry(self):
        overlay = publication_layer(
            "domain",
            "domain:self-signed",
            recommended=["untrusted_advice"],
            scope={"domain": "machine-learning"},
        )
        artifact = profiles.resolve_profile(
            {"domain": "machine-learning"}, trusted_profiles() + [overlay]
        )
        self.assertEqual(artifact["status"], "PROFILE_RESOLVED", artifact)
        result = publication.assess(
            {
                "publication_profile": artifact,
                "reviewer_roles_completed": list(publication.REQUIRED_REVIEWERS),
            }
        )
        self.assertEqual(result["profile_resolution"]["status"], "PROFILE_CONFLICT")
        self.assertTrue(
            any(
                item["code"] == "UNTRUSTED_APPLIED_PROFILE"
                for item in result["profile_resolution"]["conflicts"]
            )
        )

    def test_recomputed_self_hash_cannot_hide_replay_mismatch(self):
        artifact = resolved_registered_profile()
        artifact["required"] = []
        artifact["canonical_output_hash"] = profiles.canonical_hash(
            {key: value for key, value in artifact.items() if key != "canonical_output_hash"}
        )
        result = publication.assess(
            {
                "scientific_validity": "PASS",
                "evidence_sufficiency": "PASS",
                "reviewer_roles_completed": list(publication.REQUIRED_REVIEWERS),
                "publication_profile": artifact,
            }
        )
        self.assertEqual(result["profile_resolution"]["status"], "PROFILE_CONFLICT")
        self.assertTrue(
            any(
                item["code"] == "PROFILE_REPLAY_MISMATCH"
                for item in result["profile_resolution"]["conflicts"]
            )
        )

    def test_conflicted_profile_fails_closed(self):
        result = publication.assess({
            "scientific_validity": "PASS", "evidence_sufficiency": "PASS",
            "reviewer_roles_completed": list(publication.REQUIRED_REVIEWERS),
            "publication_profile": {"status": "PROFILE_CONFLICT", "conflicts": [{"code": "CROSS_CATEGORY_ASSIGNMENT"}]},
        })
        self.assertEqual(result["publication_sufficiency"]["status"], "FAIL")
        self.assertEqual(result["profile_resolution"]["status"], "PROFILE_CONFLICT")
        self.assertEqual(result["disposition"], "EXPAND_RESEARCH")

    def test_unknown_required_profile_dimension_fails_without_crashing(self):
        resolved_profile = resolved_registered_profile()
        self.assertEqual(resolved_profile["status"], "PROFILE_RESOLVED", resolved_profile)
        result = publication.assess({
            "scientific_validity": "PASS", "evidence_sufficiency": "PASS",
            "reviewer_roles_completed": list(publication.REQUIRED_REVIEWERS),
            "publication_profile": resolved_profile,
        })
        self.assertEqual(result["publication_sufficiency"]["status"], "FAIL")
        self.assertIn("domain_specific_replication", result["research_depth_profile"]["failed_dimensions"])
        self.assertTrue(any(item["dimension"] == "domain_specific_replication" for item in result["research_expansion_plan"]))

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
