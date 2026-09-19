import importlib.util
import hashlib
import os
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_runtime():
    spec = importlib.util.spec_from_file_location(
        "long_run_handoff", ROOT / "scripts" / "long_run_handoff.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LongRunHandoffTests(unittest.TestCase):
    def durable_record(self, root: Path):
        paths = {}
        for name in ("status", "heartbeat", "stdout", "stderr"):
            path = root / f"{name}.log"
            path.write_text("ready\n", encoding="utf-8")
            paths[name] = str(path)
        frozen_files = {}
        frozen_hashes = {}
        for index, name in enumerate(("runner", "manifest", "protocol"), start=1):
            path = root / f"{name}.txt"
            path.write_text(f"frozen-{index}\n", encoding="utf-8")
            field = f"{name}_sha256"
            frozen_files[field] = str(path)
            frozen_hashes[field] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        return {
            "launch_mode": "WINDOWS_TASK_SCHEDULER",
            "launch_id": "formal-campaign-v2",
            "working_directory": str(root),
            "status_path": paths["status"],
            "heartbeat_path": paths["heartbeat"],
            "stdout_log": paths["stdout"],
            "stderr_log": paths["stderr"],
            "resume_command": "python supervisor.py --resume",
            "frozen_hashes": frozen_hashes,
            "frozen_files": frozen_files,
            "expected_outputs": [
                {"path": str(root / "final-result.json"), "minimum_bytes": 2},
            ],
        }

    def test_two_hour_threshold_routes_long_work_to_background_and_yield(self):
        runtime = load_runtime()
        with tempfile.TemporaryDirectory() as temporary:
            record = self.durable_record(Path(temporary))
            short = runtime.assess(7200, record)
            long = runtime.assess(7201, record)
        self.assertEqual(short["decision"], "CONTINUE_IN_SESSION")
        self.assertEqual(long["decision"], "BACKGROUND_AND_YIELD")
        self.assertEqual(long["conversation_action"], "END_CURRENT_TURN")

    def test_long_work_cannot_yield_without_a_durable_resume_contract(self):
        runtime = load_runtime()
        result = runtime.assess(7201, {"launch_mode": "FOREGROUND"})
        self.assertEqual(result["decision"], "BLOCKED_NEEDS_DURABLE_LAUNCH")
        self.assertTrue(result["findings"])

    def test_long_work_requires_frozen_file_bindings_and_declared_outputs(self):
        runtime = load_runtime()
        with tempfile.TemporaryDirectory() as temporary:
            record = self.durable_record(Path(temporary))
            record.pop("frozen_files")
            no_files = runtime.assess(7201, record)
            record = self.durable_record(Path(temporary))
            record.pop("expected_outputs")
            no_outputs = runtime.assess(7201, record)
            record = self.durable_record(Path(temporary))
            record.pop("working_directory")
            no_working_directory = runtime.assess(7201, record)
        self.assertEqual(no_files["decision"], "BLOCKED_NEEDS_DURABLE_LAUNCH")
        self.assertEqual(no_outputs["decision"], "BLOCKED_NEEDS_DURABLE_LAUNCH")
        self.assertEqual(
            no_working_directory["decision"],
            "BLOCKED_NEEDS_DURABLE_LAUNCH",
        )

    def test_resume_waits_while_running_and_continues_only_after_verification(self):
        runtime = load_runtime()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = self.durable_record(root)
            running = runtime.resume_decision(record, {"status": "RUNNING"})
            completed_without_output = runtime.resume_decision(
                record,
                {"status": "COMPLETED", "outputs_verified": True},
            )
            (root / "final-result.json").write_text("{}", encoding="utf-8")
            completed = runtime.resume_decision(record, {"status": "COMPLETED"})

        self.assertEqual(running["decision"], "WAIT_AND_YIELD")
        self.assertEqual(completed_without_output["decision"], "VERIFY_BEFORE_CONTINUING")
        self.assertEqual(completed["decision"], "RESUME_RESEARCH")
        self.assertTrue(completed["frozen_identities_verified"])
        self.assertTrue(completed["outputs_verified"])

    def test_resume_detects_stale_heartbeat_and_frozen_identity_drift(self):
        runtime = load_runtime()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = self.durable_record(root)
            old = time.time() - 601
            os.utime(record["heartbeat_path"], (old, old))
            stale = runtime.resume_decision(
                record,
                {"status": "RUNNING", "heartbeat_fresh": True},
                heartbeat_max_age_seconds=300,
            )

            Path(record["frozen_files"]["runner_sha256"]).write_text(
                "mutated\n", encoding="utf-8"
            )
            drift = runtime.resume_decision(record, {"status": "COMPLETED"})

        self.assertEqual(stale["decision"], "INVESTIGATE_STALE_HEARTBEAT")
        self.assertEqual(drift["decision"], "IDENTITY_DRIFT_STOP")
        self.assertTrue(drift["findings"])

    def test_skill_declares_the_executable_long_run_rule(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("BACKGROUND_AND_YIELD", skill)
        self.assertIn("two hours", skill.lower())
        self.assertIn("references/core/long-running-work.md", skill)


if __name__ == "__main__":
    unittest.main()
