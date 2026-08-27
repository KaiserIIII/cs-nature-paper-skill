#!/usr/bin/env python3
"""Validate V3.1 machine-readable registries without third-party packages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "assets" / "registry"
CAP_FIELDS = ("id", "name", "department", "description", "input_types", "output_types", "scientific_risk", "required_permissions", "checker_requirement", "possible_native_tools", "specialist_triggers")
SKILL_FIELDS = ("skill_id", "source", "exact_ref", "license", "host_support", "capabilities", "inputs", "outputs", "permissions", "network", "credentials", "write_scope", "runtime", "context_cost", "estimated_tool_cost", "known_risks", "adoption_status", "runtime_status", "last_reviewed", "behavior_trials", "rollback")
FLOATING = {"", "head", "latest", "main", "master", "trunk"}


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError(f"{path} must contain an object")
    return value


def validate(registry_dir: Path = REGISTRY) -> dict[str, Any]:
    findings: list[str] = []
    capabilities = _read(registry_dir / "capabilities.json"); catalog = _read(registry_dir / "skill_catalog.json"); methods = _read(registry_dir / "method_router.json")
    if capabilities.get("skill_version") != "3.1.0" or catalog.get("skill_version") != "3.1.0" or methods.get("skill_version") != "3.1.0": findings.append("all registries must declare skill_version 3.1.0")
    cap_ids = []
    for index, item in enumerate(capabilities.get("capabilities", [])):
        if not isinstance(item, dict): findings.append(f"capabilities[{index}] must be an object"); continue
        cap_ids.append(item.get("id")); findings.extend(f"capabilities[{index}].{field} is required" for field in CAP_FIELDS if field not in item)
        for field in ("input_types", "output_types", "required_permissions", "possible_native_tools", "specialist_triggers"):
            if not isinstance(item.get(field), list): findings.append(f"capabilities[{index}].{field} must be a list")
    if len(cap_ids) != len(set(cap_ids)): findings.append("capability ids must be unique")
    skill_ids = []
    for index, item in enumerate(catalog.get("skills", [])):
        if not isinstance(item, dict): findings.append(f"skills[{index}] must be an object"); continue
        skill_ids.append(item.get("skill_id")); findings.extend(f"skills[{index}].{field} is required" for field in SKILL_FIELDS if field not in item)
        if str(item.get("exact_ref", "")).lower() in FLOATING: findings.append(f"skills[{index}] exact_ref must be pinned")
        if item.get("runtime_status") == "APPROVED" and str(item.get("exact_ref", "")).lower() in FLOATING: findings.append(f"skills[{index}] approved runtime cannot use floating ref")
        if item.get("adoption_status") not in {"INSPIRED", "REFERENCED", "NOT_USED"}: findings.append(f"skills[{index}] adoption_status invalid")
        if item.get("runtime_status") not in {"APPROVED", "PROVISIONAL", "SPECIALIST", "QUARANTINED", "REJECTED", "UNASSESSED"}: findings.append(f"skills[{index}] runtime_status invalid")
        unknown = sorted(set(item.get("capabilities", [])) - set(cap_ids))
        if unknown: findings.append(f"skills[{index}] references unknown capabilities: {unknown}")
    if len(skill_ids) != len(set(skill_ids)): findings.append("skill ids must be unique")
    method_ids = [item.get("id") for item in methods.get("methods", []) if isinstance(item, dict)]
    if len(method_ids) < 13: findings.append("method router must cover at least 13 method families")
    if len(method_ids) != len(set(method_ids)): findings.append("method ids must be unique")
    return {"operation": "validate-registry", "status": "PASS" if not findings else "FAIL", "capability_count": len(cap_ids), "skill_count": len(skill_ids), "method_count": len(method_ids), "findings": findings}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--registry-dir", type=Path, default=REGISTRY); return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try: result = validate(args.registry_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc: print(json.dumps({"status":"ERROR","error":str(exc)})); return 2
    print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__": sys.exit(main())
