import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


vendor_runtime = load("vendor_skill_runtime")
internal = load("internal_specialists")


class V4VendorRuntimeTests(unittest.TestCase):
    def test_manifest_is_pinned_complete_and_redistributable(self):
        result = vendor_runtime.validate_manifest()
        self.assertEqual(result["status"], "PASS", result)
        self.assertGreaterEqual(result["vendored_skill_count"], 20)
        self.assertGreaterEqual(result["repository_count"], 5)
        self.assertTrue(result["all_exact_shas_pinned"])
        self.assertTrue(result["all_vendored_files_present"])
        self.assertTrue(result["all_licenses_redistributable"])
        manifest = json.loads(vendor_runtime.MANIFEST.read_text(encoding="utf-8"))
        index = subprocess.check_output(
            ["git", "ls-files", "-s", "-z", "--", "vendor/research-skills"],
            cwd=ROOT,
        )
        tracked = {}
        for entry in index.rstrip(b"\0").split(b"\0"):
            metadata, raw_path = entry.split(b"\t", 1)
            _, object_id, stage = metadata.split()
            if stage == b"0":
                tracked[raw_path.decode("utf-8")] = object_id.decode("ascii")
        ordered = list(tracked.items())
        batch = subprocess.check_output(
            ["git", "cat-file", "--batch"],
            cwd=ROOT,
            input="".join(f"{object_id}\n" for _, object_id in ordered).encode("ascii"),
        )
        blobs = {}
        offset = 0
        for repository_path, _ in ordered:
            header_end = batch.index(b"\n", offset)
            size = int(batch[offset:header_end].rsplit(b" ", 1)[1])
            content_start = header_end + 1
            blobs[repository_path] = batch[content_start:content_start + size]
            offset = content_start + size + 1
        for skill in manifest["skills"]:
            for record in skill["vendored_files"]:
                repository_path = Path("vendor", "research-skills", record["path"]).as_posix()
                self.assertIn(repository_path, blobs, f"manifest file is not tracked: {repository_path}")
                self.assertEqual(
                    hashlib.sha256(blobs[repository_path]).hexdigest(),
                    record["sha256"],
                    f"manifest hash differs from Git index: {repository_path}",
                )

    def test_manifest_records_required_audit_fields(self):
        manifest = json.loads(
            (ROOT / "vendor" / "research-skills" / "THIRD_PARTY_MANIFEST.json").read_text(encoding="utf-8")
        )
        required = {
            "name", "repository", "source_path", "exact_commit", "license",
            "redistribution_allowed", "vendored_files", "modified",
            "local_modifications", "security_audit", "behavior_trial",
            "capabilities", "assigned_specialists",
        }
        for skill in manifest["skills"]:
            self.assertFalse(required - set(skill), skill.get("name"))
            self.assertRegex(skill["exact_commit"], r"^[0-9a-f]{40}$")
            self.assertTrue(skill["redistribution_allowed"])
            self.assertEqual(skill["security_audit"]["status"], "PASS")
            self.assertEqual(skill["behavior_trial"]["status"], "PASS")

    def test_license_decision_fails_closed(self):
        for value in ("UNKNOWN", "NOASSERTION", "CC-BY-NC-4.0", "CC-BY-ND-4.0", ""):
            result = vendor_runtime.license_decision(value)
            self.assertEqual(result["status"], "DO_NOT_VENDOR", value)
            self.assertFalse(result["redistribution_allowed"], value)
        self.assertEqual(vendor_runtime.license_decision("MIT")["status"], "PASS")

    def test_loading_statistics_reads_the_real_vendored_skill(self):
        loaded = vendor_runtime.load_for_capability("statistical-analysis")
        self.assertEqual(loaded["status"], "PASS", loaded)
        self.assertEqual(loaded["source_kind"], "VENDORED_THIRD_PARTY_SKILL")
        self.assertIn("statistical-analysis", loaded["capabilities"])
        self.assertIn("Analysis Workflow", loaded["skill_text"])
        self.assertTrue(Path(loaded["skill_path"]).is_file())
        self.assertIn("vendor", Path(loaded["skill_path"]).parts)

    def test_required_nodes_load_real_vendored_resources_offline(self):
        routes = {
            "literature": "literature-evidence",
            "analysis": "statistics",
            "writing": "scientific-writing",
            "review": "adversarial-review-board",
            "formal_experiment": "research-engineering-compute",
        }
        with tempfile.TemporaryDirectory() as temp:
            for node, specialist in routes.items():
                result = internal.invoke_specialist(
                    specialist,
                    task={"node": node, "description": "offline formal workflow"},
                    project=Path(temp),
                    network_available=False,
                )
                self.assertEqual(result["status"], "PASS", result)
                self.assertEqual(result["network_used"], False)
                self.assertEqual(result["provider_type"], "INTERNAL_SPECIALIST")
                self.assertGreaterEqual(len(result["loaded_skills"]), 1)
                self.assertTrue(all(item["source_kind"] == "VENDORED_THIRD_PARTY_SKILL" for item in result["loaded_skills"]))
                self.assertTrue(Path(temp, result["artifacts"][0]).is_file())

    def test_research_executor_uses_builtin_after_offline_upgrade_discovery(self):
        state = load("research_state")
        executor = load("research_executor")
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "paper"
            project.mkdir()
            state.init_state(project, "ml-benchmark", "maximum-autonomy", "machine-learning")
            inputs = project / "inputs"
            inputs.mkdir()
            (inputs / "research_brief.json").write_text(json.dumps({
                "title": "Offline publication workflow",
                "question": "Can a bounded result support a full paper?",
                "workflow": "full-paper",
                "submission_targeted": True,
            }), encoding="utf-8")
            policy = project / ".research-state" / "autonomy_policy.json"
            policy.write_text(json.dumps({
                "permissions": {
                    "local_read": True, "local_write": True, "execute": True,
                    "network": False, "auto_hire": False,
                }
            }), encoding="utf-8")

            result = executor.execute_node(project, "writing")

            self.assertEqual(result["status"], "HOST_EXECUTION_REQUIRED", result)
            self.assertEqual(result["provider_route"]["provider"]["type"], "INTERNAL_SPECIALIST")
            self.assertEqual(result["provider_route"]["provider_decision"]["decision"], "FALLBACK_BUILT_IN")
            self.assertEqual(result["specialist_discovery"]["status"], "UNAVAILABLE")
            self.assertEqual(result["internal_specialist_invocation"]["status"], "PASS")
            self.assertTrue((project / result["internal_specialist_invocation"]["artifacts"][0]).is_file())
            self.assertTrue(result["loaded_skills"])


if __name__ == "__main__":
    unittest.main()
