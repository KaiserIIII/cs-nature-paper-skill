#!/usr/bin/env python3
"""Resolve research capabilities into the smallest qualified runtime team."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SKILL_VERSION = "3.1.0"
FLOATING_REFS = {"", "head", "latest", "main", "master", "trunk"}
STATUS_ORDER = {"APPROVED": 0, "SPECIALIST": 1, "PROVISIONAL": 2, "UNASSESSED": 3, "QUARANTINED": 4, "REJECTED": 5}


class RouterError(RuntimeError):
    pass


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "assets" / "registry"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise RouterError(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise RouterError(f"JSON root must be an object: {path}")
    return value


def _paths(registry_dir: Path) -> tuple[Path, Path]:
    return registry_dir / "capabilities.json", registry_dir / "skill_catalog.json"


def load_catalog(registry_dir: Path = REGISTRY_DIR) -> tuple[dict[str, Any], dict[str, Any]]:
    capability_path, catalog_path = _paths(registry_dir)
    capabilities, catalog = _read(capability_path), _read(catalog_path)
    if capabilities.get("skill_version") != SKILL_VERSION or catalog.get("skill_version") != SKILL_VERSION:
        raise RouterError("registry skill_version must match runtime " + SKILL_VERSION)
    if not isinstance(capabilities.get("capabilities"), list) or not isinstance(catalog.get("skills"), list):
        raise RouterError("capability and skill registries must contain lists")
    return capabilities, catalog


def _project_registry(project: Path | None) -> dict[str, Any] | None:
    if project is None:
        return None
    project = project.resolve()
    for directory in (".research-state-v31", ".research-state-v3", ".research-state"):
        path = project / directory / "employee_registry.json"
        if path.exists():
            return _read(path)
    return None


def _active(skill: dict[str, Any]) -> bool:
    return skill.get("runtime_status") in {"APPROVED", "SPECIALIST", "PROVISIONAL"}


def _permission_gaps(required: list[str], skill: dict[str, Any]) -> list[str]:
    permissions = skill.get("permissions") if isinstance(skill.get("permissions"), dict) else {}
    gaps: list[str] = []
    for permission in required:
        if permission == "network" and not skill.get("network", permissions.get("network", False)):
            gaps.append(permission)
        elif permission == "credentials" and not skill.get("credentials", permissions.get("credentials", False)):
            gaps.append(permission)
        elif permission in {"local_write", "execute"} and permission not in skill.get("write_scope", []) and permission == "local_write":
            if "project-local" not in skill.get("write_scope", []):
                gaps.append(permission)
        elif permission == "execute" and not permissions.get("executes_scripts", False):
            gaps.append(permission)
    return gaps


def _candidate_skills(capability: str, catalog: dict[str, Any]) -> list[dict[str, Any]]:
    return [skill for skill in catalog["skills"] if capability in skill.get("capabilities", []) and _active(skill)]


def resolve(capability: str, *, project: Path | None = None, registry_dir: Path = REGISTRY_DIR) -> dict[str, Any]:
    capabilities, catalog = load_catalog(registry_dir)
    capability_doc = next((item for item in capabilities["capabilities"] if item.get("id") == capability), None)
    if capability_doc is None:
        raise RouterError(f"unknown capability: {capability}")
    candidates = _candidate_skills(capability, catalog)
    ranked = sorted(candidates, key=lambda item: (STATUS_ORDER.get(item.get("runtime_status"), 9), item.get("context_cost", "unknown"), item.get("skill_id", "")))
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    required_permissions = capability_doc.get("required_permissions", [])
    for skill in ranked:
        gaps = _permission_gaps(required_permissions, skill)
        record = {"skill_id": skill.get("skill_id"), "exact_ref": skill.get("exact_ref"), "runtime_status": skill.get("runtime_status"), "permission_gaps": gaps, "risk": skill.get("known_risks", [])}
        if skill.get("runtime_status") in {"QUARANTINED", "REJECTED"} or gaps:
            rejected.append(record)
        else:
            selected.append(record)
    native = capability_doc.get("possible_native_tools", [])
    checker = capability_doc.get("checker_requirement", "")
    status = "PASS" if selected or native else "FAIL"
    if required_permissions and not selected and native:
        status = "CONDITIONAL"
    return {"operation": "resolve", "status": status, "capability": capability, "native_coverage": "AVAILABLE" if native else "NONE", "candidate_employees": selected + rejected, "selected": selected[:1], "checker": checker, "permissions_required": required_permissions, "risk": capability_doc.get("scientific_risk"), "specialist_triggers": capability_doc.get("specialist_triggers", []), "rejected": rejected}


def team(task: str, capabilities: list[str], *, project: Path | None = None, registry_dir: Path = REGISTRY_DIR) -> dict[str, Any]:
    resolved = [resolve(capability, project=project, registry_dir=registry_dir) for capability in capabilities]
    failures = [item for item in resolved if item["status"] == "FAIL"]
    selected: dict[str, dict[str, Any]] = {}
    for item in resolved:
        for employee in item["selected"]:
            selected[employee["skill_id"]] = employee
    return {"operation": "team", "status": "FAIL" if failures else ("CONDITIONAL" if any(item["status"] == "CONDITIONAL" for item in resolved) else "PASS"), "task": task, "required_capabilities": capabilities, "team": list(selected.values()), "resolutions": resolved, "smallest_qualified_team": len(selected), "failure_capabilities": [item["capability"] for item in failures]}


def inventory(*, project: Path | None = None, registry_dir: Path = REGISTRY_DIR) -> dict[str, Any]:
    capabilities, catalog = load_catalog(registry_dir)
    employee_registry = _project_registry(project)
    employees = employee_registry.get("employees", []) if employee_registry else []
    return {"operation": "inventory", "status": "PASS", "capabilities": [item["id"] for item in capabilities["capabilities"]], "skills": [{"skill_id": item.get("skill_id"), "runtime_status": item.get("runtime_status"), "capabilities": item.get("capabilities", [])} for item in catalog["skills"]], "qualified_project_employees": [item.get("id") for item in employees if item.get("status") in {"APPROVED", "SPECIALIST", "PROVISIONAL"}]}


def validate_plan(path: Path, *, registry_dir: Path = REGISTRY_DIR) -> dict[str, Any]:
    plan = _read(path)
    required = ("task", "capability", "employee", "exact_ref", "input_artifacts", "allowed_context", "forbidden_context", "allowed_tools", "forbidden_tools", "expected_output", "output_schema", "checker", "timeout", "cost_budget", "failure_path", "rollback")
    findings = [f"{field} is required" for field in required if plan.get(field) in (None, "", [])]
    _, catalog = load_catalog(registry_dir)
    employees = {item.get("skill_id"): item for item in catalog["skills"]}
    employee = employees.get(plan.get("employee"))
    if employee is None:
        findings.append("employee is not in skill catalog")
    elif plan.get("exact_ref") != employee.get("exact_ref"):
        findings.append("exact_ref does not match catalog pin")
    if str(plan.get("exact_ref", "")).lower() in FLOATING_REFS:
        findings.append("exact_ref must not be floating")
    overlap = sorted(set(plan.get("allowed_tools", [])) & set(plan.get("forbidden_tools", [])))
    if overlap:
        findings.append(f"tool appears in both allowed and forbidden: {overlap}")
    private_forbidden = {"credentials", "tokens", "private review letters", "editor correspondence"}
    if private_forbidden & set(plan.get("allowed_context", [])):
        findings.append("private material cannot be allowed context")
    return {"operation": "validate-plan", "status": "PASS" if not findings else "FAIL", "findings": findings, "plan": str(path)}


def explain(capability: str, *, registry_dir: Path = REGISTRY_DIR) -> dict[str, Any]:
    result = resolve(capability, registry_dir=registry_dir)
    result["selection_policy"] = ["critical capability coverage", "scientific fit", "qualification status", "least privilege", "provenance", "checker independence", "host compatibility", "context/runtime cost", "maintenance"]
    result["note"] = "Stars and aggregate scores are never used as evidence of qualification."
    return result | {"operation": "explain"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--version", action="version", version=f"%(prog)s {SKILL_VERSION}"); parser.add_argument("--registry-dir", type=Path, default=REGISTRY_DIR)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("inventory", "resolve", "team", "validate-plan", "explain"):
        p = subs.add_parser(name)
        if name in {"inventory", "resolve", "team"}: p.add_argument("--project", type=Path)
        if name in {"resolve", "explain"}: p.add_argument("--capability", required=True)
        if name == "team": p.add_argument("task"); p.add_argument("--capability", action="append", dest="capabilities", required=True)
        if name == "validate-plan": p.add_argument("plan", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inventory": result = inventory(project=args.project, registry_dir=args.registry_dir)
        elif args.command == "resolve": result = resolve(args.capability, project=args.project, registry_dir=args.registry_dir)
        elif args.command == "team": result = team(args.task, args.capabilities, project=args.project, registry_dir=args.registry_dir)
        elif args.command == "validate-plan": result = validate_plan(args.plan, registry_dir=args.registry_dir)
        else: result = explain(args.capability, registry_dir=args.registry_dir)
    except RouterError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False)); return 2
    print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result["status"] in {"PASS", "CONDITIONAL"} else 1


if __name__ == "__main__":
    sys.exit(main())
