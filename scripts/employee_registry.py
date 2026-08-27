#!/usr/bin/env python3
"""Audit skill employees and check department capability coverage."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


SKILL_VERSION = "3.0.0"
SCHEMA_VERSION = 3
SUPPORTED_SCHEMA_VERSIONS = {1, 3}
STATUSES = {
    "APPROVED",
    "PROVISIONAL",
    "SPECIALIST",
    "QUARANTINED",
    "REJECTED",
    "UNASSESSED",
}
ACTIVE_STATUSES = {"APPROVED", "PROVISIONAL", "SPECIALIST"}
FLOATING_REFS = {"", "head", "latest", "main", "master", "trunk"}
UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class RegistryError(RuntimeError):
    """Raised for malformed registry files or invalid command input."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistryError(f"registry not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RegistryError("registry root must be a JSON object")
    return value


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return value is not None


def _is_string_list(value: Any, *, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def _https_source(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _exact_ref(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() not in FLOATING_REFS


def _security_states(value: Any) -> set[str]:
    states: set[str] = set()
    if not isinstance(value, list):
        return states
    for item in value:
        if isinstance(item, str):
            states.update(token for token in re.findall(r"\b(?:PASS|WARN|FAIL)\b", item.upper()))
        elif isinstance(item, dict) and isinstance(item.get("status"), str):
            states.add(item["status"].upper())
    return states


def _require(employee: dict[str, Any], fields: Iterable[str], label: str) -> list[str]:
    return [f"{label}.{field} is required" for field in fields if not _nonempty(employee.get(field))]


def _audit_contract(contract: Any, index: int) -> list[str]:
    label = f"department_contracts[{index}]"
    if not isinstance(contract, dict):
        return [f"{label} must be an object"]
    findings = _require(contract, ("department", "required_capabilities", "required_roles"), label)
    if _nonempty(contract.get("required_capabilities")) and not _is_string_list(
        contract.get("required_capabilities")
    ):
        findings.append(f"{label}.required_capabilities must be a non-empty string list")
    if _nonempty(contract.get("required_roles")) and not _is_string_list(contract.get("required_roles")):
        findings.append(f"{label}.required_roles must be a non-empty string list")
    if not isinstance(contract.get("producer_checker_separation"), bool):
        findings.append(f"{label}.producer_checker_separation must be boolean")
    return findings


def _audit_employee(employee: Any, index: int) -> tuple[list[str], list[str]]:
    label = f"employees[{index}]"
    if not isinstance(employee, dict):
        return [f"{label} must be an object"], []

    findings = _require(employee, ("id", "source", "status", "departments", "capabilities"), label)
    warnings: list[str] = []
    status = employee.get("status")
    if status not in STATUSES:
        findings.append(f"{label}.status must be one of {sorted(STATUSES)}")
        return findings, warnings

    for field in ("departments", "capabilities"):
        if _nonempty(employee.get(field)) and not _is_string_list(employee.get(field)):
            findings.append(f"{label}.{field} must be a non-empty string list")

    if status == "UNASSESSED":
        warnings.append(f"{label} is UNASSESSED and cannot staff a department")
        return findings, warnings

    if status in {"QUARANTINED", "REJECTED"}:
        if not _is_string_list(employee.get("known_risks")):
            findings.append(f"{label}.known_risks must explain why status is {status}")
        return findings, warnings

    findings.extend(
        _require(
            employee,
            (
                "ref",
                "license",
                "roles",
                "trigger_scope",
                "do_not_use_for",
                "permissions",
                "environment_contract",
                "quality_evidence",
                "approved_uses",
                "rollback",
                "last_reviewed_utc",
            ),
            label,
        )
    )
    if not _https_source(employee.get("source")):
        findings.append(f"{label}.source must be an HTTPS URL")
    if not _exact_ref(employee.get("ref")):
        findings.append(f"{label}.ref must pin a release or commit, not a floating branch")
    if not _is_string_list(employee.get("roles")):
        findings.append(f"{label}.roles must be a non-empty string list")
    if not _is_string_list(employee.get("approved_uses")):
        findings.append(f"{label}.approved_uses must be a non-empty string list")
    if not UTC_PATTERN.match(str(employee.get("last_reviewed_utc", ""))):
        findings.append(f"{label}.last_reviewed_utc must use YYYY-MM-DDTHH:MM:SSZ")

    permissions = employee.get("permissions")
    if isinstance(permissions, dict):
        for key in ("network", "credentials", "writes", "executes_scripts"):
            if key not in permissions:
                findings.append(f"{label}.permissions.{key} is required")
        for key in ("network", "executes_scripts"):
            if key in permissions and not isinstance(permissions[key], bool):
                findings.append(f"{label}.permissions.{key} must be boolean")
        for key in ("credentials", "writes"):
            if key in permissions and not _is_string_list(permissions[key], allow_empty=True):
                findings.append(f"{label}.permissions.{key} must be a string list")
    elif _nonempty(permissions):
        findings.append(f"{label}.permissions must be an object")

    evidence = employee.get("quality_evidence")
    if isinstance(evidence, dict):
        for key in ("source_reviewed", "license_reviewed", "scripts_reviewed"):
            if not isinstance(evidence.get(key), bool):
                findings.append(f"{label}.quality_evidence.{key} must be boolean")
        tests = evidence.get("tests")
        if not isinstance(tests, dict):
            findings.append(f"{label}.quality_evidence.tests must be an object")
        else:
            for key in ("unit", "workflow", "external"):
                if not _is_string_list(tests.get(key), allow_empty=True):
                    findings.append(f"{label}.quality_evidence.tests.{key} must be a string list")
        audits = evidence.get("security_audits")
        if not isinstance(audits, list):
            findings.append(f"{label}.quality_evidence.security_audits must be a list")
    elif _nonempty(evidence):
        findings.append(f"{label}.quality_evidence must be an object")

    if status in {"PROVISIONAL", "SPECIALIST"} and not _is_string_list(employee.get("known_risks")):
        findings.append(f"{label}.known_risks is required for {status}")

    if isinstance(evidence, dict):
        reviewed = all(evidence.get(key) is True for key in ("source_reviewed", "license_reviewed", "scripts_reviewed"))
        security_states = _security_states(evidence.get("security_audits"))
        tests = evidence.get("tests") if isinstance(evidence.get("tests"), dict) else {}
        behavioral_tests = list(tests.get("unit", [])) + list(tests.get("workflow", []))
        if status == "APPROVED":
            if not reviewed:
                findings.append(f"{label} cannot be APPROVED before source, license, and scripts are reviewed")
            if not behavioral_tests:
                findings.append(f"{label} cannot be APPROVED without unit or workflow test evidence")
            if not security_states or security_states - {"PASS"}:
                findings.append(f"{label} cannot be APPROVED without all-PASS security audit evidence")
        elif status in {"PROVISIONAL", "SPECIALIST"}:
            if not reviewed:
                findings.append(f"{label} cannot be {status} before source, license, and scripts are reviewed")
            if "FAIL" in security_states:
                findings.append(f"{label} cannot be active while a security audit is FAIL")
            if not behavioral_tests:
                warnings.append(f"{label} has no local unit or workflow trial and remains conditional")

    return findings, warnings


def audit_registry(registry: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    warnings: list[str] = []
    if registry.get("schema_version") not in SUPPORTED_SCHEMA_VERSIONS:
        findings.append(f"schema_version must be one of {sorted(SUPPORTED_SCHEMA_VERSIONS)}")
    if not isinstance(registry.get("employees"), list):
        findings.append("employees must be a list")
    if not isinstance(registry.get("department_contracts"), list):
        findings.append("department_contracts must be a list")

    employees = registry.get("employees") if isinstance(registry.get("employees"), list) else []
    contracts = (
        registry.get("department_contracts")
        if isinstance(registry.get("department_contracts"), list)
        else []
    )
    ids: list[str] = []
    for index, employee in enumerate(employees):
        employee_findings, employee_warnings = _audit_employee(employee, index)
        findings.extend(employee_findings)
        warnings.extend(employee_warnings)
        if isinstance(employee, dict) and isinstance(employee.get("id"), str):
            ids.append(employee["id"])
    duplicates = sorted({employee_id for employee_id in ids if ids.count(employee_id) > 1})
    if duplicates:
        findings.append(f"employee ids must be unique; duplicates: {duplicates}")

    departments: list[str] = []
    for index, contract in enumerate(contracts):
        findings.extend(_audit_contract(contract, index))
        if isinstance(contract, dict) and isinstance(contract.get("department"), str):
            departments.append(contract["department"])
    duplicate_departments = sorted(
        {department for department in departments if departments.count(department) > 1}
    )
    if duplicate_departments:
        findings.append(f"department contracts must be unique; duplicates: {duplicate_departments}")

    status = "FAIL" if findings else ("CONDITIONAL" if warnings else "PASS")
    return {
        "operation": "audit",
        "status": status,
        "findings": findings,
        "warnings": warnings,
        "employee_count": len(employees),
        "contract_count": len(contracts),
    }


def check_team(registry: dict[str, Any], departments: list[str] | None = None) -> dict[str, Any]:
    audit = audit_registry(registry)
    if audit["status"] == "FAIL":
        return {
            "operation": "team",
            "status": "FAIL",
            "findings": ["registry audit failed before team coverage check"] + audit["findings"],
            "warnings": audit["warnings"],
            "departments": [],
        }

    requested = set(departments or [])
    contracts = registry["department_contracts"]
    if requested:
        known = {contract["department"] for contract in contracts}
        unknown = sorted(requested - known)
        if unknown:
            raise RegistryError(f"unknown departments: {unknown}")
        contracts = [contract for contract in contracts if contract["department"] in requested]

    employees = [employee for employee in registry["employees"] if employee["status"] in ACTIVE_STATUSES]
    department_results: list[dict[str, Any]] = []
    overall = "PASS"
    for contract in contracts:
        department = contract["department"]
        eligible = [employee for employee in employees if department in employee["departments"]]
        capability_staff: dict[str, list[str]] = {}
        role_staff: dict[str, list[str]] = {}
        for capability in contract["required_capabilities"]:
            capability_staff[capability] = [
                employee["id"] for employee in eligible if capability in employee["capabilities"]
            ]
        for role in contract["required_roles"]:
            role_staff[role] = [employee["id"] for employee in eligible if role in employee["roles"]]

        missing_capabilities = sorted(
            capability for capability, staff in capability_staff.items() if not staff
        )
        missing_roles = sorted(role for role, staff in role_staff.items() if not staff)
        separation_ok = True
        if contract["producer_checker_separation"]:
            producers = set(role_staff.get("producer", []))
            checkers = set(role_staff.get("checker", []))
            separation_ok = bool(producers and checkers and any(p != c for p in producers for c in checkers))

        used_ids = {
            employee_id
            for staff in list(capability_staff.values()) + list(role_staff.values())
            for employee_id in staff
        }
        used = [employee for employee in eligible if employee["id"] in used_ids]
        conditional_ids = sorted(
            employee["id"] for employee in used if employee["status"] != "APPROVED"
        )
        if missing_capabilities or missing_roles or not separation_ok:
            status = "FAIL"
        elif conditional_ids:
            status = "CONDITIONAL"
        else:
            status = "PASS"
        if status == "FAIL":
            overall = "FAIL"
        elif status == "CONDITIONAL" and overall == "PASS":
            overall = "CONDITIONAL"

        department_results.append(
            {
                "department": department,
                "status": status,
                "capability_staff": capability_staff,
                "role_staff": role_staff,
                "missing_capabilities": missing_capabilities,
                "missing_roles": missing_roles,
                "producer_checker_separation": separation_ok,
                "conditional_employees": conditional_ids,
            }
        )

    return {
        "operation": "team",
        "status": overall,
        "findings": [],
        "warnings": audit["warnings"],
        "departments": department_results,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {SKILL_VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="audit employee records and contracts")
    audit_parser.add_argument("registry", type=Path)

    team_parser = subparsers.add_parser("team", help="check capability and role coverage")
    team_parser.add_argument("registry", type=Path)
    team_parser.add_argument(
        "--department",
        action="append",
        dest="departments",
        help="department to check; repeat to select several (default: all)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        registry = _read_json(args.registry)
        if args.command == "audit":
            result = audit_registry(registry)
        else:
            result = check_team(registry, args.departments)
    except RegistryError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
