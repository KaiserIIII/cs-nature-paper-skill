import ast
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "4.0.0"


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class V4ReleaseTests(unittest.TestCase):
    def test_skill_and_readmes_declare_v4(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn('version: "4.0.0"', skill)
        self.assertIn("CS Nature Paper V4.0.0", skill)
        self.assertIn(
            "V4 ships with audited, pinned, vendored third-party research Skills as a built-in publication-grade specialist team.",
            skill,
        )
        self.assertTrue((ROOT / "README.md").read_text(encoding="utf-8").startswith("# CS Nature Paper V4.0.0"))
        self.assertTrue((ROOT / "README_zh.md").read_text(encoding="utf-8").startswith("# CS Nature Paper V4.0.0"))

    def test_all_active_python_runtime_versions_are_v4(self):
        stale = []
        for path in (ROOT / "scripts").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "SKILL_VERSION" for target in node.targets):
                    if not isinstance(node.value, ast.Constant) or node.value.value != VERSION:
                        stale.append(path.name)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Dict):
                    continue
                for key, value in zip(node.keys, node.values):
                    if (
                        isinstance(key, ast.Constant)
                        and key.value == "skill_version"
                        and isinstance(value, ast.Constant)
                        and isinstance(value.value, str)
                        and value.value != VERSION
                    ):
                        stale.append(f"{path.name}:{value.lineno}")
        self.assertFalse(stale, stale)

    def test_active_provider_metadata_and_user_agents_are_v4(self):
        stale = []
        for path in sorted((ROOT / "providers").glob("*.py")):
            if path.name.endswith("_fixture_provider.py"):
                continue
            text = path.read_text(encoding="utf-8")
            if "3.2.1" in text:
                stale.append(str(path.relative_to(ROOT)))
        discovery = (ROOT / "scripts" / "skill_discovery_provider.py").read_text(encoding="utf-8")
        if "cs-nature-paper-provider/3.2.1" in discovery:
            stale.append("scripts/skill_discovery_provider.py")
        self.assertFalse(stale, stale)

    def test_active_schema_version_constants_are_v4(self):
        stale = []
        for path in sorted((ROOT / "assets" / "schemas").glob("*.schema.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            const = value.get("properties", {}).get("skill_version", {}).get("const")
            if const is not None and const != VERSION:
                stale.append(str(path.relative_to(ROOT)))
        self.assertFalse(stale, stale)

    def test_public_privacy_lint_scans_docs_prepared_and_forward_slash_paths(self):
        privacy = load("privacy_lint")
        self.assertNotIn("prepared", privacy.SKIP_DIRS)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prepared = root / "prepared"
            prepared.mkdir()
            (prepared / "leak.json").write_text('{"path":"E:/private/project/result.json"}', encoding="utf-8")
            result = privacy.lint([root], root)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(item["kind"] == "windows-forward-absolute-path" for item in result["findings"]), result)

        public = privacy.lint(
            [ROOT / "benchmarks", ROOT / "docs", ROOT / "release_manifest.json"],
            ROOT,
        )
        self.assertEqual(public["status"], "PASS", public["findings"])

    def test_all_nonlegacy_json_assets_declare_v4(self):
        stale = []
        for path in (ROOT / "assets").rglob("*.json"):
            if "legacy" in path.parts:
                continue
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, dict) and "skill_version" in value and value["skill_version"] != VERSION:
                stale.append(str(path.relative_to(ROOT)))
        self.assertFalse(stale, stale)

    def test_release_manifest_describes_unreleased_v4_rc(self):
        value = json.loads((ROOT / "release_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(value["source_version"], VERSION)
        self.assertEqual(value["base_commit"], "6f13161601854763b500cdb596dbe52df3a0fd19")
        self.assertEqual(value["source_branch"], "feat/v4-vendored-research-team")
        self.assertEqual(value["release_status"], "RC_NOT_RELEASED")
        self.assertIsNone(value["tag"])
        self.assertEqual(value["benchmark_suite"]["status"], "NOT_RUN")
        self.assertEqual(value["benchmark_suite"]["recommended_merge"], "NO")
        self.assertEqual(value["tta_field_regression"]["thin_draft_detection"], "PASS")
        self.assertEqual(value["tta_field_regression"]["publication_sufficiency"], "FAIL")
        self.assertEqual(value["recommended_merge"], "NO")

    def test_v4_runtime_never_downloads_or_clones_vendored_skills(self):
        text = "\n".join(
            (ROOT / "scripts" / name).read_text(encoding="utf-8")
            for name in ("internal_specialists.py", "vendor_skill_runtime.py")
        ).lower()
        self.assertNotIn("git clone", text)
        self.assertNotIn("invoke-webrequest", text)
        self.assertNotIn("requests.get", text)
        self.assertNotIn("urllib.request", text)

    def test_v4_manifest_and_json_assets_pass_integrity_validation(self):
        validator = load("validate_release")
        self.assertEqual(validator.validate_json_assets(), [])
        self.assertEqual(validator.validate_benchmark_suite_assets(), [])
        self.assertEqual(validator.validate_private_ultra_assets(), [])
        self.assertEqual(validator.validate_long_run_assets(), [])
        self.assertEqual(validator.validate_release_manifest(require_hosted_ci=False), [])

    def test_hosted_ci_resolution_preserves_v4_and_incomplete_research_gates(self):
        resolver = load("resolve_release_manifest")
        validator = load("validate_release")
        commit = __import__("subprocess").run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "resolved.json"
            value = resolver.resolve(
                ROOT / "release_manifest.json",
                output,
                commit,
                run_id=42,
                workflow="cs-nature-paper-v4",
                branch="feat/v4-vendored-research-team",
                conclusion="success",
                matrix_status="PASS",
            )
            self.assertEqual(value["source_version"], VERSION)
            self.assertEqual(value["recommended_merge"], "NO")
            self.assertIn("V4.0.0 RC FAIL", value["release_disposition"])
            self.assertEqual(
                validator.validate_release_manifest(
                    output,
                    expected_commit=commit,
                    expected_branch="feat/v4-vendored-research-team",
                    require_hosted_ci=True,
                ),
                [],
            )

    def test_benchmark_manifest_fails_closed_and_matches_run_state(self):
        validator = load("validate_release")
        value = json.loads((ROOT / "release_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(validator.validate_benchmark_manifest_consistency(value), [])
        value["benchmark_suite"]["ars_parity_gate"] = "PASS"
        findings = validator.validate_benchmark_manifest_consistency(value)
        self.assertTrue(any("NOT_RUN must fail closed" in item for item in findings), findings)


if __name__ == "__main__":
    unittest.main()
