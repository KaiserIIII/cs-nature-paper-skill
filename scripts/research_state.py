#!/usr/bin/env python3
"""Initialize and audit the private CS Nature Paper research control plane."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SKILL_VERSION = "2.1.0"
STUDY_TYPES = ("empirical", "engineering", "theory", "survey", "position", "mixed")
MODES = ("full", "plan", "execute", "write", "revision", "review", "preflight")
GATES = ("argument", "protocol", "claims", "submission")
FINAL_CLAIM_STATUSES = {"SUPPORTED", "SCOPED", "WITHDRAWN"}
EVIDENCED_CLAIM_STATUSES = {"SUPPORTED", "SCOPED"}
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "assets" / "templates"


class StateError(RuntimeError):
    """Raised for operational or malformed-state errors."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StateError(f"missing state file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise StateError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise StateError(f"expected a JSON object in {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def init_state(project_dir: Path, study_type: str, mode: str) -> dict[str, Any]:
    project_dir = project_dir.resolve()
    if not project_dir.is_dir():
        raise StateError(f"project directory does not exist: {project_dir}")

    state_dir = project_dir / ".research-state"
    if state_dir.exists():
        raise StateError(f"refusing to overwrite existing research state: {state_dir}")

    contract = _read_json(TEMPLATE_DIR / "research_contract.json")
    ledger = _read_json(TEMPLATE_DIR / "evidence_ledger.json")
    decision_template = (TEMPLATE_DIR / "decision_log.md").read_text(encoding="utf-8")

    created_utc = _utc_now()
    title = project_dir.name
    contract["created_utc"] = created_utc
    contract["skill_version"] = SKILL_VERSION
    contract["project"].update({"title": title, "study_type": study_type, "mode": mode})
    ledger["created_utc"] = created_utc
    ledger["skill_version"] = SKILL_VERSION
    decision_log = (
        decision_template.replace("{{PROJECT_TITLE}}", title)
        .replace("{{STUDY_TYPE}}", study_type)
        .replace("{{MODE}}", mode)
        .replace("{{CREATED_UTC}}", created_utc)
    )

    state_dir.mkdir()
    _write_json(state_dir / "research_contract.json", contract)
    _write_json(state_dir / "evidence_ledger.json", ledger)
    (state_dir / "decision_log.md").write_text(decision_log, encoding="utf-8")

    return {
        "operation": "init",
        "status": "PASS",
        "state_dir": str(state_dir),
        "created": ["research_contract.json", "evidence_ledger.json", "decision_log.md"],
        "private": True,
    }


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return value is not None


def _require_fields(value: dict[str, Any], fields: Iterable[str], prefix: str) -> list[str]:
    return [f"{prefix}.{field} is required" for field in fields if not _nonempty(value.get(field))]


def _argument_findings(contract: dict[str, Any], ledger: dict[str, Any]) -> list[str]:
    argument = contract.get("scientific_argument")
    if not isinstance(argument, dict):
        return ["research_contract.scientific_argument must be an object"]

    findings = _require_fields(
        argument,
        (
            "stakeholder_problem",
            "phenomenon_or_artifact",
            "prior_knowledge",
            "gap",
            "mechanism_or_model",
            "target_population_and_scope",
            "contribution",
            "downstream_boundary",
        ),
        "scientific_argument",
    )

    questions = argument.get("questions_or_goals")
    if not isinstance(questions, list) or not any(
        isinstance(item, dict) and _nonempty(item.get("id")) and _nonempty(item.get("text"))
        for item in questions
    ):
        findings.append("scientific_argument.questions_or_goals needs at least one identified question")

    study_type = contract.get("project", {}).get("study_type")
    if study_type in {"empirical", "mixed"}:
        constructs = argument.get("constructs")
        construct_fields = ("name", "conceptual_definition", "operationalization", "role", "known_gap")
        if not isinstance(constructs, list) or not any(
            isinstance(item, dict) and not _require_fields(item, construct_fields, "construct")
            for item in constructs
        ):
            findings.append(
                "scientific_argument.constructs needs a complete construct with definition, operationalization, role, and known gap"
            )

    claims = ledger.get("claims")
    if not isinstance(claims, list) or not any(
        isinstance(item, dict)
        and _nonempty(item.get("id"))
        and _nonempty(item.get("text"))
        and _nonempty(item.get("scope"))
        and _nonempty(item.get("required_evidence"))
        for item in claims
    ):
        findings.append("evidence_ledger.claims needs at least one scoped claim with required evidence")
    return findings


def _protocol_findings(contract: dict[str, Any]) -> list[str]:
    protocol = contract.get("protocol")
    if not isinstance(protocol, dict):
        return ["research_contract.protocol must be an object"]
    study_type = contract.get("project", {}).get("study_type")
    if study_type not in {"empirical", "mixed", "engineering"}:
        return []

    findings = _require_fields(
        protocol,
        (
            "units",
            "outcomes",
            "estimands",
            "denominators",
            "missingness_and_exclusions",
            "clustering_and_dependence",
            "repetition_rationale",
            "multiplicity",
            "stopping_and_failure_rules",
            "frozen_inputs",
        ),
        "protocol",
    )
    if protocol.get("status") == "draft" or not _nonempty(protocol.get("status")):
        findings.append("protocol.status must record a frozen or amended state, not draft")
    return findings


def _claim_findings(ledger: dict[str, Any]) -> list[str]:
    claims = ledger.get("claims")
    if not isinstance(claims, list) or not claims:
        return ["evidence_ledger.claims needs at least one claim"]

    findings: list[str] = []
    for index, claim in enumerate(claims, start=1):
        label = claim.get("id") if isinstance(claim, dict) else f"row-{index}"
        if not isinstance(claim, dict):
            findings.append(f"claim {label} must be an object")
            continue
        findings.extend(_require_fields(claim, ("id", "text", "type", "scope", "required_evidence", "status"), f"claim {label}"))
        status = claim.get("status")
        if status not in FINAL_CLAIM_STATUSES:
            findings.append(f"claim {label} has unresolved status {status!r}")
        elif status in EVIDENCED_CLAIM_STATUSES and not _nonempty(claim.get("observed_evidence")):
            findings.append(f"claim {label} is {status} but has no observed evidence anchor")
    return findings


def audit_state(project_dir: Path, gate: str) -> dict[str, Any]:
    state_dir = project_dir.resolve() / ".research-state"
    contract = _read_json(state_dir / "research_contract.json")
    ledger = _read_json(state_dir / "evidence_ledger.json")
    if contract.get("schema_version") != 2 or ledger.get("schema_version") != 2:
        raise StateError("unsupported research-state schema; expected schema_version 2")

    if gate == "argument":
        findings = _argument_findings(contract, ledger)
    elif gate == "protocol":
        findings = _protocol_findings(contract)
    elif gate == "claims":
        findings = _claim_findings(ledger)
    else:
        findings = (
            _argument_findings(contract, ledger)
            + _protocol_findings(contract)
            + _claim_findings(ledger)
        )
        venue = contract.get("venue")
        if not isinstance(venue, dict):
            findings.append("research_contract.venue must be an object")
        else:
            findings.extend(
                _require_fields(venue, ("rules_last_verified_utc", "primary_sources"), "venue")
            )

    return {
        "operation": "audit",
        "gate": gate,
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "state_dir": str(state_dir),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {SKILL_VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create a private .research-state directory")
    init_parser.add_argument("project_dir", type=Path)
    init_parser.add_argument("--study-type", choices=STUDY_TYPES, required=True)
    init_parser.add_argument("--mode", choices=MODES, required=True)

    audit_parser = subparsers.add_parser("audit", help="audit one research-state gate")
    audit_parser.add_argument("project_dir", type=Path)
    audit_parser.add_argument("--gate", choices=GATES, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "init":
            result = init_state(args.project_dir, args.study_type, args.mode)
        else:
            result = audit_state(args.project_dir, args.gate)
    except StateError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
