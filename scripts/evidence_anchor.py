#!/usr/bin/env python3
"""Validate V3.1 evidence anchors, including optional deep provenance checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REQUIRED = ("anchor_id", "claim_id", "result_id", "source_artifact", "exact_region", "transformation", "command", "exit_status", "code_commit", "config_hash", "environment", "input_hash", "uncertainty", "scope", "status", "verified_utc")
STATUSES = {"VERIFIED", "UNVERIFIED", "CONTRADICTS", "QUALIFIES"}
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class AnchorError(RuntimeError):
    pass


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise AnchorError(f"invalid JSON: {path}") from exc


def validate_anchor(value: Any) -> dict[str, Any]:
    findings: list[str] = []
    if not isinstance(value, dict):
        return {"status": "FAIL", "findings": ["anchor must be an object"]}
    findings.extend(f"{field} is required" for field in REQUIRED if field != "exit_status" and (not isinstance(value.get(field), str) or not value[field].strip()))
    if not isinstance(value.get("exit_status"), int):
        findings.append("exit_status must be an integer")
    if value.get("status") not in STATUSES:
        findings.append(f"status must be one of {sorted(STATUSES)}")
    if not UTC.match(str(value.get("verified_utc", ""))):
        findings.append("verified_utc must use YYYY-MM-DDTHH:MM:SSZ")
    if value.get("status") == "VERIFIED" and value.get("exit_status") != 0:
        findings.append("VERIFIED anchor requires exit_status 0")
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def deep_validate_anchor(value: Any, root: Path) -> dict[str, Any]:
    """Verify locally inspectable provenance; external sources remain conditional."""
    basic = validate_anchor(value)
    if basic["status"] == "FAIL":
        return basic | {"verification": "deep"}
    findings: list[str] = []
    conditional: list[str] = []
    source = str(value["source_artifact"])
    parsed = urlparse(source)
    if parsed.scheme and parsed.netloc:
        conditional.append("source artifact is external and cannot be locally hash-verified")
    else:
        raw_path, _, fragment = source.partition("#")
        candidate = (root / raw_path).resolve()
        if not _inside(root.resolve(), candidate):
            findings.append("source artifact escapes verification root")
        elif not candidate.exists() or not candidate.is_file():
            findings.append(f"source artifact does not exist: {raw_path}")
        else:
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            match = re.search(r"sha256=([0-9a-fA-F]{64})", fragment)
            expected = match.group(1).lower() if match else str(value.get("source_sha256", "")).removeprefix("sha256:").lower()
            if expected and digest != expected:
                findings.append("source artifact hash does not match")
            if not expected:
                conditional.append("source artifact has no declared sha256")
            region = str(value.get("exact_region", ""))
            line_match = re.search(r"(?:line|row)\s+(\d+)", region, re.IGNORECASE)
            if line_match and int(line_match.group(1)) > len(candidate.read_text(encoding="utf-8", errors="replace").splitlines()):
                findings.append("exact_region line is outside source artifact")
    if value.get("code_commit") and (root / ".git").exists():
        try:
            subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"{value['code_commit']}^{{commit}}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, OSError):
            findings.append("code_commit cannot be resolved in project git repository")
    if value.get("checker_required") and not value.get("checker"):
        findings.append("checker is required for this anchor")
    status = "FAIL" if findings else ("CONDITIONAL" if conditional else "PASS")
    return {"status": status, "verification": "deep", "findings": findings, "conditional": conditional, "source_artifact": source}


def validate_path(path: Path, *, deep: bool = False, root: Path | None = None) -> dict[str, Any]:
    value = _read(path)
    if isinstance(value, dict) and isinstance(value.get("anchors"), list):
        findings: list[str] = []
        conditional: list[str] = []
        for index, anchor in enumerate(value["anchors"]):
            result = deep_validate_anchor(anchor, root or path.parent) if deep else validate_anchor(anchor)
            findings.extend(f"anchors[{index}]: {finding}" for finding in result["findings"])
            conditional.extend(f"anchors[{index}]: {item}" for item in result.get("conditional", []))
        status = "FAIL" if findings else ("CONDITIONAL" if conditional else "PASS")
        return {"operation": "ledger", "status": status, "anchor_count": len(value["anchors"]), "findings": findings, "conditional": conditional}
    result = deep_validate_anchor(value, root or path.parent) if deep else validate_anchor(value)
    result.update({"operation": "validate", "path": str(path)})
    return result


def ledger_path(project: Path) -> Path:
    state = project.resolve() / ".research-state-v31"
    if not state.exists(): state = project.resolve() / ".research-state-v3"
    if not state.exists(): state = project.resolve() / ".research-state"
    return state / "evidence_ledger.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("validate", help="validate one anchor JSON"); p.add_argument("path", type=Path); p.add_argument("--deep", action="store_true"); p.add_argument("--root", type=Path)
    p = subs.add_parser("ledger", help="validate anchors in a project ledger"); p.add_argument("project", type=Path); p.add_argument("--deep", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = validate_path(args.path, deep=args.deep, root=args.root) if args.command == "validate" else validate_path(ledger_path(args.project), deep=args.deep, root=args.project)
    except AnchorError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False)); return 2
    print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result["status"] in {"PASS", "CONDITIONAL"} else 1


if __name__ == "__main__": sys.exit(main())
