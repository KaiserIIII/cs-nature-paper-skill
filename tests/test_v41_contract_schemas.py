import hashlib
import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "assets" / "schemas"
TEMPLATES = ROOT / "assets" / "templates"
HASH_PATTERN = "^sha256:[0-9a-f]{64}$"
SOURCE_HASH_PATTERN = "^[0-9a-f]{64}$"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_runtime(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def schema_errors(instance, schema, path="$"):
    errors = []
    expected_type = schema.get("type")
    type_checks = {
        "object": lambda value: isinstance(value, dict),
        "array": lambda value: isinstance(value, list),
        "string": lambda value: isinstance(value, str),
        "boolean": lambda value: isinstance(value, bool),
        "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
        "number": lambda value: isinstance(value, (int, float))
        and not isinstance(value, bool),
        "null": lambda value: value is None,
    }
    if expected_type and not type_checks[expected_type](instance):
        return [f"{path}: expected {expected_type}"]
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: not in enum")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{path}: shorter than minLength")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: pattern mismatch")
    if isinstance(instance, list):
        if schema.get("uniqueItems"):
            canonical = [json.dumps(item, sort_keys=True) for item in instance]
            if len(canonical) != len(set(canonical)):
                errors.append(f"{path}: duplicate items")
        if "items" in schema:
            for index, item in enumerate(instance):
                errors.extend(schema_errors(item, schema["items"], f"{path}[{index}]"))
    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                errors.append(f"{path}: missing {key}")
        properties = schema.get("properties", {})
        for key, subschema in properties.items():
            if key in instance:
                errors.extend(schema_errors(instance[key], subschema, f"{path}.{key}"))
        if schema.get("additionalProperties") is False:
            for key in set(instance) - set(properties):
                errors.append(f"{path}: unexpected {key}")
        elif isinstance(schema.get("additionalProperties"), dict):
            for key in set(instance) - set(properties):
                errors.extend(
                    schema_errors(
                        instance[key],
                        schema["additionalProperties"],
                        f"{path}.{key}",
                    )
                )
    if "oneOf" in schema:
        matches = sum(not schema_errors(instance, branch, path) for branch in schema["oneOf"])
        if matches != 1:
            errors.append(f"{path}: expected exactly one oneOf match, got {matches}")
    return errors


def assert_schema_valid(test_case, instance, schema):
    test_case.assertEqual(schema_errors(instance, schema), [])


class V41ContractSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_json(ROOT / "assets" / "registry" / "publication_profiles.json")
        cls.profile_schema = load_json(SCHEMAS / "publication_profile.schema.json")
        cls.profile_template = load_json(TEMPLATES / "publication_profile.json")
        cls.obligation_schema = load_json(
            SCHEMAS / "falsification_obligation.schema.json"
        )
        cls.obligation_template = load_json(
            TEMPLATES / "falsification_obligation.json"
        )

    def test_publication_profile_requires_hash_bound_source_payload(self):
        schema = self.profile_schema
        self.assertIn("source_payload", schema["required"])
        self.assertEqual(
            schema["properties"]["source_hash"]["pattern"], SOURCE_HASH_PATTERN
        )

        payload = schema["properties"]["source_payload"]
        self.assertEqual(payload["type"], "object")
        self.assertEqual(
            set(payload["required"]),
            {"required", "recommended", "not_applicable", "overrides"},
        )
        self.assertFalse(payload["additionalProperties"])
        for field in ("required", "recommended", "not_applicable"):
            dimension_list = payload["properties"][field]
            self.assertEqual(dimension_list["type"], "array")
            self.assertEqual(dimension_list["items"]["type"], "string")
            self.assertEqual(dimension_list["items"]["minLength"], 1)
            self.assertTrue(dimension_list["uniqueItems"])
        self.assertIn("na_justifications", payload["properties"])

        payload_override = payload["properties"]["overrides"]["items"]
        self.assertEqual(
            set(payload_override["required"]),
            {"dimension", "from", "to", "justification", "scope"},
        )
        self.assertNotIn("source_id", payload_override["properties"])

    def test_publication_profile_status_and_provenance_are_typed(self):
        schema = self.profile_schema
        self.assertIn("status", schema["required"])
        self.assertIn("provenance", schema["required"])
        self.assertEqual(
            schema["properties"]["status"]["enum"],
            ["PROFILE_ACTIVE", "PROFILE_DEPRECATED"],
        )

        provenance = schema["properties"]["provenance"]
        self.assertEqual(provenance["type"], "object")
        self.assertEqual(
            set(provenance["required"]),
            {"source_id", "source_hash", "profile_version"},
        )
        self.assertEqual(
            provenance["properties"]["source_hash"]["pattern"],
            SOURCE_HASH_PATTERN,
        )
        self.assertFalse(provenance["additionalProperties"])

    def test_publication_profile_override_provenance_is_not_opaque(self):
        override = self.profile_schema["properties"]["overrides"]["items"]
        self.assertEqual(override["type"], "object")
        self.assertEqual(
            set(override["required"]),
            {
                "dimension",
                "from",
                "to",
                "justification",
                "scope",
                "source_id",
                "source_hash",
                "profile_version",
            },
        )
        self.assertEqual(
            override["properties"]["from"]["enum"],
            ["required", "recommended", "not_applicable"],
        )
        self.assertEqual(
            override["properties"]["to"]["enum"],
            ["required", "recommended", "not_applicable"],
        )
        self.assertEqual(
            override["properties"]["source_hash"]["pattern"],
            SOURCE_HASH_PATTERN,
        )
        for field in ("dimension", "justification", "source_id", "profile_version"):
            self.assertEqual(override["properties"][field]["type"], "string")
            self.assertEqual(override["properties"][field]["minLength"], 1)
        self.assertEqual(override["properties"]["scope"]["type"], "object")

    def test_publication_profile_template_mirrors_source_and_provenance(self):
        template = self.profile_template
        self.assertEqual(template["status"], "PROFILE_ACTIVE")
        self.assertEqual(template["provenance"]["source_id"], template["profile_id"])
        self.assertEqual(
            template["provenance"]["profile_version"], template["version"]
        )
        self.assertEqual(
            template["provenance"]["source_hash"], template["source_hash"]
        )
        for field in ("required", "recommended", "not_applicable", "overrides"):
            self.assertEqual(template["source_payload"][field], template[field])

        encoded = json.dumps(
            template["source_payload"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.assertEqual(template["source_hash"], hashlib.sha256(encoded).hexdigest())

    def test_shipped_registry_profiles_validate_and_follow_runtime_hash_model(self):
        for profile in self.registry["profiles"]:
            with self.subTest(profile=profile.get("profile_id")):
                assert_schema_valid(self, profile, self.profile_schema)
                self.assertEqual(profile["status"], "PROFILE_ACTIVE")
                self.assertEqual(profile["provenance"]["source_id"], profile["profile_id"])
                self.assertEqual(
                    profile["provenance"]["profile_version"], profile["version"]
                )
                self.assertEqual(
                    profile["provenance"]["source_hash"], profile["source_hash"]
                )
                encoded = json.dumps(
                    profile["source_payload"],
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                self.assertEqual(
                    profile["source_hash"], hashlib.sha256(encoded).hexdigest()
                )

    def test_source_payload_accepts_runtime_na_and_strips_override_provenance(self):
        source_override = {
            "dimension": "dataset",
            "from": "required",
            "to": "not_applicable",
            "justification": "formal theory has no empirical dataset",
            "scope": {"study_type": "theory"},
        }
        payload = {
            "required": ["dataset"],
            "recommended": [],
            "not_applicable": [],
            "overrides": [source_override],
            "na_justifications": {"dataset": "formal theory has no empirical dataset"},
        }
        assert_schema_valid(
            self, payload, self.profile_schema["properties"]["source_payload"]
        )
        self.assertNotIn(
            "source_hash",
            self.profile_schema["properties"]["source_payload"]["properties"][
                "overrides"
            ]["items"]["properties"],
        )

        source_hash = hashlib.sha256(
            json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        ).hexdigest()
        profile = {
            "profile_id": "fallback:theory",
            "layer": "fallback",
            "version": "1.0.0",
            "status": "PROFILE_ACTIVE",
            "source_hash": source_hash,
            "source_payload": payload,
            "provenance": {
                "source_id": "fallback:theory",
                "source_hash": source_hash,
                "profile_version": "1.0.0",
            },
            "required": ["dataset"],
            "recommended": [],
            "not_applicable": [],
            "overrides": [
                {
                    **source_override,
                    "source_id": "fallback:theory",
                    "source_hash": source_hash,
                    "profile_version": "1.0.0",
                }
            ],
            "na_justifications": payload["na_justifications"],
        }
        assert_schema_valid(self, profile, self.profile_schema)
        resolved = load_runtime("publication_profiles").resolve_profile(
            {"study_type": "theory"}, [profile]
        )
        self.assertEqual(resolved["status"], "PROFILE_RESOLVED", resolved)
        self.assertEqual(resolved["not_applicable"], ["dataset"])

    def test_falsification_schema_requires_authority_boundaries_and_hashes(self):
        schema = self.obligation_schema
        authority_fields = {
            "claim_status_change_authorized",
            "evidence_upgrade_authorized",
            "graph_transition_authorized",
            "publication_pass",
        }
        self.assertTrue(authority_fields.issubset(schema["required"]))
        for field in authority_fields:
            self.assertIs(schema["properties"][field]["const"], False)

        self.assertIn("status", schema["required"])
        self.assertEqual(
            schema["properties"]["status"]["enum"],
            ["OBLIGATION_REQUIRED", "NOT_REQUIRED", "OBLIGATION_REJECTED"],
        )
        defined = next(
            branch
            for branch in schema["oneOf"]
            if branch["properties"]["status"].get("const") == "OBLIGATION_REQUIRED"
        )
        for field in ("claim_hash", "obligation_hash"):
            self.assertIn(field, defined["required"])
            self.assertEqual(schema["properties"][field]["pattern"], HASH_PATTERN)
        self.assertEqual(
            schema["properties"]["profile_hash"]["pattern"],
            "^(sha256:)?[0-9a-f]{64}$",
        )

    def test_falsification_checks_have_required_typed_fields(self):
        schema = self.obligation_schema
        for field in (
            "confirmation_test",
            "falsification_attempt",
            "boundary_condition_test",
            "strongest_surviving_alternative",
            "residual_confidence",
        ):
            with self.subTest(field=field):
                check = schema["properties"][field]
                self.assertEqual(check["type"], "object")
                self.assertEqual(set(check["required"]), {"check_id", "description"})
                for nested in ("check_id", "description"):
                    self.assertEqual(check["properties"][nested]["type"], "string")
                    self.assertEqual(check["properties"][nested]["minLength"], 1)

    def test_falsification_template_satisfies_static_contract(self):
        template = self.obligation_template
        self.assertEqual(template["status"], "OBLIGATION_REQUIRED")
        self.assertTrue(template["required"])
        for field in ("claim_hash", "profile_hash", "obligation_hash"):
            self.assertRegex(template[field], r"^(?:sha256:)?[0-9a-f]{64}$")
        for field in (
            "confirmation_test",
            "falsification_attempt",
            "boundary_condition_test",
            "strongest_surviving_alternative",
            "residual_confidence",
        ):
            self.assertTrue(template[field]["check_id"])
            self.assertTrue(template[field]["description"])
        for field in (
            "claim_status_change_authorized",
            "evidence_upgrade_authorized",
            "graph_transition_authorized",
            "publication_pass",
        ):
            self.assertIs(template[field], False)
        assert_schema_valid(self, template, self.obligation_schema)

    def test_runtime_falsification_instances_match_each_schema_branch(self):
        profiles = load_runtime("publication_profiles")
        falsification = load_runtime("falsification_obligation")
        resolved = profiles.resolve_profile({}, self.registry["profiles"])
        self.assertEqual(resolved["status"], "PROFILE_RESOLVED", resolved)
        base_claim = {
            "claim_id": "C-schema",
            "text": "Schema cross-validation claim.",
            "strength": "HIGH",
            "load_bearing": True,
        }
        instances = [
            falsification.derive_obligation(
                base_claim, resolved, producer_id="provider:falsification"
            ),
            falsification.derive_obligation(
                {**base_claim, "strength": "BOUNDED", "load_bearing": False},
                resolved,
                producer_id="provider:falsification",
            ),
            falsification.derive_obligation(
                base_claim,
                {**resolved, "status": "PROFILE_CONFLICT"},
                producer_id="provider:falsification",
            ),
        ]
        self.assertEqual(
            [instance["status"] for instance in instances],
            ["OBLIGATION_REQUIRED", "NOT_REQUIRED", "OBLIGATION_REJECTED"],
        )
        for instance in instances:
            with self.subTest(status=instance["status"]):
                assert_schema_valid(self, instance, self.obligation_schema)

    def test_falsification_defined_branch_rejects_missing_fields_or_authority(self):
        template = self.obligation_template
        mutations = []
        for field in (
            "producer_id",
            "claim_hash",
            "confirmation_test",
        ):
            value = dict(template)
            value.pop(field)
            mutations.append(value)
        escalated = dict(template)
        escalated["publication_pass"] = True
        mutations.append(escalated)
        contradictory = dict(template)
        contradictory["status"] = "NOT_REQUIRED"
        mutations.append(contradictory)

        for value in mutations:
            with self.subTest(keys=sorted(value), status=value.get("status")):
                self.assertTrue(schema_errors(value, self.obligation_schema))


if __name__ == "__main__":
    unittest.main()
