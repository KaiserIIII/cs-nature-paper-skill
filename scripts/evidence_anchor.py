#!/usr/bin/env python3
"""Validate evidence anchors and observed execution provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REQUIRED = ("anchor_id", "claim_id", "result_id", "source_artifact", "exact_region", "transformation", "uncertainty", "scope", "status")
STATUSES = {"DECLARED", "OBSERVED", "VERIFIED", "UNVERIFIED", "CONTRADICTS", "QUALIFIES"}
LEVELS = {"DECLARED", "OBSERVED", "VERIFIED"}
SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
RAW_SHA = re.compile(r"^[0-9a-f]{64}$")
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class AnchorError(RuntimeError):
    pass


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise AnchorError(f"invalid JSON: {path}") from exc


def _level(value: dict[str, Any]) -> tuple[str, bool]:
    if value.get("provenance_level") in LEVELS:
        return value["provenance_level"], False
    # Historical status is retained as metadata but never upgrades provenance.
    return "DECLARED", True


def validate_anchor(value: Any) -> dict[str, Any]:
    findings: list[str] = []
    if not isinstance(value, dict):
        return {"status": "FAIL", "findings": ["anchor must be an object"]}
    for field in REQUIRED:
        if not isinstance(value.get(field), str) or not value[field].strip():
            findings.append(f"{field} is required")
    level, legacy = _level(value)
    if value.get("provenance_level") is not None and value.get("provenance_level") not in LEVELS:
        findings.append("provenance_level must be DECLARED, OBSERVED, or VERIFIED")
    if value.get("status") not in STATUSES:
        findings.append(f"status must be one of {sorted(STATUSES)}")
    for field in ("config_hash", "input_hash", "stdout_sha256", "stderr_sha256"):
        if field in value and value[field] and not SHA.fullmatch(str(value[field])):
            # Legacy V3 anchors are accepted at the shallow boundary only.
            if not legacy or field not in {"config_hash", "input_hash"}:
                findings.append(f"{field} must match sha256:<64 lowercase hex>")
    if value.get("source_sha256") and not RAW_SHA.fullmatch(str(value["source_sha256"])):
        findings.append("source_sha256 must be 64 lowercase hex characters")
    if level == "VERIFIED" and value.get("exit_status") is not None and value.get("exit_status") != 0:
        findings.append("VERIFIED anchor requires exit_status 0")
    if level in {"OBSERVED", "VERIFIED"} and not legacy:
        execution_ref = value.get("execution_record_id") or value.get("execution_record")
        acquisition_ref = value.get("artifact_acquisition_record_id") or value.get("artifact_acquisition_record")
        if not execution_ref and not acquisition_ref:
            findings.append(f"{level} anchor requires execution_record_id or artifact_acquisition_record_id")
        if execution_ref and (not value.get("command") or not value.get("cwd") or value.get("exit_status") is None):
            findings.append(f"{level} anchor requires observed command, cwd, and exit_status")
    if level == "VERIFIED" and not legacy:
        if not value.get("checker"):
            findings.append("VERIFIED anchor requires an independent checker")
        for field in ("config_hash", "input_hash"):
            if not SHA.fullmatch(str(value.get(field, ""))):
                findings.append(f"VERIFIED anchor requires {field}")
        if value.get("code_version_type") not in {"git_commit", "content_hash", "release_id", "not_applicable"}:
            findings.append("VERIFIED anchor requires code_version_type")
        if not value.get("code_version"):
            findings.append("VERIFIED anchor requires code_version")
        source = str(value.get("source_artifact", ""))
        if not value.get("source_sha256") and not re.search(r"#sha256=[0-9a-fA-F]{64}$", source):
            findings.append("VERIFIED anchor requires an output artifact hash")
    result = {
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "provenance_level": level,
        "legacy": legacy,
    }
    if legacy:
        result.update({"legacy_status": value.get("status"), "migration_state": "LEGACY_DECLARED"})
    return result


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _git_commit_exists(root: Path, commit: str) -> bool:
    try:
        subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"{commit}^{{commit}}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


def _artifact_path(path: Path, cwd: Path) -> Path:
    return path.resolve() if path.is_absolute() else (cwd / path).resolve()


def _record_path(path: Path, cwd: Path) -> str:
    try:
        return path.relative_to(cwd).as_posix()
    except ValueError:
        return str(path)


def execution_record(path: Path, command: list[str] | str, *, cwd: Path, input_paths: list[Path] | None = None, output_paths: list[Path] | None = None, environment: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a command and write the only trustworthy exit status record."""
    argv = command if isinstance(command, list) else shlex.split(command)
    cwd = cwd.resolve()
    inputs = [_artifact_path(item, cwd) for item in input_paths or []]
    declared_outputs = [_artifact_path(item, cwd) for item in output_paths or []]
    input_set = set(inputs)
    undeclared_preexisting = [item for item in declared_outputs if item.exists() and item not in input_set]
    if undeclared_preexisting:
        joined = ", ".join(str(item) for item in undeclared_preexisting)
        raise AnchorError(f"declared output already exists before command: {joined}")
    before = {
        item: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in declared_outputs
        if item.exists() and item.is_file()
    }
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    started_unix_ns = time.time_ns()
    timer = time.monotonic()
    completed = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=False, check=False)
    finished_unix_ns = time.time_ns()
    finished = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    findings: list[str] = []
    if completed.returncode != 0:
        findings.append(f"command exited with status {completed.returncode}")
    record = {
        "record_id": path.stem, "command": " ".join(argv), "argv": argv, "cwd": str(cwd),
        "exit_status": completed.returncode, "started_utc": started, "finished_utc": finished,
        "started_unix_ns": started_unix_ns, "finished_unix_ns": finished_unix_ns,
        "stdout_sha256": "sha256:" + hashlib.sha256(completed.stdout).hexdigest(),
        "stderr_sha256": "sha256:" + hashlib.sha256(completed.stderr).hexdigest(),
        "environment": environment or {"python": sys.version.split()[0]}, "inputs": [],
        "outputs": [], "preexisting_artifacts": [],
        "wall_time_seconds": round(time.monotonic() - timer, 6),
    }
    for item in inputs:
        if item.exists() and item.is_file():
            record["inputs"].append({"path": _record_path(item, cwd), "sha256": "sha256:" + hashlib.sha256(item.read_bytes()).hexdigest()})
        else:
            findings.append(f"input artifact does not exist: {_record_path(item, cwd)}")
    for output in declared_outputs:
        relative = _record_path(output, cwd)
        if output in before:
            record["preexisting_artifacts"].append({
                "path": relative,
                "sha256_before": "sha256:" + before[output],
                "sha256_after": "sha256:" + hashlib.sha256(output.read_bytes()).hexdigest() if output.is_file() else None,
                "produced_by_command": False,
            })
            continue
        if not output.exists() or not output.is_file():
            findings.append(f"command did not create declared output: {relative}")
            continue
        stat = output.stat()
        if stat.st_mtime_ns < started_unix_ns:
            findings.append(f"declared output predates execution start: {relative}")
            continue
        record["outputs"].append({
            "path": relative,
            "sha256": "sha256:" + hashlib.sha256(output.read_bytes()).hexdigest(),
            "mtime_unix_ns": stat.st_mtime_ns,
            "produced_by_command": True,
            "existed_before": False,
        })
    record["findings"] = findings
    record["status"] = "PASS" if not findings else "FAIL"
    record["provenance_level"] = "OBSERVED" if not findings else "DECLARED"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def _load_execution(value: dict[str, Any], root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    ref = value.get("execution_record") or value.get("execution_record_id")
    if not ref:
        return None, []
    path = Path(str(ref))
    if not path.is_absolute():
        path = (root / path).resolve()
    if not path.exists():
        return None, [f"execution record does not exist: {ref}"]
    try:
        record = _read(path)
    except AnchorError as exc:
        return None, [str(exc)]
    return record, []


def deep_validate_anchor(value: Any, root: Path) -> dict[str, Any]:
    basic = validate_anchor(value)
    if basic["status"] == "FAIL":
        return basic | {"verification": "deep"}
    findings: list[str] = []
    conditional: list[str] = []
    level, legacy = basic["provenance_level"], basic["legacy"]
    source = str(value["source_artifact"])
    parsed = urlparse(source)
    candidate: Path | None = None
    artifact_digest = ""
    if parsed.scheme and parsed.netloc:
        conditional.append("source artifact is external and cannot be locally hash-verified")
    else:
        raw_path, _, fragment = source.partition("#")
        candidate = (root / raw_path).resolve()
        if not _inside(root.resolve(), candidate): findings.append("source artifact escapes verification root")
        elif not candidate.exists() or not candidate.is_file(): findings.append(f"source artifact does not exist: {raw_path}")
        else:
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            artifact_digest = digest
            match = re.search(r"sha256=([0-9a-fA-F]{64})", fragment)
            expected = match.group(1).lower() if match else str(value.get("source_sha256", "")).lower()
            if expected and digest != expected: findings.append("source artifact hash does not match")
            if not expected: conditional.append("source artifact has no declared sha256")
            region = str(value.get("exact_region", "")); line_match = re.search(r"(?:line|row)\s+(\d+)", region, re.I)
            if line_match and int(line_match.group(1)) > len(candidate.read_text(encoding="utf-8", errors="replace").splitlines()): findings.append("exact_region line is outside source artifact")
    if value.get("code_version_type") == "git_commit":
        if not _git_commit_exists(root, str(value.get("code_version") or value.get("code_commit", ""))): findings.append("git code_version cannot be resolved in project repository")
    elif value.get("code_version_type") == "content_hash" and not SHA.fullmatch(str(value.get("code_version", ""))):
        findings.append("content_hash code_version must be sha256:<64 lowercase hex>")
    elif value.get("code_commit") and (root / ".git").exists() and not legacy and not _git_commit_exists(root, str(value["code_commit"])):
        findings.append("code_commit cannot be resolved in project git repository")
    if value.get("checker_required") and not value.get("checker"): findings.append("checker is required for this anchor")
    if level in {"OBSERVED", "VERIFIED"} and not legacy:
        record, record_findings = _load_execution(value, root); findings.extend(record_findings)
        if record:
            for field in ("command", "cwd", "exit_status", "started_utc", "finished_utc", "stdout_sha256", "stderr_sha256"):
                if field not in record: findings.append(f"execution record missing {field}")
            if record.get("status") != "PASS": findings.append("execution record did not pass output provenance checks")
            if value.get("exit_status") is not None and value.get("exit_status") != record.get("exit_status"): findings.append("anchor exit_status differs from observed execution record")
            if record.get("exit_status") != 0 and level == "VERIFIED": findings.append("VERIFIED anchor requires observed execution exit_status 0")
            if candidate is not None and candidate.exists():
                record_cwd = Path(str(record.get("cwd", root)))
                produced = []
                for item in record.get("outputs", []):
                    if not isinstance(item, dict) or not item.get("produced_by_command"):
                        continue
                    output_path = Path(str(item.get("path", "")))
                    resolved = output_path.resolve() if output_path.is_absolute() else (record_cwd / output_path).resolve()
                    if resolved == candidate.resolve():
                        produced.append(item)
                if not produced:
                    findings.append("anchor source artifact is not a produced output in the execution record")
                elif produced[0].get("sha256") != "sha256:" + artifact_digest:
                    findings.append("anchor source artifact hash differs from produced output hash")
    status = "FAIL" if findings else ("CONDITIONAL" if conditional else "PASS")
    return {"status": status, "verification": "deep", "provenance_level": level, "findings": findings, "conditional": conditional, "source_artifact": source}


def validate_path(path: Path, *, deep: bool = False, root: Path | None = None) -> dict[str, Any]:
    value = _read(path)
    base = root or path.parent
    if isinstance(value, dict) and isinstance(value.get("anchors"), list):
        findings: list[str] = []; conditional: list[str] = []
        for index, anchor in enumerate(value["anchors"]):
            result = deep_validate_anchor(anchor, base) if deep else validate_anchor(anchor)
            findings.extend(f"anchors[{index}]: {item}" for item in result["findings"]); conditional.extend(f"anchors[{index}]: {item}" for item in result.get("conditional", []))
        return {"operation": "ledger", "status": "FAIL" if findings else ("CONDITIONAL" if conditional else "PASS"), "anchor_count": len(value["anchors"]), "findings": findings, "conditional": conditional}
    result = deep_validate_anchor(value, base) if deep else validate_anchor(value); result.update({"operation": "validate", "path": str(path)}); return result


def ledger_path(project: Path) -> Path:
    project = project.resolve()
    for directory in (".research-state-v31", ".research-state-v3", ".research-state"):
        path = project / directory / "evidence_ledger.json"
        if path.exists(): return path
    return project / ".research-state-v31" / "evidence_ledger.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("validate"); p.add_argument("path", type=Path); p.add_argument("--deep", action="store_true"); p.add_argument("--root", type=Path)
    p = subs.add_parser("ledger"); p.add_argument("project", type=Path); p.add_argument("--deep", action="store_true")
    p = subs.add_parser("execute"); p.add_argument("record", type=Path); p.add_argument("--cwd", type=Path, default=Path.cwd()); p.add_argument("argv", nargs="+")
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    try:
        if args.command == "execute":
            record = execution_record(args.record, args.argv, cwd=args.cwd)
            result = {"operation": "execute", "status": "OBSERVED" if record["status"] == "PASS" else "FAIL", "record": record}
        else: result = validate_path(args.path, deep=args.deep, root=getattr(args, "root", None)) if args.command == "validate" else validate_path(ledger_path(args.project), deep=args.deep, root=args.project)
    except AnchorError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False)); sys.exit(2)
    print(json.dumps(result, indent=2, ensure_ascii=False)); sys.exit(0 if result["status"] in {"PASS", "CONDITIONAL", "OBSERVED"} else 1)
