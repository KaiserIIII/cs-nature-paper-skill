import copy
import importlib.util
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_release_v41", ROOT / "scripts" / "validate_release.py"
)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(validator)

MANIFEST_SPEC = importlib.util.spec_from_file_location(
    "build_manifest_v41", ROOT / "scripts" / "build_manifest.py"
)
build_manifest = importlib.util.module_from_spec(MANIFEST_SPEC)
assert MANIFEST_SPEC and MANIFEST_SPEC.loader
MANIFEST_SPEC.loader.exec_module(build_manifest)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class V41ReleaseSchemaValidationTests(unittest.TestCase):
    def run_release_with_root(self, root):
        components = (
            "validate_behavior_cases",
            "validate_benchmark_suite_assets",
            "validate_long_run_assets",
            "validate_private_ultra_assets",
            "validate_release_trust_assets",
            "validate_release_manifest",
            "validate_runtime_results",
            "validate_docs",
        )
        registry = types.SimpleNamespace(
            validate=lambda: {"status": "PASS", "findings": []}
        )
        privacy = types.SimpleNamespace(
            lint=lambda paths: {"status": "PASS", "findings": []}
        )
        patches = [mock.patch.object(validator, name, return_value=[]) for name in components]
        with mock.patch.object(validator, "ROOT", root), mock.patch.dict(
            "sys.modules", {"validate_registry": registry, "privacy_lint": privacy}
        ):
            for patcher in patches:
                patcher.start()
            try:
                return validator.validate()
            finally:
                for patcher in reversed(patches):
                    patcher.stop()

    def stage_v41_contracts(self, root):
        for stem in ("publication_profile", "falsification_obligation"):
            write_json(
                root / "assets" / "schemas" / f"{stem}.schema.json",
                load_json(ROOT / "assets" / "schemas" / f"{stem}.schema.json"),
            )
            write_json(
                root / "assets" / "templates" / f"{stem}.json",
                load_json(ROOT / "assets" / "templates" / f"{stem}.json"),
            )
        self.refresh_source_manifest(root)

    def refresh_source_manifest(self, root):
        (root / "SHA256SUMS.txt").write_text(
            build_manifest.render(root), encoding="utf-8", newline="\n"
        )

    def test_new_schema_stems_resolve_to_shipped_templates(self):
        expected = {
            "publication_profile": ROOT
            / "assets"
            / "templates"
            / "publication_profile.json",
            "falsification_obligation": ROOT
            / "assets"
            / "templates"
            / "falsification_obligation.json",
        }
        for stem, path in expected.items():
            with self.subTest(stem=stem):
                self.assertEqual(validator.schema_instance_path(stem, ROOT), path)
                self.assertTrue(path.is_file())

    def test_release_file_inventory_contains_both_contract_templates(self):
        paths = {path for _, path in build_manifest.entries(ROOT)}
        self.assertIn("assets/templates/publication_profile.json", paths)
        self.assertIn("assets/templates/falsification_obligation.json", paths)

    def test_explicit_schema_candidate_cannot_be_silently_skipped(self):
        schema = load_json(
            ROOT / "assets" / "schemas" / "publication_profile.schema.json"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_json(
                root / "assets" / "schemas" / "publication_profile.schema.json",
                schema,
            )
            original_root = validator.ROOT
            validator.ROOT = root
            try:
                findings = validator.validate_json_assets()
            finally:
                validator.ROOT = original_root
        self.assertTrue(
            any("publication_profile" in item and "missing" in item for item in findings),
            findings,
        )

    def test_release_validation_reads_both_shipped_templates(self):
        cases = {
            "publication_profile": (
                "status",
                ROOT / "assets" / "templates" / "publication_profile.json",
            ),
            "falsification_obligation": (
                "publication_pass",
                ROOT / "assets" / "templates" / "falsification_obligation.json",
            ),
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for stem, (field, template_path) in cases.items():
                schema = load_json(
                    ROOT / "assets" / "schemas" / f"{stem}.schema.json"
                )
                template = load_json(template_path)
                template.pop(field)
                write_json(
                    root / "assets" / "schemas" / f"{stem}.schema.json", schema
                )
                write_json(
                    root / "assets" / "templates" / f"{stem}.json", template
                )
            original_root = validator.ROOT
            validator.ROOT = root
            try:
                findings = validator.validate_json_assets()
            finally:
                validator.ROOT = original_root
        for stem, (field, _) in cases.items():
            with self.subTest(stem=stem):
                self.assertTrue(
                    any(stem in item and field in item for item in findings), findings
                )

    def test_release_entry_fails_when_contract_template_is_missing_or_tampered(self):
        for stem in ("publication_profile", "falsification_obligation"):
            for mutation in ("missing", "tampered"):
                with self.subTest(stem=stem, mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    self.stage_v41_contracts(root)
                    candidate = root / "assets" / "templates" / f"{stem}.json"
                    if mutation == "missing":
                        candidate.unlink()
                    else:
                        value = load_json(candidate)
                        value["status"] = "ATTACKER_STATUS"
                        write_json(candidate, value)
                    result = self.run_release_with_root(root)
                    self.assertEqual(result["status"], "FAIL", result)
                    self.assertTrue(result["findings"], result)

    def test_release_entry_rejects_schema_valid_contract_content_tampering(self):
        cases = {
            "publication_profile": ("version", "9.9.9"),
            "falsification_obligation": ("producer_id", "attacker:producer"),
        }
        for stem, (field, value) in cases.items():
            with self.subTest(stem=stem), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self.stage_v41_contracts(root)
                candidate = root / "assets" / "templates" / f"{stem}.json"
                document = load_json(candidate)
                document[field] = value
                write_json(candidate, document)
                schema = load_json(
                    root / "assets" / "schemas" / f"{stem}.schema.json"
                )
                self.assertEqual(validator.validate_instance(document, schema), [])
                result = self.run_release_with_root(root)
                self.assertEqual(result["status"], "FAIL", result)
                self.assertTrue(
                    any("SOURCE_MANIFEST_MISMATCH" in item for item in result["findings"]),
                    result,
                )

    def test_release_entry_enforces_real_v41_oneof_and_const(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.stage_v41_contracts(root)
            self.assertEqual(self.run_release_with_root(root)["status"], "PASS")

        mutations = (
            ("publication_pass", 0),
            ("status", "NOT_REQUIRED"),
        )
        for field, value in mutations:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self.stage_v41_contracts(root)
                candidate = root / "assets" / "templates" / "falsification_obligation.json"
                document = load_json(candidate)
                document[field] = value
                write_json(candidate, document)
                self.refresh_source_manifest(root)
                result = self.run_release_with_root(root)
                self.assertEqual(result["status"], "FAIL", result)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.stage_v41_contracts(root)
            schema_path = root / "assets" / "schemas" / "falsification_obligation.schema.json"
            schema = load_json(schema_path)
            schema["oneOf"].append(copy.deepcopy(schema["oneOf"][0]))
            write_json(schema_path, schema)
            self.refresh_source_manifest(root)
            result = self.run_release_with_root(root)
            self.assertEqual(result["status"], "FAIL", result)
            self.assertTrue(any("matched 2" in item for item in result["findings"]), result)

    def test_validator_enforces_const_and_exactly_one_oneof_branch(self):
        schema = load_json(
            ROOT / "assets" / "schemas" / "falsification_obligation.schema.json"
        )
        template = load_json(
            ROOT / "assets" / "templates" / "falsification_obligation.json"
        )
        self.assertEqual(validator.validate_instance(template, schema), [])

        for invalid_value in (True, 0, "false", None):
            authority_escalation = copy.deepcopy(template)
            authority_escalation["publication_pass"] = invalid_value
            with self.subTest(invalid_value=invalid_value):
                self.assertTrue(
                    any(
                        "publication_pass" in item and "const" in item
                        for item in validator.validate_instance(authority_escalation, schema)
                    )
                )

        contradictory_branch = copy.deepcopy(template)
        contradictory_branch["status"] = "NOT_REQUIRED"
        self.assertTrue(
            any(
                "oneOf" in item
                for item in validator.validate_instance(contradictory_branch, schema)
            )
        )

        incomplete_defined = copy.deepcopy(template)
        incomplete_defined.pop("producer_id")
        self.assertTrue(
            any(
                "oneOf" in item
                for item in validator.validate_instance(incomplete_defined, schema)
            )
        )


if __name__ == "__main__":
    unittest.main()
