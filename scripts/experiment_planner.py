#!/usr/bin/env python3
"""Plan claim-linked experiments using information gain per cost."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

FIELDS = ("experiment_id", "claim_ids", "threat", "hypothesis_or_question", "design", "stage", "formal_status", "inputs", "expected_results", "interpretation_positive", "interpretation_negative", "interpretation_null", "cost", "priority", "stop_rule", "dependencies", "outputs", "evidence_anchors")
EXCEPTIONS = {"reproducibility", "required venue artifact", "safety", "diagnostic"}


class PlannerError(RuntimeError):
    pass


def _read(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise PlannerError(f"invalid JSON: {path}") from exc


def information_priority(option: dict[str, Any]) -> float:
    gain = float(option.get("information_gain", 0) or 0)
    cost = float(option.get("cost", 0) or 0)
    risk = float(option.get("risk", 0) or 0)
    reversibility = float(option.get("reversibility", 1) or 1)
    return round((gain * max(reversibility, 0.1) * max(1 - risk, 0.1)) / max(cost, 0.01), 6)


def plan(options_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    raw = _read(options_path)
    options = raw.get("experiments", raw) if isinstance(raw, dict) else raw
    if not isinstance(options, list):
        raise PlannerError("options must be a list or an object with experiments")
    selected: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for option in options:
        if not isinstance(option, dict):
            dropped.append({"reason": "not an object"}); continue
        threat = str(option.get("threat", "")).lower()
        if not option.get("claim_ids") and not any(token in threat for token in EXCEPTIONS):
            dropped.append({"experiment_id": option.get("experiment_id"), "reason": "no claim or permitted diagnostic purpose"}); continue
        if option.get("outcome_independent") is True and not any(token in threat for token in EXCEPTIONS):
            dropped.append({"experiment_id": option.get("experiment_id"), "reason": "outcome-independent experiment"}); continue
        item = dict(option); item["priority"] = information_priority(option); item.setdefault("stage", "PILOT"); item.setdefault("formal_status", "UNREGISTERED"); item.setdefault("evidence_anchors", [])
        selected.append(item)
    selected.sort(key=lambda item: (-item["priority"], item.get("experiment_id", "")))
    registry = {"schema_version": 3, "skill_version": "3.1.0", "experiments": selected, "decision_matrix": [{"experiment_id": item.get("experiment_id"), "decision_relevance": item.get("decision_relevance", ""), "information_gain": item.get("information_gain", 0), "cost": item.get("cost", 0), "priority": item["priority"]} for item in selected], "dropped": dropped}
    if output_path:
        output_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"operation": "plan", "status": "PASS", "selected": selected, "dropped": dropped, "registry": str(output_path) if output_path else None}


def audit(path: Path) -> dict[str, Any]:
    value = _read(path); findings: list[str] = []
    for index, item in enumerate(value.get("experiments", [])):
        if not isinstance(item, dict):
            findings.append(f"experiments[{index}] must be an object"); continue
        missing = [field for field in FIELDS if field not in item]
        if missing: findings.append(f"experiments[{index}] missing {missing}")
        if item.get("stage") not in {"DISCOVERY", "PILOT", "FORMAL", "EXPLORATORY_POST_HOC", "REPLICATION", "REPRODUCTION"}:
            findings.append(f"experiments[{index}].stage is invalid")
        if item.get("outcome_independent") and not any(token in str(item.get("threat", "")).lower() for token in EXCEPTIONS):
            findings.append(f"experiments[{index}] is outcome-independent")
    return {"operation": "audit", "status": "PASS" if not findings else "FAIL", "experiment_count": len(value.get("experiments", [])), "findings": findings}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan"); p.add_argument("options", type=Path); p.add_argument("--output", type=Path)
    p = sub.add_parser("audit"); p.add_argument("registry", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try: result = plan(args.options, args.output) if args.command == "plan" else audit(args.registry)
    except PlannerError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False)); return 2
    print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__": sys.exit(main())
