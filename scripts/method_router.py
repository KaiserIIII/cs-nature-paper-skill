#!/usr/bin/env python3
"""Recommend a methods playbook without pretending keywords prove validity."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SKILL_VERSION = "3.1.1"
ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "assets" / "registry" / "method_router.json"
HIGH_RISK = {"causal", "human-subjects", "security-measurement", "survey", "systematic-review"}


def _read() -> dict[str, Any]:
    return json.loads(ROUTER.read_text(encoding="utf-8"))


def _hits(text: str, triggers: list[str]) -> list[str]:
    normalized = text.casefold()
    return [trigger for trigger in triggers if re.search(r"(?<!\w)" + re.escape(trigger.casefold()) + r"(?!\w)", normalized)]


def route(task: str, explicit: str | None = None, *, project: Path | None = None) -> dict[str, Any]:
    methods = _read()["methods"]
    if explicit:
        selected = next((item for item in methods if item["id"] == explicit), None)
        if selected is None:
            return {"operation": "route", "status": "FAIL", "findings": [f"unknown method: {explicit}"]}
        scored = [(len(_hits(task, selected.get("triggers", []))), selected)]
        confidence = "explicit"
    else:
        scored = [(len(_hits(task, item.get("triggers", []))), item) for item in methods]
        scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
        top_score = scored[0][0] if scored else 0
        if top_score == 0:
            clarification = ["state the unit of analysis", "state the intended outcome or estimand", "identify whether assignment/intervention is present"]
            return {"operation": "route", "status": "CONDITIONAL", "task": task, "method": None, "confidence": "unresolved", "reason": "insufficient task signal", "required_clarification_or_diagnosis": clarification, "candidate_methods": [], "conflicts": [], "specialist_required": False, "source": str(ROUTER)}
        selected = scored[0][1]
        confidence = "keyword"
    top_score = scored[0][0]
    tied = [item for score, item in scored if score == top_score and score > 0]
    conflicts = [item["id"] for item in tied[1:]]
    candidates = [item["id"] for score, item in scored if score > 0]
    risk = "HIGH" if selected["id"] in HIGH_RISK or any(item in HIGH_RISK for item in candidates) else "MEDIUM" if len(candidates) > 1 else "LOW"
    ambiguous = len(tied) > 1
    specialist_required = selected["id"] in HIGH_RISK or ambiguous
    result = {"operation": "route", "status": "CONDITIONAL" if ambiguous or selected["id"] in HIGH_RISK else "PASS", "task": task, "method": selected["id"], "confidence": confidence, "candidate_methods": candidates, "conflicts": conflicts, "risk": risk, "recommended_primary_design": selected["id"], "secondary_modules": [item for item in candidates if item != selected["id"]], "specialist_required": specialist_required, "required_definitions": selected["required_definitions"], "estimands": selected["common_estimands"], "evidence_requirements": selected["evidence_requirements"], "minimum_checks": selected["minimum_checks"], "specialist_escalation": selected["specialist_escalation"], "forbidden_claims": selected["forbidden_claims"], "source": str(ROUTER), "method_selection_boundary": ["unit", "estimand", "sampling", "assignment_or_identification", "dependence", "measurement", "missingness", "scope"]}
    if project:
        result["diagnostic_project"] = str(project)
        result["note"] = "A host must inspect project claims/design before finalizing a high-risk method."
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("route"); p.add_argument("task"); p.add_argument("--method"); p.add_argument("--project", type=Path)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args(); result = route(args.task, args.method, project=args.project); print(json.dumps(result, indent=2, ensure_ascii=False)); sys.exit(0 if result["status"] in {"PASS", "CONDITIONAL"} else 1)
