#!/usr/bin/env python3
"""Initialize, migrate, and audit the private V3.1 research control plane."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SKILL_VERSION = "3.1.1"
SCHEMA_VERSION = 3
LEGACY_SCHEMA_VERSION = 2
STUDY_TYPES = (
    "empirical", "engineering", "engineering-system", "ml-benchmark", "algorithmic",
    "theory", "measurement", "observational", "causal", "human-study", "replication",
    "reproduction", "survey", "systematic-review", "benchmark-dataset", "tool-demo",
    "position", "mixed",
)
MODES = ("full", "guided", "copilot", "autopilot", "plan", "execute", "write", "revision", "review", "preflight")
GATES = ("argument", "feasibility", "protocol", "claims", "submission")
FINAL_CLAIM_STATUSES = {"SUPPORTED", "SCOPED", "WITHDRAWN"}
EVIDENCED_CLAIM_STATUSES = {"SUPPORTED", "SCOPED"}
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "assets" / "templates" / "v3"
LEGACY_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "assets" / "legacy" / "v2"
V3_TEMPLATES = (
    "project.json", "research_contract.json", "research_graph.json", "claims.json",
    "evidence_ledger.json", "literature_registry.json", "experiment_registry.json",
    "artifact_manifest.json", "amendments.json", "risks.json", "venue_profile.json",
    "employee_registry.json", "delegation_plan.json", "handoff.json", "query_log.json",
    "review_finding.json",
)

class StateError(RuntimeError):
    """Raised for operational or malformed-state errors."""

def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _read_json(path: Path) -> dict[str, Any]:
    try: value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc: raise StateError(f"missing state file: {path}") from exc
    except json.JSONDecodeError as exc: raise StateError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict): raise StateError(f"expected a JSON object in {path}")
    return value

def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def _nonempty(value: Any) -> bool:
    if isinstance(value, str): return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)): return bool(value)
    return value is not None

def _require_fields(value: dict[str, Any], fields: Iterable[str], prefix: str) -> list[str]:
    return [f"{prefix}.{field} is required" for field in fields if not _nonempty(value.get(field))]

def _state_dir(project_dir: Path) -> Path:
    v31 = project_dir.resolve() / ".research-state-v31"
    if v31.exists():
        return v31
    v3 = project_dir.resolve() / ".research-state-v3"
    return v3 if v3.exists() else project_dir.resolve() / ".research-state"

def init_state(project_dir: Path, study_type: str, mode: str, domain: str = "") -> dict[str, Any]:
    project_dir = project_dir.resolve()
    if not project_dir.is_dir(): raise StateError(f"project directory does not exist: {project_dir}")
    state_dir = project_dir / ".research-state"
    if state_dir.exists(): raise StateError(f"refusing to overwrite existing research state: {state_dir}")
    created_utc, title = _utc_now(), project_dir.name
    state_dir.mkdir(); created: list[str] = []
    for template_name in V3_TEMPLATES:
        value = _read_json(TEMPLATE_DIR / template_name)
        value["skill_version"], value["created_utc"] = SKILL_VERSION, created_utc
        if "schema_version" in value: value["schema_version"] = SCHEMA_VERSION
        if template_name == "project.json":
            value.update({"project_dir": str(project_dir), "title": title, "domain": domain, "study_type": study_type, "mode": mode, "automation_mode": mode, "budget": {"tokens": None, "minutes": None, "network": False, "compute": None, "money": 0}, "permissions": {"private_paths": [str(project_dir)], "external_writes": [], "publish": False, "submit": False}})
        elif template_name == "research_contract.json": value["project"].update({"title": title, "study_type": study_type, "mode": mode, "domain": domain})
        _write_json(state_dir / template_name, value); created.append(template_name)
    decision_template_path = TEMPLATE_DIR / "decision_log.md"
    if not decision_template_path.exists():
        decision_template_path = Path(__file__).resolve().parents[1] / "assets" / "templates" / "decision_log.md"
    decision_template = decision_template_path.read_text(encoding="utf-8")
    decision_log = decision_template.replace("{{PROJECT_TITLE}}", title).replace("{{STUDY_TYPE}}", study_type).replace("{{MODE}}", mode).replace("{{CREATED_UTC}}", created_utc)
    (state_dir / "decision_log.md").write_text(decision_log, encoding="utf-8"); created.append("decision_log.md")
    graph_path = state_dir / "research_graph.json"
    if graph_path.exists():
        shutil.copy2(graph_path, state_dir / ".research-graph-initial.json")
        created.append(".research-graph-initial.json")
    return {"operation": "init", "status": "PASS", "state_dir": str(state_dir), "created": created, "private": True}

def _claim_records(ledger: dict[str, Any], claims_doc: dict[str, Any] | None = None) -> Any:
    canonical = claims_doc.get("claims") if isinstance(claims_doc, dict) else None
    if isinstance(canonical, list) and any(isinstance(x, dict) and _nonempty(x.get("text")) for x in canonical):
        return canonical
    # V2 compatibility: old ledgers keep claim records in-place.
    return ledger.get("claims")

def _argument_findings(contract: dict[str, Any], ledger: dict[str, Any], claims_doc: dict[str, Any] | None = None) -> list[str]:
    argument = contract.get("scientific_argument")
    if not isinstance(argument, dict): return ["research_contract.scientific_argument must be an object"]
    findings = _require_fields(argument, ("stakeholder_problem", "phenomenon_or_artifact", "prior_knowledge", "gap", "mechanism_or_model", "target_population_and_scope", "contribution", "downstream_boundary"), "scientific_argument")
    questions = argument.get("questions_or_goals")
    if not isinstance(questions, list) or not any(isinstance(x, dict) and _nonempty(x.get("id")) and _nonempty(x.get("text")) for x in questions): findings.append("scientific_argument.questions_or_goals needs at least one identified question")
    study_type = contract.get("project", {}).get("study_type")
    if study_type in {"empirical", "mixed", "measurement", "observational", "causal", "human-study", "ml-benchmark"}:
        constructs = argument.get("constructs"); fields = ("name", "conceptual_definition", "operationalization", "role", "known_gap")
        if not isinstance(constructs, list) or not any(isinstance(x, dict) and not _require_fields(x, fields, "construct") for x in constructs): findings.append("scientific_argument.constructs needs a complete operationalized construct")
    claims = _claim_records(ledger, claims_doc)
    if not isinstance(claims, list) or not any(isinstance(x, dict) and _nonempty(x.get("id")) and _nonempty(x.get("text")) and _nonempty(x.get("scope")) and _nonempty(x.get("required_evidence")) for x in claims): findings.append("evidence ledger needs at least one scoped claim with required evidence")
    return findings

def _protocol_findings(contract: dict[str, Any]) -> list[str]:
    protocol = contract.get("protocol")
    if not isinstance(protocol, dict): return ["research_contract.protocol must be an object"]
    if contract.get("project", {}).get("study_type") not in {"empirical", "mixed", "engineering", "engineering-system", "ml-benchmark", "measurement", "observational", "causal", "human-study", "replication", "reproduction"}: return []
    findings = _require_fields(protocol, ("units", "outcomes", "estimands", "denominators", "missingness_and_exclusions", "clustering_and_dependence", "repetition_rationale", "multiplicity", "stopping_and_failure_rules", "frozen_inputs"), "protocol")
    if protocol.get("status") in {None, "draft"}: findings.append("protocol.status must record a frozen or amended state, not draft")
    return findings

def _feasibility_findings(contract: dict[str, Any]) -> list[str]:
    feasibility = contract.get("feasibility")
    if not isinstance(feasibility, dict): return ["research_contract.feasibility must be an object"]
    findings = _require_fields(feasibility, ("decision", "resource_inventory", "cost", "risks", "lower_resource_option"), "feasibility")
    if feasibility.get("decision") not in {"GO", "GO_WITH_SCOPE_REDUCTION", "PILOT_FIRST", "HIGH_RISK", "NO_GO"}: findings.append("feasibility.decision must be a bounded decision")
    return findings

def _claim_findings(ledger: dict[str, Any], claims_doc: dict[str, Any] | None = None) -> list[str]:
    claims = _claim_records(ledger, claims_doc)
    if not isinstance(claims, list) or not claims: return ["evidence ledger claims needs at least one claim"]
    findings: list[str] = []
    for index, claim in enumerate(claims, start=1):
        label = claim.get("id") if isinstance(claim, dict) else f"row-{index}"
        if not isinstance(claim, dict): findings.append(f"claim {label} must be an object"); continue
        findings.extend(_require_fields(claim, ("id", "text", "type", "scope", "required_evidence", "status"), f"claim {label}"))
        status = claim.get("status")
        if status not in FINAL_CLAIM_STATUSES: findings.append(f"claim {label} has unresolved status {status!r}")
        elif status in EVIDENCED_CLAIM_STATUSES and not _nonempty(claim.get("observed_evidence")): findings.append(f"claim {label} is {status} but has no observed evidence anchor")
    return findings

def audit_state(project_dir: Path, gate: str) -> dict[str, Any]:
    state_dir = _state_dir(project_dir); contract = _read_json(state_dir / "research_contract.json"); ledger = _read_json(state_dir / "evidence_ledger.json")
    claims_doc = _read_json(state_dir / "claims.json") if (state_dir / "claims.json").exists() else None
    if not {contract.get("schema_version"), ledger.get("schema_version")} <= {LEGACY_SCHEMA_VERSION, SCHEMA_VERSION}: raise StateError("unsupported research-state schema; expected schema_version 2 or 3")
    if gate == "argument": findings = _argument_findings(contract, ledger, claims_doc)
    elif gate == "feasibility": findings = _feasibility_findings(contract)
    elif gate == "protocol": findings = _protocol_findings(contract)
    elif gate == "claims": findings = _claim_findings(ledger, claims_doc)
    else:
        findings = _argument_findings(contract, ledger, claims_doc) + _protocol_findings(contract) + _claim_findings(ledger, claims_doc); venue = contract.get("venue")
        if not isinstance(venue, dict): findings.append("research_contract.venue must be an object")
        else: findings.extend(_require_fields(venue, ("rules_last_verified_utc", "primary_sources"), "venue"))
    return {"operation": "audit", "gate": gate, "status": "PASS" if not findings else "FAIL", "findings": findings, "state_dir": str(state_dir)}

def migrate_v2(project_dir: Path) -> dict[str, Any]:
    project_dir = project_dir.resolve(); source, target = project_dir / ".research-state", project_dir / ".research-state-v3"
    if not source.is_dir(): raise StateError(f"V2 research state not found: {source}")
    if target.exists(): raise StateError(f"refusing to overwrite existing V3 state: {target}")
    shutil.copytree(source, target); now = _utc_now()
    for name in ("research_contract.json", "evidence_ledger.json"):
        value = _read_json(target / name); value.update({"schema_version": SCHEMA_VERSION, "skill_version": SKILL_VERSION, "migrated_from": "v2", "migrated_utc": now}); _write_json(target / name, value)
    contract = _read_json(target / "research_contract.json")
    contract.setdefault("feasibility", {"decision": "PILOT_FIRST", "resource_inventory": "not recorded in V2; author review required", "cost": "not recorded in V2", "risks": ["V2 state has no feasibility gate"], "lower_resource_option": "author must define before formal execution"})
    _write_json(target / "research_contract.json", contract)
    existing = {p.name for p in target.iterdir()}
    for template_name in V3_TEMPLATES:
        if template_name in existing or template_name in {"research_contract.json", "evidence_ledger.json"}: continue
        value = _read_json(TEMPLATE_DIR / template_name); value.update({"skill_version": SKILL_VERSION, "schema_version": SCHEMA_VERSION, "created_utc": now}); _write_json(target / template_name, value)
    legacy_ledger = _read_json(source / "evidence_ledger.json")
    if isinstance(legacy_ledger.get("claims"), list):
        _write_json(target / "claims.json", {"schema_version": 1, "skill_version": SKILL_VERSION, "created_utc": now, "migrated_from": "v2", "claims": legacy_ledger["claims"]})
    return {"operation": "migrate-v2", "status": "PASS", "source": str(source), "state_dir": str(target), "preserved": True}

def migrate_v3(project_dir: Path) -> dict[str, Any]:
    """Copy V3 state to a V3.1 directory without rewriting the source."""
    project_dir = project_dir.resolve()
    source = project_dir / ".research-state-v3"
    if not source.is_dir():
        source = project_dir / ".research-state"
    target = project_dir / ".research-state-v31"
    if not source.is_dir():
        raise StateError(f"V3 research state not found: {source}")
    if target.exists():
        raise StateError(f"refusing to overwrite existing V3.1 state: {target}")
    shutil.copytree(source, target)
    now = _utc_now()
    for path in target.glob("*.json"):
        value = _read_json(path)
        value.update({"skill_version": SKILL_VERSION, "migrated_from": "v3", "migrated_utc": now})
        _write_json(path, value)
    provenance = {"source": str(source), "target": str(target), "preserved": True, "migrated_utc": now, "tool": SKILL_VERSION}
    _write_json(target / "migration_provenance.json", provenance)
    return {"operation": "migrate-v3", "status": "PASS", "source": str(source), "state_dir": str(target), "preserved": True, "provenance": str(target / "migration_provenance.json")}

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--version", action="version", version=f"%(prog)s {SKILL_VERSION}"); subs = parser.add_subparsers(dest="command", required=True)
    init = subs.add_parser("init", help="create a private V3 research-state directory"); init.add_argument("project_dir", type=Path); init.add_argument("--study-type", choices=STUDY_TYPES, required=True); init.add_argument("--mode", choices=MODES, required=True); init.add_argument("--domain", default="")
    audit = subs.add_parser("audit", help="audit one research-state gate"); audit.add_argument("project_dir", type=Path); audit.add_argument("--gate", choices=GATES, required=True)
    migrate = subs.add_parser("migrate-v2", help="copy V2 state without overwriting it"); migrate.add_argument("project_dir", type=Path)
    migrate3 = subs.add_parser("migrate-v3", help="copy V3 state to V3.1 without overwriting it"); migrate3.add_argument("project_dir", type=Path)
    return parser

def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "init": result = init_state(args.project_dir, args.study_type, args.mode, args.domain)
        elif args.command == "migrate-v2": result = migrate_v2(args.project_dir)
        elif args.command == "migrate-v3": result = migrate_v3(args.project_dir)
        else: result = audit_state(args.project_dir, args.gate)
    except StateError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False)); return 2
    print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result["status"] in {"PASS", "CONDITIONAL"} else 1

if __name__ == "__main__": sys.exit(main())
