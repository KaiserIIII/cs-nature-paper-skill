#!/usr/bin/env python3
"""Render a compact human/machine-readable research dashboard."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def _state(project: Path) -> Path:
    for name in (".research-state-v31", ".research-state-v3", ".research-state"):
        candidate = project.resolve() / name
        if candidate.exists(): return candidate
    return project.resolve() / ".research-state"


def _read(path: Path, default: Any) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return default


def build(project: Path) -> dict[str, Any]:
    state = _state(project); project_doc = _read(state / "project.json", {}); contract = _read(state / "research_contract.json", {}); graph = _read(state / "research_graph.json", {"nodes": []}); registry = _read(state / "employee_registry.json", {"employees": []})
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    policy_path = state / "autonomy_policy.json"
    session_path = state / "director_session.json"
    completion_path = state / "completion_contract.json"
    audit_path = state / ".autonomy-audit.jsonl"
    policy = _read(policy_path, {})
    session = _read(session_path, {})
    completion = _read(completion_path, {})
    audit_head = "GENESIS"
    if audit_path.exists():
        lines = audit_path.read_text(encoding="utf-8").splitlines()
        if lines:
            try: audit_head = json.loads(lines[-1]).get("event_hash", "GENESIS")
            except json.JSONDecodeError: audit_head = "INVALID"
    return {"PROJECT":{"Goal": contract.get("scientific_argument", {}).get("contribution", ""), "Mode": project_doc.get("mode"), "Domain": project_doc.get("domain"), "Study type": project_doc.get("study_type"), "Ambition": project_doc.get("ambition"), "Budget": project_doc.get("budget")}, "SCIENTIFIC":{"Argument": contract.get("scientific_argument", {}).get("stakeholder_problem", ""), "Novelty": contract.get("scientific_argument", {}).get("gap", ""), "Feasibility": contract.get("feasibility", {}).get("decision"), "Protocol": contract.get("protocol", {}).get("status"), "Evidence": "see evidence_ledger.json", "Claims": "see claims.json"}, "EXECUTION":{"Completed":[node.get("id") for node in nodes if node.get("status") in {"PASS","CONDITIONAL"}], "Running":[node.get("id") for node in nodes if node.get("status") == "RUNNING"], "Blocked":[node.get("id") for node in nodes if node.get("status") == "BLOCKED"], "Next":[node.get("id") for node in nodes if node.get("status") == "READY"]}, "DEPARTMENTS":{department: "see graph" for department in ("Literature","Innovation","Implementation","Figures","Writing","Validation","Review")}, "RISKS":{"Top 3": _read(state / "risks.json", {}).get("risks", [])[:3]}, "AUTHOR ACTION": _read(state / "project.json", {}).get("author_actions", []), "qualified_employees": [item.get("id") for item in registry.get("employees", []) if item.get("status") in {"APPROVED","PROVISIONAL","SPECIALIST"}], "AUTONOMY":{"mode": policy.get("mode"), "risk_cap": policy.get("risk_cap"), "fail_closed": policy.get("fail_closed"), "session_status": session.get("status"), "session_id": session.get("session_id"), "recovery_count": session.get("recovery_count", 0), "ordinary_author_prompts": session.get("ordinary_author_prompts", 0), "audit_head": audit_head}, "COMPLETION":{"status": completion.get("status", "PENDING"), "project_disposition": completion.get("project_disposition", "IN_PROGRESS"), "critical_failures": completion.get("critical_failures", []), "residual_risks": completion.get("residual_risks", [])}}


def render_markdown(value: dict[str, Any]) -> str:
    lines = ["# Research Dashboard", ""]
    for section, values in value.items():
        lines.extend([f"## {section}", ""])
        if isinstance(values, dict):
            for key, item in values.items(): lines.append(f"- **{key}:** {json.dumps(item, ensure_ascii=False) if isinstance(item, (dict, list)) else item}")
        else: lines.append(f"{values}")
        lines.append("")
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("project", type=Path); parser.add_argument("--output", type=Path); parser.add_argument("--format", choices=("json","markdown"), default="json"); return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv); value = build(args.project); output = json.dumps(value, indent=2, ensure_ascii=False) + "\n" if args.format == "json" else render_markdown(value); (args.output or (args.project / "research-dashboard.md")).write_text(output, encoding="utf-8") if args.output else print(output, end=""); return 0


if __name__ == "__main__": sys.exit(main())
