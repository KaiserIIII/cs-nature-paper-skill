#!/usr/bin/env python3
"""Validate evidence anchors and observed execution provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
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
    # V3.1 compatibility: old anchors used status=VERIFIED without execution
    # records. They remain legacy declarations until re-recorded by the runtime.
    return ("VERIFIED" if value.get("status") == "VERIFIED" else "DECLARED"), True


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
    if value.get("status") == "VERIFIED" and value.get("exit_status") is not None and value.get("exit_status") != 0:
        findings.append("VERIFIED anchor requires exit_status 0")
    if level in {"OBSERVED", "VERIFIED"} and not legacy:
        if not value.get("execution_record_id") and not value.get("execution_record"):
            findings.append(f"{level} anchor requires execution_record_id")
        if not value.get("command") or not value.get("cwd") or value.get("exit_status") is None:
            findings.append(f"{level} anchor requires observed command, cwd, and exit_status")
    return {"status": "PASS" if not findings else "FAIL", "findings": findings, "provenance_level": level, "legacy": legacy}


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


def execution_record(path: Path, command: list[str] | str, *, cwd: Path, input_paths: list[Path] | None = None, output_paths: list[Path] | None = None, environment: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a command and write the only trustworthy exit status record."""
    import shlex
    import time
    argv = command if isinstance(command, list) else shlex.split(command)
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    timer = time.monotonic()
    completed = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=False, check=False)
    finished = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    record = {
        "record_id": path.stem, "command": " ".join(argv), "argv": argv, "cwd": str(cwd),
        "exit_status": completed.returncode, "started_utc": started, "finished_utc": finished,
        "stdout_sha256": "sha256:" + hashlib.sha256(completed.stdout).hexdigest(),
        "stderr_sha256": "sha256:" + hashlib.sha256(completed.stderr).hexdigest(),
        "environment": environment or {"python": sys.version.split()[0]}, "outputs": [],
        "wall_time_seconds": round(time.monotonic() - timer, 6),
    }
    for output in output_paths or []:
        if output.exists() and output.is_file():
            record["outputs"].append({"path": str(output), "sha256": "sha256:" + hashlib.sha256(output.read_bytes()).hexdigest()})
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
    if parsed.scheme and parsed.netloc:
        conditional.append("source artifact is external and cannot be locally hash-verified")
    else:
        raw_path, _, fragment = source.partition("#")
        candidate = (root / raw_path).resolve()
        if not _inside(root.resolve(), candidate): findings.append("source artifact escapes verification root")
        elif not candidate.exists() or not candidate.is_file(): findings.append(f"source artifact does not exist: {raw_path}")
        else:
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
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
            if value.get("exit_status") is not None and value.get("exit_status") != record.get("exit_status"): findings.append("anchor exit_status differs from observed execution record")
            if record.get("exit_status") != 0 and level == "VERIFIED": findings.append("VERIFIED anchor requires observed execution exit_status 0")
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
        if args.command == "execute": result = {"operation": "execute", "status": "OBSERVED", "record": execution_record(args.record, args.argv, cwd=args.cwd)}
        else: result = validate_path(args.path, deep=args.deep, root=getattr(args, "root", None)) if args.command == "validate" else validate_path(ledger_path(args.project), deep=args.deep, root=args.project)
    except AnchorError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False)); sys.exit(2)
    print(json.dumps(result, indent=2, ensure_ascii=False)); sys.exit(0 if result["status"] in {"PASS", "CONDITIONAL", "OBSERVED"} else 1)
