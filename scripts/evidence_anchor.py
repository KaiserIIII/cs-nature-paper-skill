#!/usr/bin/env python3
"""Validate V3 evidence anchors and evidence-ledger anchor collections."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

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
    if not isinstance(value.get("exit_status"), int): findings.append("exit_status must be an integer")
    if value.get("status") not in STATUSES: findings.append(f"status must be one of {sorted(STATUSES)}")
    if not UTC.match(str(value.get("verified_utc", ""))): findings.append("verified_utc must use YYYY-MM-DDTHH:MM:SSZ")
    if value.get("status") == "VERIFIED" and value.get("exit_status") != 0: findings.append("VERIFIED anchor requires exit_status 0")
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def validate_path(path: Path) -> dict[str, Any]:
    value = _read(path)
    if isinstance(value, dict) and isinstance(value.get("anchors"), list):
        findings: list[str] = []
        for index, anchor in enumerate(value["anchors"]):
            result = validate_anchor(anchor)
            findings.extend(f"anchors[{index}]: {finding}" for finding in result["findings"])
        return {"operation": "ledger", "status": "PASS" if not findings else "FAIL", "anchor_count": len(value["anchors"]), "findings": findings}
    result = validate_anchor(value); result.update({"operation": "validate", "path": str(path)}); return result


def ledger_path(project: Path) -> Path:
    state = project.resolve() / ".research-state-v3"
    if not state.exists(): state = project.resolve() / ".research-state"
    return state / "evidence_ledger.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("validate", help="validate one anchor JSON"); p.add_argument("path", type=Path)
    p = subs.add_parser("ledger", help="validate anchors in a project ledger"); p.add_argument("project", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = validate_path(args.path if args.command == "validate" else ledger_path(args.project))
    except AnchorError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False)); return 2
    print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__": sys.exit(main())
