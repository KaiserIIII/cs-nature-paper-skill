#!/usr/bin/env python3
"""Resolve capabilities while keeping selection separate from execution."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SKILL_VERSION = "3.1.1"
FLOATING_REFS = {"", "head", "latest", "main", "master", "trunk"}
ACTIVE = {"APPROVED", "SPECIALIST", "PROVISIONAL"}
COST_ORDER = {"low": 0, "medium": 1, "high": 2, "unknown": 3}


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


def load_catalog(registry_dir: Path = REGISTRY_DIR) -> tuple[dict[str, Any], dict[str, Any]]:
    capabilities = _read(registry_dir / "capabilities.json")
    catalog = _read(registry_dir / "skill_catalog.json")
    if capabilities.get("skill_version") != SKILL_VERSION or catalog.get("skill_version") != SKILL_VERSION:
        raise RouterError(f"registry skill_version must match runtime {SKILL_VERSION}")
    if not isinstance(capabilities.get("capabilities"), list) or not isinstance(catalog.get("skills"), list):
        raise RouterError("capability and skill registries must contain lists")
    return capabilities, catalog


def _project_registry(project: Path | None) -> dict[str, Any] | None:
    if project is None:
        return None
    for directory in (".research-state-v31", ".research-state-v3", ".research-state"):
        path = project.resolve() / directory / "employee_registry.json"
        if path.exists():
            return _read(path)
    return None


def _behavior_qualified(skill: dict[str, Any]) -> bool:
    trials = skill.get("behavior_trials", [])
    if isinstance(trials, dict):
        return any(str(v).upper() in {"PASS", "PASSED", "BEHAVIOR_QUALIFIED"} for v in trials.values())
    return any(str(item).upper() in {"PASS", "PASSED", "BEHAVIOR_QUALIFIED", "FORMAL_QUALIFIED"} for item in trials)


def _permission_gaps(required: list[str], skill: dict[str, Any]) -> list[str]:
    permissions = skill.get("permissions") if isinstance(skill.get("permissions"), dict) else {}
    gaps: list[str] = []
    for permission in required:
        if permission == "network" and not bool(skill.get("network", permissions.get("network", False))):
            gaps.append(permission)
        elif permission == "credentials" and not bool(skill.get("credentials", permissions.get("credentials", False))):
            gaps.append(permission)
        elif permission == "local_write" and "project-local" not in skill.get("write_scope", []) and "project-local" not in permissions.get("writes", []):
            gaps.append(permission)
        elif permission == "execute" and not bool(permissions.get("executes_scripts", False)):
            gaps.append(permission)
    return gaps


def _formal_eligibility(skill: dict[str, Any], capability_doc: dict[str, Any], context: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    status = skill.get("runtime_status")
    if status == "PROVISIONAL":
        reasons.append("PROVISIONAL providers are advisory-only and cannot produce formal evidence")
    if status == "SPECIALIST":
        if not skill.get("exact_ref") or str(skill.get("exact_ref")).lower() in FLOATING_REFS:
            reasons.append("SPECIALIST requires an exact pinned ref")
        if not _behavior_qualified(skill):
            reasons.append("SPECIALIST lacks a passed relevant behavior trial")
        scope = skill.get("allowed_activation_scope", skill.get("activation_scope", []))
        if scope and context.get("purpose") not in scope and "formal" not in scope:
            reasons.append("activation scope does not include formal work")
    if context.get("load_bearing") and status not in {"APPROVED", "SPECIALIST"}:
        reasons.append("load-bearing work requires an APPROVED or formally qualified SPECIALIST")
    if context.get("criticality") in {"high", "critical"} and status == "SPECIALIST" and not _behavior_qualified(skill):
        reasons.append("high-criticality specialist requires behavior qualification")
    return not reasons, reasons


def _record(skill: dict[str, Any], capability_doc: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    gaps = _permission_gaps(capability_doc.get("required_permissions", []), skill)
    formal_ok, formal_reasons = _formal_eligibility(skill, capability_doc, context)
    eligible = not gaps and (formal_ok if context["purpose"] == "formal" or context["load_bearing"] else True)
    reasons = list(formal_reasons)
    if gaps:
        reasons.append("missing permissions: " + ", ".join(gaps))
    return {
        "skill_id": skill.get("skill_id"), "exact_ref": skill.get("exact_ref"),
        "runtime_status": skill.get("runtime_status"), "permission_gaps": gaps,
        "behavior_qualified": _behavior_qualified(skill), "formal_eligible": formal_ok,
        "eligible": eligible, "eligibility_reasons": reasons,
        "risk": skill.get("known_risks", []),
    }


def resolve(capability: str, *, project: Path | None = None, registry_dir: Path = REGISTRY_DIR,
            purpose: str = "advisory", load_bearing: bool = False,
            criticality: str = "low", host: str | None = None) -> dict[str, Any]:
    if purpose not in {"advisory", "exploratory", "formal"}:
        raise RouterError("purpose must be advisory, exploratory, or formal")
    if criticality not in {"low", "medium", "high", "critical"}:
        raise RouterError("criticality must be low, medium, high, or critical")
    capabilities, catalog = load_catalog(registry_dir)
    capability_doc = next((item for item in capabilities["capabilities"] if item.get("id") == capability), None)
    if capability_doc is None:
        raise RouterError(f"unknown capability: {capability}")
    context = {"purpose": purpose, "load_bearing": bool(load_bearing), "criticality": criticality}
    candidates = [item for item in catalog["skills"] if capability in item.get("capabilities", []) and item.get("runtime_status") in ACTIVE]
    records = [_record(skill, capability_doc, context) for skill in candidates]
    records.sort(key=lambda item: (
        0 if item["eligible"] else 1,
        0 if item["runtime_status"] == "APPROVED" else 1 if item["runtime_status"] == "SPECIALIST" else 2,
        COST_ORDER.get(str(next((s.get("context_cost") for s in candidates if s.get("skill_id") == item["skill_id"]), "unknown")).lower(), 3),
        item["skill_id"] or "",
    ))
    selected = [item for item in records if item["eligible"]]
    if purpose == "formal" or load_bearing:
        selected = [item for item in selected if item["runtime_status"] != "PROVISIONAL"]
    native = capability_doc.get("possible_native_tools", [])
    critical_only_provisional = bool(records) and not selected and all(item["runtime_status"] == "PROVISIONAL" for item in records)
    if selected:
        status = "PASS"
    elif native:
        status = "CONDITIONAL"
    elif critical_only_provisional or purpose == "formal" or load_bearing:
        status = "CONDITIONAL"
    else:
        status = "FAIL"
    return {
        "operation": "resolve", "status": status, "capability": capability,
        "task_context": context, "native_coverage": "AVAILABLE" if native else "NONE",
        "candidate_employees": records, "selected": selected[:1],
        "checker": capability_doc.get("checker_requirement", ""),
        "permissions_required": capability_doc.get("required_permissions", []),
        "risk": capability_doc.get("scientific_risk"), "specialist_triggers": capability_doc.get("specialist_triggers", []),
        "execution_state": "RESOLVED", "rejected": [item for item in records if not item["eligible"]],
    }


def team(task: str, capabilities: list[str], *, project: Path | None = None, registry_dir: Path = REGISTRY_DIR,
         purpose: str = "advisory", load_bearing: bool = False, criticality: str = "low") -> dict[str, Any]:
    resolved = [resolve(capability, project=project, registry_dir=registry_dir, purpose=purpose, load_bearing=load_bearing, criticality=criticality) for capability in capabilities]
    failures = [item for item in resolved if item["status"] == "FAIL"]
    selected: dict[str, dict[str, Any]] = {}
    for item in resolved:
        for employee in item["selected"]:
            selected[employee["skill_id"]] = employee
    return {"operation": "team", "status": "FAIL" if failures else ("CONDITIONAL" if any(item["status"] == "CONDITIONAL" for item in resolved) else "PASS"), "task": task, "task_context": {"purpose": purpose, "load_bearing": load_bearing, "criticality": criticality}, "required_capabilities": capabilities, "team": list(selected.values()), "resolutions": resolved, "smallest_qualified_team": len(selected), "failure_capabilities": [item["capability"] for item in failures], "execution_state": "RESOLVED"}


def inventory(*, project: Path | None = None, registry_dir: Path = REGISTRY_DIR) -> dict[str, Any]:
    capabilities, catalog = load_catalog(registry_dir)
    employee_registry = _project_registry(project)
    employees = employee_registry.get("employees", []) if employee_registry else []
    return {"operation": "inventory", "status": "PASS", "skill_version": SKILL_VERSION, "capabilities": [item["id"] for item in capabilities["capabilities"]], "skills": [{"skill_id": item.get("skill_id"), "runtime_status": item.get("runtime_status"), "capabilities": item.get("capabilities", []), "behavior_qualified": _behavior_qualified(item)} for item in catalog["skills"]], "qualified_project_employees": [item.get("id") for item in employees if item.get("status") in ACTIVE]}


def validate_plan(path: Path, *, registry_dir: Path = REGISTRY_DIR) -> dict[str, Any]:
    plan = _read(path)
    required = ("task", "capability", "employee", "exact_ref", "input_artifacts", "allowed_context", "forbidden_context", "allowed_tools", "forbidden_tools", "expected_output", "output_schema", "checker", "timeout", "cost_budget", "failure_path", "rollback")
    findings = [f"{field} is required" for field in required if plan.get(field) in (None, "", [])]
    _, catalog = load_catalog(registry_dir)
    employee = next((item for item in catalog["skills"] if item.get("skill_id") == plan.get("employee")), None)
    if employee is None:
        findings.append("employee is not in skill catalog")
    else:
        if plan.get("exact_ref") != employee.get("exact_ref"): findings.append("exact_ref does not match catalog pin")
        purpose = plan.get("purpose", "formal" if plan.get("load_bearing") else "advisory")
        if purpose == "formal" or plan.get("load_bearing"):
            record = _record(employee, next((c for c in _read(registry_dir / "capabilities.json")["capabilities"] if c.get("id") == plan.get("capability")), {}), {"purpose": purpose, "load_bearing": bool(plan.get("load_bearing")), "criticality": plan.get("criticality", "low")})
            if not record["eligible"] or employee.get("runtime_status") == "PROVISIONAL": findings.append("employee is not qualified for formal evidence in this context")
    if str(plan.get("exact_ref", "")).lower() in FLOATING_REFS: findings.append("exact_ref must not be floating")
    overlap = sorted(set(plan.get("allowed_tools", [])) & set(plan.get("forbidden_tools", [])))
    if overlap: findings.append(f"tool appears in both allowed and forbidden: {overlap}")
    if {"credentials", "tokens", "private review letters", "editor correspondence"} & set(plan.get("allowed_context", [])): findings.append("private material cannot be allowed context")
    return {"operation": "validate-plan", "status": "PASS" if not findings else "FAIL", "findings": findings, "plan": str(path), "execution_state": "DELEGATION_READY" if not findings else "REJECTED"}


def explain(capability: str, *, registry_dir: Path = REGISTRY_DIR) -> dict[str, Any]:
    result = resolve(capability, registry_dir=registry_dir)
    result["selection_policy"] = ["capability fit", "scientific task fit", "formal eligibility", "behavior qualification", "least privilege", "checker independence", "host compatibility", "context/runtime cost"]
    result["note"] = "Resolution is not execution; a host must produce a validated handoff."
    return result | {"operation": "explain"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--version", action="version", version=f"%(prog)s {SKILL_VERSION}"); parser.add_argument("--registry-dir", type=Path, default=REGISTRY_DIR)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("inventory", "resolve", "team", "validate-plan", "explain"):
        p = subs.add_parser(name)
        if name in {"inventory", "resolve", "team"}: p.add_argument("--project", type=Path)
        if name in {"resolve", "explain"}: p.add_argument("--capability", required=True)
        if name == "resolve":
            p.add_argument("--purpose", choices=["advisory", "exploratory", "formal"], default="advisory"); p.add_argument("--load-bearing", action="store_true"); p.add_argument("--criticality", choices=["low", "medium", "high", "critical"], default="low")
        if name == "team":
            p.add_argument("task"); p.add_argument("--capability", action="append", dest="capabilities", required=True); p.add_argument("--purpose", choices=["advisory", "exploratory", "formal"], default="advisory"); p.add_argument("--load-bearing", action="store_true"); p.add_argument("--criticality", choices=["low", "medium", "high", "critical"], default="low")
        if name == "validate-plan": p.add_argument("plan", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inventory": result = inventory(project=args.project, registry_dir=args.registry_dir)
        elif args.command == "resolve": result = resolve(args.capability, project=args.project, registry_dir=args.registry_dir, purpose=args.purpose, load_bearing=args.load_bearing, criticality=args.criticality)
        elif args.command == "team": result = team(args.task, args.capabilities, project=args.project, registry_dir=args.registry_dir, purpose=args.purpose, load_bearing=args.load_bearing, criticality=args.criticality)
        elif args.command == "validate-plan": result = validate_plan(args.plan, registry_dir=args.registry_dir)
        else: result = explain(args.capability, registry_dir=args.registry_dir)
    except RouterError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False)); return 2
    print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result["status"] in {"PASS", "CONDITIONAL"} else 1


if __name__ == "__main__": sys.exit(main())
