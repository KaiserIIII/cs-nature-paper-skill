import hashlib
import importlib.util
import json
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "release_trust", ROOT / "scripts" / "release_trust.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class V41ReleaseTrustTests(unittest.TestCase):
    def test_shipped_release_trust_is_valid_and_fixed_path(self):
        runtime = load_module()
        result = runtime.validate_release_trust()
        self.assertEqual(result["status"], "PASS", result)
        self.assertIsNotNone(
            runtime.load_trusted_json("assets/registry/publication_profiles.json")
        )
        self.assertIsNone(runtime.load_trusted_json("attacker/registry.json"))

    def test_registry_rewrite_is_rejected_even_with_matching_sha256sums(self):
        runtime = load_module()
        registry_path = ROOT / "assets" / "registry" / "publication_profiles.json"
        manifest_path = ROOT / "SHA256SUMS.txt"
        forged_registry = json.loads(registry_path.read_text(encoding="utf-8"))
        forged_registry["profiles"][0]["required"] = []
        forged_registry_bytes = (
            json.dumps(forged_registry, indent=2, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        forged_hash = hashlib.sha256(forged_registry_bytes).hexdigest()
        forged_manifest = "\n".join(
            forged_hash + "  assets/registry/publication_profiles.json"
            if line.endswith("  assets/registry/publication_profiles.json")
            else line
            for line in manifest_path.read_text(encoding="utf-8").splitlines()
        ) + "\n"
        real_read_bytes = Path.read_bytes

        def attacked_read_bytes(path):
            if path.resolve() == registry_path.resolve():
                return forged_registry_bytes
            return real_read_bytes(path)

        real_read_text = Path.read_text

        def attacked_read_text(path, *args, **kwargs):
            if path.resolve() == manifest_path.resolve():
                return forged_manifest
            return real_read_text(path, *args, **kwargs)

        with mock.patch.object(Path, "read_bytes", attacked_read_bytes), mock.patch.object(
            Path, "read_text", attacked_read_text
        ):
            result = runtime.validate_release_trust()
            trusted = runtime.load_trusted_json(
                "assets/registry/publication_profiles.json"
            )

        self.assertEqual(result["status"], "FAIL")
        self.assertIsNone(trusted)


if __name__ == "__main__":
    unittest.main()
