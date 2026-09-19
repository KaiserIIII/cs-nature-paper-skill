import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("publication_profiles", ROOT / "scripts" / "publication_profiles.py")
publication_profiles = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(publication_profiles)


def layer(layer_name, profile_id, **kwargs):
    data = {
        "profile_id": profile_id,
        "layer": layer_name,
        "version": "1.0.0",
        "required": [],
        "recommended": [],
        "not_applicable": [],
        "overrides": [],
    }
    data.update(kwargs)
    effective_overrides = [
        {
            key: value
            for key, value in item.items()
            if key not in {"source_id", "source_hash", "profile_version"}
        }
        for item in data["overrides"]
    ]
    payload = data.get(
        "source_payload",
        {
            "required": sorted(set(data["required"])),
            "recommended": sorted(set(data["recommended"])),
            "not_applicable": sorted(set(data["not_applicable"])),
            "overrides": sorted(
                effective_overrides,
                key=lambda item: __import__("json").dumps(item, sort_keys=True),
            ),
            **(
                {"na_justifications": data["na_justifications"]}
                if "na_justifications" in data
                else {}
            ),
        },
    )
    data["source_payload"] = payload
    data.setdefault("source_hash", publication_profiles.canonical_hash(payload))
    data.setdefault("status", "PROFILE_ACTIVE")
    data.setdefault(
        "provenance",
        {
            "source_id": profile_id,
            "source_hash": data["source_hash"],
            "profile_version": data["version"],
        },
    )
    data["overrides"] = [
        {
            **item,
            "source_id": profile_id,
            "source_hash": data["source_hash"],
            "profile_version": data["version"],
        }
        for item in data["overrides"]
    ]
    return data


class PublicationProfileTests(unittest.TestCase):
    def test_non_mapping_request_or_non_list_profiles_fail_closed(self):
        cases = [
            (None, []),
            ([], []),
            ({}, None),
            ({}, {}),
        ]
        for request, profile_set in cases:
            with self.subTest(request=request, profiles=profile_set):
                result = publication_profiles.resolve_profile(request, profile_set)
                self.assertEqual(result["status"], "PROFILE_CONFLICT")
                self.assertTrue(
                    any(
                        item["code"] == "INVALID_RESOLUTION_INPUT"
                        for item in result["conflicts"]
                    )
                )

    def test_deprecated_profile_is_rejected(self):
        for value in (
            layer("fallback", "fallback", status="PROFILE_DEPRECATED"),
            layer(
                "domain",
                "deprecated:unmatched",
                status="PROFILE_DEPRECATED",
                scope={"domain": "other"},
            ),
        ):
            with self.subTest(profile_id=value["profile_id"]):
                result = publication_profiles.resolve_profile(
                    {"domain": "machine-learning"},
                    [layer("fallback", "fallback"), value],
                )
                self.assertEqual(result["status"], "PROFILE_CONFLICT")
                self.assertTrue(
                    any(
                        item["code"] == "PROFILE_DEPRECATED"
                        for item in result["conflicts"]
                    )
                )

    def test_missing_or_mismatched_profile_provenance_is_rejected(self):
        missing = layer("fallback", "fallback")
        missing.pop("provenance")
        mismatched = layer("fallback", "fallback")
        mismatched["provenance"]["source_id"] = "forged"
        extra = layer("fallback", "fallback")
        extra["provenance"]["trusted"] = True
        for value, code in (
            (missing, "MISSING_PROFILE_PROVENANCE"),
            (mismatched, "PROFILE_PROVENANCE_MISMATCH"),
            (extra, "PROFILE_PROVENANCE_MISMATCH"),
        ):
            with self.subTest(code=code):
                result = publication_profiles.resolve_profile({}, [value])
                self.assertEqual(result["status"], "PROFILE_CONFLICT")
                self.assertTrue(
                    any(item["code"] == code for item in result["conflicts"])
                )

    def test_empty_profiles_or_missing_fallback_fail_closed(self):
        for profiles in ([], [layer("domain", "domain:ml", required=["x"]) ]):
            with self.subTest(profiles=profiles):
                result = publication_profiles.resolve_profile({"domain": "ml"}, profiles)
                self.assertEqual(result["status"], "PROFILE_CONFLICT")
                self.assertTrue(
                    any(item["code"] == "MISSING_FALLBACK" for item in result["conflicts"])
                )

    def test_layers_follow_fixed_specificity_order_and_are_repeatable(self):
        profiles = [layer("design", "design", recommended=["d"]), layer("fallback", "fallback", required=["base"]), layer("venue", "venue", recommended=["v"]), layer("domain", "domain", required=["domain"]), layer("study_type", "study", recommended=["study"]), layer("claim_type", "claim", recommended=["claim"]), layer("article_type", "article", recommended=["article"])]
        request = {"domain": "ml", "study_type": "benchmark", "claim_type": "generalization", "venue": "nature", "article_type": "article", "design": "empirical"}
        first = publication_profiles.resolve_profile(request, profiles)
        second = publication_profiles.resolve_profile(request, list(reversed(profiles)))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PROFILE_RESOLVED")
        self.assertEqual(first["applied_profile_ids"], ["fallback", "domain", "study", "claim", "venue", "article", "design"])
        self.assertEqual(first["required"], ["base", "domain"])
        self.assertEqual(first["recommended"], ["article", "claim", "d", "study", "v"])
        self.assertEqual(first["canonical_input_hash"], publication_profiles.canonical_hash(first["canonical_input"]))
        self.assertEqual(first["canonical_output_hash"], publication_profiles.canonical_hash({k: v for k, v in first.items() if k != "canonical_output_hash"}))
        self.assertEqual(first["domain"], "ml")
        self.assertEqual(first["study_type"], "benchmark")

    def test_unmatched_scoped_profile_is_not_applied(self):
        profiles = [
            layer("fallback", "fallback", required=["base"]),
            layer("domain", "ml", scope={"domain": "machine-learning"}, required=["ml-only"]),
            layer("domain", "systems", scope={"domain": "systems"}, required=["systems-only"]),
        ]
        result = publication_profiles.resolve_profile({"domain": "systems"}, profiles)
        self.assertEqual(result["status"], "PROFILE_RESOLVED")
        self.assertEqual(result["applied_profile_ids"], ["fallback", "systems"])
        self.assertEqual(result["required"], ["base", "systems-only"])

    def test_cross_category_dimension_conflict_fails_closed_without_override(self):
        result = publication_profiles.resolve_profile({}, [layer("fallback", "f", required=["x"]), layer("domain", "d", recommended=["x"])])
        self.assertEqual(result["status"], "PROFILE_CONFLICT")
        self.assertTrue(any(item["dimension"] == "x" for item in result["conflicts"]))

    def test_explicit_scoped_override_resolves_conflict(self):
        override = {"dimension": "dataset", "from": "required", "to": "not_applicable", "justification": "formal theory has no empirical dataset", "scope": {"study_type": "theory"}}
        result = publication_profiles.resolve_profile({"study_type": "theory"}, [layer("fallback", "f", required=["dataset"]), layer("study_type", "theory", overrides=[override])])
        self.assertEqual(result["status"], "PROFILE_RESOLVED")
        self.assertEqual(result["not_applicable"], ["dataset"])
        self.assertIn("dataset", result["na_justifications"])

    def test_direct_not_applicable_requires_recorded_justification(self):
        result = publication_profiles.resolve_profile({}, [layer("fallback", "f", not_applicable=["dataset"], na_justifications={"dataset": "no empirical objects exist in this design"})])
        self.assertEqual(result["status"], "PROFILE_RESOLVED")
        self.assertEqual(result["na_justifications"]["dataset"], "no empirical objects exist in this design")

    def test_missing_or_invalid_na_justification_is_conflict(self):
        result = publication_profiles.resolve_profile({}, [layer("fallback", "f", required=["dataset"]), layer("study_type", "theory", overrides=[{"dimension": "dataset", "from": "required", "to": "not_applicable", "scope": {}}])])
        self.assertEqual(result["status"], "PROFILE_CONFLICT")

    def test_na_justification_must_be_a_nonempty_string(self):
        result = publication_profiles.resolve_profile(
            {},
            [
                layer(
                    "fallback",
                    "fallback",
                    not_applicable=["dataset"],
                    na_justifications={"dataset": 7},
                )
            ],
        )
        self.assertEqual(result["status"], "PROFILE_CONFLICT")
        self.assertTrue(
            any(item["code"] == "INVALID_NA_JUSTIFICATION" for item in result["conflicts"])
        )

    def test_required_to_not_applicable_needs_explicit_research_scope(self):
        for scope, request in (({}, {}), ({"arbitrary": "value"}, {"arbitrary": "value"})):
            with self.subTest(scope=scope):
                override = {
                    "dimension": "dataset",
                    "from": "required",
                    "to": "not_applicable",
                    "justification": "the design has no empirical dataset",
                    "scope": scope,
                }
                result = publication_profiles.resolve_profile(
                    request,
                    [
                        layer("fallback", "fallback", required=["dataset"]),
                        layer("study_type", "theory", overrides=[override]),
                    ],
                )
                self.assertEqual(result["status"], "PROFILE_CONFLICT")

    def test_override_requires_scope_and_owner_identity(self):
        missing_scope = {"dimension": "x", "from": "required", "to": "recommended", "justification": "bounded claim"}
        result = publication_profiles.resolve_profile({}, [layer("fallback", "f", required=["x"]), layer("domain", "d", overrides=[missing_scope])])
        self.assertEqual(result["status"], "PROFILE_CONFLICT")

        wrong_owner_profile = layer(
            "domain",
            "d",
            overrides=[
                {
                    "dimension": "x",
                    "from": "required",
                    "to": "recommended",
                    "justification": "bounded claim",
                    "scope": {},
                }
            ],
        )
        wrong_owner_profile["overrides"][0]["source_id"] = "forged"
        result = publication_profiles.resolve_profile(
            {}, [layer("fallback", "f", required=["x"]), wrong_owner_profile]
        )
        self.assertEqual(result["status"], "PROFILE_CONFLICT")

    def test_same_specificity_conflicting_overrides_fail_closed(self):
        first = layer("domain", "a", overrides=[{"dimension": "x", "from": "required", "to": "recommended", "justification": "one", "scope": {"domain": "ml"}}])
        second = layer("domain", "b", overrides=[{"dimension": "x", "from": "required", "to": "not_applicable", "justification": "two", "scope": {"domain": "ml"}}])
        result = publication_profiles.resolve_profile({"domain": "ml"}, [layer("fallback", "f", required=["x"]), first, second])
        self.assertEqual(result["status"], "PROFILE_CONFLICT")

    def test_less_specific_override_applies_before_more_specific_override(self):
        domain_override = {"dimension": "x", "from": "required", "to": "recommended", "justification": "domain evidence convention", "scope": {}}
        venue_override = {"dimension": "x", "from": "recommended", "to": "required", "justification": "venue requires this dimension", "scope": {}}
        result = publication_profiles.resolve_profile({}, [
            layer("fallback", "fallback", required=["x"]),
            layer("domain", "domain", overrides=[domain_override]),
            layer("venue", "venue", overrides=[venue_override]),
        ])
        self.assertEqual(result["status"], "PROFILE_RESOLVED", result)
        self.assertEqual(result["required"], ["x"])
        self.assertEqual([item["source_id"] for item in result["resolution_events"]], ["domain", "venue"])

    def test_ordinary_assignment_is_applied_before_overrides_at_each_layer(self):
        result = publication_profiles.resolve_profile(
            {},
            [
                layer("fallback", "fallback", required=["x"]),
                layer(
                    "domain",
                    "domain",
                    overrides=[
                        {
                            "dimension": "x",
                            "from": "required",
                            "to": "recommended",
                            "justification": "domain convention",
                            "scope": {},
                        }
                    ],
                ),
                layer("venue", "venue", required=["x"]),
            ],
        )
        self.assertEqual(result["status"], "PROFILE_CONFLICT")
        self.assertTrue(
            any(item["code"] == "CROSS_CATEGORY_ASSIGNMENT" for item in result["conflicts"])
        )

    def test_scope_specificity_orders_overrides_within_a_layer(self):
        generic = layer(
            "domain",
            "generic",
            overrides=[
                {
                    "dimension": "x",
                    "from": "required",
                    "to": "recommended",
                    "justification": "generic domain rule",
                    "scope": {},
                }
            ],
        )
        specific = layer(
            "domain",
            "specific",
            scope={"domain": "ml"},
            overrides=[
                {
                    "dimension": "x",
                    "from": "recommended",
                    "to": "required",
                    "justification": "ML-specific requirement",
                    "scope": {"domain": "ml"},
                }
            ],
        )
        result = publication_profiles.resolve_profile(
            {"domain": "ml"}, [specific, layer("fallback", "fallback", required=["x"]), generic]
        )
        self.assertEqual(result["status"], "PROFILE_RESOLVED", result)
        self.assertEqual(result["required"], ["x"])
        self.assertEqual(
            [item["source_id"] for item in result["resolution_events"]],
            ["generic", "specific"],
        )

    def test_collection_and_override_order_are_canonical(self):
        overrides = [
            {"dimension": "x", "from": "required", "to": "recommended", "justification": "x rule", "scope": {}},
            {"dimension": "y", "from": "required", "to": "recommended", "justification": "y rule", "scope": {}},
        ]
        first_profiles = [
            layer("fallback", "fallback", required=["y", "x", "x"]),
            layer("domain", "domain", overrides=overrides),
        ]
        second_profiles = [
            layer("domain", "domain", overrides=list(reversed(overrides))),
            layer("fallback", "fallback", required=["x", "y"]),
        ]
        first = publication_profiles.resolve_profile({}, first_profiles)
        second = publication_profiles.resolve_profile({}, second_profiles)
        self.assertEqual(first, second)
        self.assertEqual(first["recommended"], ["x", "y"])

    def test_stale_source_hash_fails_closed(self):
        result = publication_profiles.resolve_profile({}, [layer("fallback", "f", source_payload={"required": ["x"]}, source_hash="0" * 64, required=["x"])])
        self.assertEqual(result["status"], "PROFILE_CONFLICT")
        self.assertTrue(any(item["code"] == "STALE_SOURCE_HASH" for item in result["conflicts"]))

    def test_source_payload_is_strictly_bound_to_effective_fields(self):
        value = layer("fallback", "fallback", required=["x"])
        value["required"] = ["forged"]
        result = publication_profiles.resolve_profile({}, [value])
        self.assertEqual(result["status"], "PROFILE_CONFLICT")
        self.assertTrue(
            any(item["code"] == "SOURCE_PAYLOAD_MISMATCH" for item in result["conflicts"])
        )

    def test_source_hash_is_hex_and_is_normalized_case_insensitively(self):
        valid = layer("fallback", "fallback", required=["x"])
        valid["source_hash"] = valid["source_hash"].upper()
        self.assertEqual(
            publication_profiles.resolve_profile({}, [valid])["status"],
            "PROFILE_RESOLVED",
        )
        invalid = layer("fallback", "fallback", required=["x"])
        invalid["source_hash"] = "z" * 64
        result = publication_profiles.resolve_profile({}, [invalid])
        self.assertEqual(result["status"], "PROFILE_CONFLICT")
        self.assertTrue(
            any(item["code"] == "INVALID_SOURCE_HASH" for item in result["conflicts"])
        )

    def test_shipped_fallback_registry_is_hash_bound_and_resolvable(self):
        import json

        registry = json.loads((ROOT / "assets" / "registry" / "publication_profiles.json").read_text(encoding="utf-8"))
        result = publication_profiles.resolve_profile({}, registry["profiles"])
        self.assertEqual(result["status"], "PROFILE_RESOLVED", result)
        self.assertEqual(result["applied_profile_ids"], ["fallback:full-paper"])
        fallback = registry["profiles"][0]
        self.assertEqual(fallback["status"], "PROFILE_ACTIVE")
        self.assertEqual(fallback["provenance"]["source_id"], fallback["profile_id"])
        self.assertEqual(fallback["provenance"]["source_hash"], fallback["source_hash"])
        self.assertEqual(
            fallback["provenance"]["profile_version"], fallback["version"]
        )


if __name__ == "__main__":
    unittest.main()
