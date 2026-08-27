#!/usr/bin/env python3
"""Rank claim-linked experiments using qualitative decision relevance."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SKILL_VERSION = "3.1.1"
FIELDS = ("experiment_id", "claim_ids", "threat", "hypothesis_or_question", "design", "stage", "formal_status", "inputs", "expected_results", "interpretation_positive", "interpretation_negative", "interpretation_null", "stop_rule", "dependencies", "outputs", "evidence_anchors")
EXCEPTIONS = {"reproducibility", "required venue artifact", "safety", "diagnostic"}
BANDS = {"HIGH", "MEDIUM", "LOW"}


class PlannerError(RuntimeError):
    pass


def _read(path: Path) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc: raise PlannerError(f"invalid JSON: {path}") from exc


def _band(value: Any, default: str = "MEDIUM") -> str:
    if isinstance(value, str) and value.upper() in BANDS: return value.upper()
    if isinstance(value, (int, float)):
        return "HIGH" if value >= 2 else "MEDIUM" if value > 0 else "LOW"
    return default


def _priority(item: dict[str, Any]) -> str:
    relevance = str(item.get("decision_relevance", "")).upper()
    if relevance in BANDS: return relevance
    if item.get("claim_ids") and str(item.get("threat", "")).strip(): return "HIGH"
    return "LOW"


def information_priority(option: dict[str, Any]) -> str:
    """Return a qualitative priority; numeric optimization is opt-in only."""
    return _priority(option)


def plan(options_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    raw = _read(options_path); options = raw.get("experiments", raw) if isinstance(raw, dict) else raw
    if not isinstance(options, list): raise PlannerError("options must be a list or an object with experiments")
    selected: list[dict[str, Any]] = []; dropped: list[dict[str, Any]] = []
    for option in options:
        if not isinstance(option, dict): dropped.append({"reason": "not an object"}); continue
        threat = str(option.get("threat", "")).lower()
        exception = any(token in threat for token in EXCEPTIONS)
        if not option.get("claim_ids") and not exception:
            dropped.append({"experiment_id": option.get("experiment_id"), "reason": "no claim or permitted diagnostic purpose"}); continue
        if option.get("outcome_independent") is True and not exception:
            dropped.append({"experiment_id": option.get("experiment_id"), "reason": "outcome-independent experiment"}); continue
        item = dict(option)
        item["decision_relevance"] = _band(item.get("decision_relevance"), "HIGH" if item.get("claim_ids") else "LOW")
        item["information_gain"] = _band(item.get("information_gain"), "MEDIUM")
        item["scientific_risk"] = _band(item.get("scientific_risk", item.get("risk")), "MEDIUM")
        item["cost"] = _band(item.get("cost"), "MEDIUM")
        item["reversibility"] = _band(item.get("reversibility"), "MEDIUM")
        item["priority"] = _priority(item)
        item.setdefault("stage", "PILOT"); item.setdefault("formal_status", "UNREGISTERED"); item.setdefault("evidence_anchors", [])
        item.setdefault("why_selected", f"tests {item.get('threat', 'a declared threat')} for claim {', '.join(item.get('claim_ids', [])) or 'a permitted diagnostic'}")
        item.setdefault("why_not_selected", "")
        item.setdefault("which_claim", item.get("claim_ids", [])); item.setdefault("which_threat", item.get("threat", ""))
        item.setdefault("what_positive_changes", item.get("interpretation_positive", "")); item.setdefault("what_negative_changes", item.get("interpretation_negative", "")); item.setdefault("what_null_changes", item.get("interpretation_null", ""))
        selected.append(item)
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}; selected.sort(key=lambda item: (order[item["priority"]], order[item["information_gain"]], item.get("experiment_id", "")))
    registry = {"schema_version": 3, "skill_version": SKILL_VERSION, "experiments": selected, "decision_matrix": [{"experiment_id": item.get("experiment_id"), "decision_relevance": item["decision_relevance"], "information_gain": item["information_gain"], "scientific_risk": item["scientific_risk"], "cost": item["cost"], "reversibility": item["reversibility"], "priority": item["priority"], "why_selected": item["why_selected"], "why_not_selected": item["why_not_selected"], "which_claim": item["which_claim"], "which_threat": item["which_threat"], "what_positive_changes": item["what_positive_changes"], "what_negative_changes": item["what_negative_changes"], "what_null_changes": item["what_null_changes"]} for item in selected], "dropped": dropped, "quantitative_optimization": False}
    if output_path: output_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"operation": "plan", "status": "PASS", "selected": selected, "dropped": dropped, "registry": str(output_path) if output_path else None}


def audit(path: Path) -> dict[str, Any]:
    value = _read(path); findings: list[str] = []
    for index, item in enumerate(value.get("experiments", [])):
        if not isinstance(item, dict): findings.append(f"experiments[{index}] must be an object"); continue
        missing = [field for field in FIELDS if field not in item]
        if missing: findings.append(f"experiments[{index}] missing {missing}")
        if item.get("stage") not in {"DISCOVERY", "PILOT", "FORMAL", "EXPLORATORY_POST_HOC", "REPLICATION", "REPRODUCTION"}: findings.append(f"experiments[{index}].stage is invalid")
        if isinstance(item.get("priority"), (int, float)): findings.append(f"experiments[{index}].priority uses fake numeric precision")
        if item.get("outcome_independent") and not any(token in str(item.get("threat", "")).lower() for token in EXCEPTIONS): findings.append(f"experiments[{index}] is outcome-independent")
    return {"operation": "audit", "status": "PASS" if not findings else "FAIL", "experiment_count": len(value.get("experiments", [])), "findings": findings}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan"); p.add_argument("options", type=Path); p.add_argument("--output", type=Path)
    p = sub.add_parser("audit"); p.add_argument("registry", type=Path)
    args = parser.parse_args(); result = plan(args.options, args.output) if args.command == "plan" else audit(args.registry); print(json.dumps(result, indent=2, ensure_ascii=False)); sys.exit(0 if result["status"] == "PASS" else 1)
