#!/usr/bin/env python3
"""Validate host execution handoffs before they enter the control plane."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

FLOATING = {"", "main", "master", "head", "latest", "trunk"}
REQUIRED = ("producer", "skill", "exact_ref", "capability", "input_artifacts", "output_artifacts", "commands", "assumptions", "uncertainty", "permission_use", "evidence_anchors", "verification", "checker")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(value: Any, root: Path | None = None) -> dict[str, Any]:
    findings: list[str] = []
    if not isinstance(value, dict):
        return {"operation": "handoff-validate", "status": "FAIL", "findings": ["handoff must be an object"]}
    for field in REQUIRED:
        item = value.get(field)
        if item is None or item == "" or item == []:
            findings.append(f"{field} is required")
    if str(value.get("exact_ref", "")).lower() in FLOATING:
        findings.append("exact_ref must be pinned")
    if not isinstance(value.get("input_artifacts"), list) or not isinstance(value.get("output_artifacts"), list):
        findings.append("input_artifacts and output_artifacts must be lists")
    if not isinstance(value.get("commands"), list) or not value.get("commands"):
        findings.append("commands must record at least one host action")
    if not isinstance(value.get("permission_use"), (dict, list)):
        findings.append("permission_use must record permissions actually used")
    if not isinstance(value.get("verification"), (dict, str)):
        findings.append("verification must be a report or status")
    if root:
        root = root.resolve()
        for field in ("input_artifacts", "output_artifacts"):
            for item in value.get(field, []) if isinstance(value.get(field), list) else []:
                path = item.get("path") if isinstance(item, dict) else item
                if not isinstance(path, str):
                    findings.append(f"{field} contains an artifact without a path")
                    continue
                candidate = (root / path).resolve()
                try: candidate.relative_to(root)
                except ValueError: findings.append(f"{field} path escapes root: {path}")
                else:
                    if not candidate.exists(): findings.append(f"{field} is missing: {path}")
    status = "PASS" if not findings else "FAIL"
    return {"operation": "handoff-validate", "status": status, "findings": findings, "execution_state": "HANDOFF_RECEIVED" if status == "PASS" else "REJECTED"}


def accept(path: Path, root: Path | None = None) -> dict[str, Any]:
    result = validate(_read(path), root)
    if result["status"] == "PASS": result["execution_state"] = "CHECKED"
    return result | {"path": str(path)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "accept"):
        p = sub.add_parser(name); p.add_argument("handoff", type=Path); p.add_argument("--root", type=Path)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args(); result = accept(args.handoff, args.root) if args.command == "accept" else validate(_read(args.handoff), args.root); print(json.dumps(result, indent=2, ensure_ascii=False)); sys.exit(0 if result["status"] == "PASS" else 1)
