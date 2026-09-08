#!/usr/bin/env python3
"""Fail-closed policy for work that must outlive the current conversation."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any


SKILL_VERSION = "4.0.0"
TWO_HOURS_SECONDS = 2 * 60 * 60
DURABLE_LAUNCH_MODES = {"WINDOWS_TASK_SCHEDULER", "SYSTEMD", "SLURM", "PUEUE", "DAGU", "DETACHED_SERVICE"}
REQUIRED_PATHS = ("status_path", "heartbeat_path", "stdout_log", "stderr_log")
REQUIRED_FROZEN_HASHES = ("runner_sha256", "manifest_sha256", "protocol_sha256")


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        return False
    return all(character in "0123456789abcdef" for character in value[7:])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def validate_durable_record(record: dict[str, Any], *, require_paths_exist: bool = True) -> list[str]:
    findings: list[str] = []
    if record.get("launch_mode") not in DURABLE_LAUNCH_MODES:
        findings.append("launch_mode is not an approved durable background mechanism")
    if not record.get("launch_id"):
        findings.append("launch_id is required")
    working_directory = record.get("working_directory")
    if not working_directory:
        findings.append("working_directory is required")
    else:
        working_path = Path(working_directory)
        if not working_path.is_absolute():
            findings.append("working_directory must be absolute")
        elif require_paths_exist and not working_path.is_dir():
            findings.append(f"working_directory does not exist: {working_directory}")
    if not record.get("resume_command"):
        findings.append("resume_command is required")
    for field in REQUIRED_PATHS:
        value = record.get(field)
        if not value:
            findings.append(f"{field} is required")
        else:
            path = Path(value)
            if not path.is_absolute():
                findings.append(f"{field} must be absolute")
            elif require_paths_exist and not path.exists():
                findings.append(f"{field} does not exist: {value}")
    frozen = record.get("frozen_hashes")
    frozen_files = record.get("frozen_files")
    if not isinstance(frozen, dict):
        findings.append("frozen_hashes is required")
    else:
        for field in REQUIRED_FROZEN_HASHES:
            if not _is_sha256(frozen.get(field)):
                findings.append(f"frozen_hashes.{field} must be an exact SHA-256 identity")
    if not isinstance(frozen_files, dict):
        findings.append("frozen_files is required")
    else:
        for field in REQUIRED_FROZEN_HASHES:
            value = frozen_files.get(field)
            if not value:
                findings.append(f"frozen_files.{field} is required")
                continue
            path = Path(value)
            if not path.is_absolute():
                findings.append(f"frozen_files.{field} must be absolute")
                continue
            if require_paths_exist and not path.is_file():
                findings.append(f"frozen_files.{field} does not exist: {value}")
                continue
            if require_paths_exist and isinstance(frozen, dict) and _is_sha256(frozen.get(field)):
                actual = _sha256(path)
                if actual != frozen[field]:
                    findings.append(
                        f"frozen identity drift for {field}: expected {frozen[field]}, observed {actual}"
                    )
    outputs = record.get("expected_outputs")
    if not isinstance(outputs, list) or not outputs:
        findings.append("expected_outputs must declare at least one output file")
    else:
        for index, output in enumerate(outputs):
            if not isinstance(output, dict) or not output.get("path"):
                findings.append(f"expected_outputs[{index}].path is required")
                continue
            if not Path(output["path"]).is_absolute():
                findings.append(f"expected_outputs[{index}].path must be absolute")
            minimum_bytes = output.get("minimum_bytes", 1)
            if not isinstance(minimum_bytes, int) or minimum_bytes < 0:
                findings.append(f"expected_outputs[{index}].minimum_bytes must be a non-negative integer")
            expected_hash = output.get("sha256")
            if expected_hash is not None and not _is_sha256(expected_hash):
                findings.append(f"expected_outputs[{index}].sha256 must be an exact SHA-256 identity")
    return findings


def verify_expected_outputs(record: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    for index, output in enumerate(record.get("expected_outputs", [])):
        path = Path(output["path"])
        if not path.is_file():
            findings.append(f"expected output does not exist: {path}")
            continue
        minimum_bytes = output.get("minimum_bytes", 1)
        if path.stat().st_size < minimum_bytes:
            findings.append(
                f"expected output is smaller than {minimum_bytes} bytes: {path}"
            )
            continue
        expected_hash = output.get("sha256")
        if expected_hash is not None:
            actual = _sha256(path)
            if actual != expected_hash:
                findings.append(
                    f"output identity mismatch for expected_outputs[{index}]: "
                    f"expected {expected_hash}, observed {actual}"
                )
    return findings


def assess(estimated_seconds: float, durable_record: dict[str, Any] | None = None) -> dict[str, Any]:
    if estimated_seconds < 0:
        return {"operation": "long-run-assessment", "status": "FAIL", "decision": "INVALID_ESTIMATE", "findings": ["estimated_seconds cannot be negative"]}
    if estimated_seconds <= TWO_HOURS_SECONDS:
        return {
            "operation": "long-run-assessment",
            "status": "PASS",
            "skill_version": SKILL_VERSION,
            "threshold_seconds": TWO_HOURS_SECONDS,
            "estimated_seconds": estimated_seconds,
            "decision": "CONTINUE_IN_SESSION",
            "conversation_action": "CONTINUE_CURRENT_TURN",
            "findings": [],
        }
    findings = validate_durable_record(durable_record or {})
    if findings:
        return {
            "operation": "long-run-assessment",
            "status": "BLOCKED",
            "skill_version": SKILL_VERSION,
            "threshold_seconds": TWO_HOURS_SECONDS,
            "estimated_seconds": estimated_seconds,
            "decision": "BLOCKED_NEEDS_DURABLE_LAUNCH",
            "conversation_action": "KEEP_WORK_LOCAL_UNTIL_DURABLE",
            "findings": findings,
        }
    return {
        "operation": "long-run-assessment",
        "status": "PASS",
        "skill_version": SKILL_VERSION,
        "threshold_seconds": TWO_HOURS_SECONDS,
        "estimated_seconds": estimated_seconds,
        "decision": "BACKGROUND_AND_YIELD",
        "conversation_action": "END_CURRENT_TURN",
        "durable_record": durable_record,
        "findings": [],
    }


def resume_decision(
    durable_record: dict[str, Any],
    observation: dict[str, Any],
    *,
    heartbeat_max_age_seconds: float = 300,
    now_timestamp: float | None = None,
) -> dict[str, Any]:
    findings = validate_durable_record(durable_record)
    if findings:
        identity_drift = any("frozen identity drift" in finding for finding in findings)
        return {
            "operation": "long-run-resume",
            "status": "BLOCKED",
            "decision": "IDENTITY_DRIFT_STOP" if identity_drift else "INVALID_DURABLE_RECORD",
            "frozen_identities_verified": False,
            "outputs_verified": False,
            "findings": findings,
        }
    status = observation.get("status")
    if status == "RUNNING":
        now = time.time() if now_timestamp is None else now_timestamp
        heartbeat_age = now - Path(durable_record["heartbeat_path"]).stat().st_mtime
        if -60 <= heartbeat_age <= heartbeat_max_age_seconds:
            return {
                "operation": "long-run-resume",
                "status": "PASS",
                "decision": "WAIT_AND_YIELD",
                "heartbeat_age_seconds": heartbeat_age,
                "frozen_identities_verified": True,
                "outputs_verified": False,
                "findings": [],
            }
        return {
            "operation": "long-run-resume",
            "status": "BLOCKED",
            "decision": "INVESTIGATE_STALE_HEARTBEAT",
            "heartbeat_age_seconds": heartbeat_age,
            "frozen_identities_verified": True,
            "outputs_verified": False,
            "findings": ["heartbeat is stale or has an invalid future timestamp"],
        }
    if status == "COMPLETED":
        output_findings = verify_expected_outputs(durable_record)
        if not output_findings:
            return {
                "operation": "long-run-resume",
                "status": "PASS",
                "decision": "RESUME_RESEARCH",
                "frozen_identities_verified": True,
                "outputs_verified": True,
                "findings": [],
            }
        return {
            "operation": "long-run-resume",
            "status": "BLOCKED",
            "decision": "VERIFY_BEFORE_CONTINUING",
            "frozen_identities_verified": True,
            "outputs_verified": False,
            "findings": output_findings,
        }
    if status in {"FAILED", "PARTIAL", "STOPPED"}:
        return {
            "operation": "long-run-resume",
            "status": "BLOCKED",
            "decision": "RESUME_FOR_RECOVERY",
            "frozen_identities_verified": True,
            "outputs_verified": False,
            "findings": [f"durable job ended with status {status}"],
        }
    return {
        "operation": "long-run-resume",
        "status": "BLOCKED",
        "decision": "OBSERVE_DURABLE_JOB_STATE",
        "frozen_identities_verified": True,
        "outputs_verified": False,
        "findings": ["durable job status is missing or unknown"],
    }


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    assess_parser = sub.add_parser("assess")
    assess_parser.add_argument("--estimated-seconds", type=float, required=True)
    assess_parser.add_argument("--durable-record", type=Path)
    resume_parser = sub.add_parser("resume")
    resume_parser.add_argument("observation", type=Path)
    resume_parser.add_argument("--durable-record", type=Path, required=True)
    resume_parser.add_argument("--heartbeat-max-age-seconds", type=float, default=300)
    args = parser.parse_args(argv)
    if args.command == "assess":
        result = assess(args.estimated_seconds, _read(args.durable_record) if args.durable_record else None)
    else:
        result = resume_decision(
            _read(args.durable_record),
            _read(args.observation),
            heartbeat_max_age_seconds=args.heartbeat_max_age_seconds,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
