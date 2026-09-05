#!/usr/bin/env python3
"""Route CUMCM questions to defensible model families and baselines."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SKILL_VERSION = "3.2.1"
ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "assets" / "registry" / "competition_method_router.json"


def _read() -> dict[str, Any]:
    value = json.loads(ROUTER.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("competition method registry must contain an object")
    return value


def _hits(text: str, triggers: list[str]) -> list[str]:
    normalized = text.casefold()
    return [
        trigger
        for trigger in triggers
        if re.search(
            r"(?<!\w)" + re.escape(trigger.casefold()) + r"(?!\w)", normalized
        )
    ]


def _first_hit_position(text: str, triggers: list[str]) -> int:
    normalized = text.casefold()
    positions = [normalized.find(trigger.casefold()) for trigger in triggers]
    positions = [position for position in positions if position >= 0]
    return min(positions) if positions else 10**9


def _unresolved(task: str) -> dict[str, Any]:
    return {
        "operation": "competition-route",
        "status": "UNRESOLVED",
        "task": task,
        "problem_type": None,
        "candidate_models": [],
        "recommended_baseline": None,
        "recommended_primary_model": None,
        "optional_improvement": None,
        "why": "The question does not expose enough structure to select a model family.",
        "main_assumptions": [],
        "failure_risks": ["model choice would be a guess"],
        "validation_plan": [],
        "complexity_upgrade_condition": None,
        "conflicts": [],
        "candidate_families": [],
        "primary_family": None,
        "secondary_families": [],
        "dependency": [],
        "baseline_first": {"decision": "UNRESOLVED", "reason": "problem structure is unresolved"},
        "routing_stage": "CANDIDATE_FAMILY_DETECTION",
        "scientific_reasoning": {"baseline": None, "primary_model": None, "upgrade_condition": None, "validation_plan": []},
        "source": str(ROUTER),
    }


def _result(
    task: str,
    selected: dict[str, Any],
    conflicts: list[str],
    confidence: str,
) -> dict[str, Any]:
    result = {
        "operation": "competition-route",
        "status": "CONDITIONAL" if conflicts else "PASS",
        "task": task,
        "problem_type": selected["problem_type"],
        "candidate_models": list(selected["candidate_models"]),
        "recommended_baseline": selected["recommended_baseline"],
        "recommended_primary_model": selected["recommended_primary_model"],
        "optional_improvement": selected["optional_improvement"],
        "why": selected["why"],
        "main_assumptions": list(selected["main_assumptions"]),
        "failure_risks": list(selected["failure_risks"]),
        "validation_plan": list(selected["validation_plan"]),
        "complexity_upgrade_condition": selected["complexity_upgrade_condition"],
        "conflicts": conflicts,
        "confidence": confidence,
        "source": str(ROUTER),
        "routing_stage": "CANDIDATE_FAMILY_DETECTION",
        "scientific_reasoning": {
            "baseline": selected["recommended_baseline"],
            "primary_model": selected["recommended_primary_model"],
            "upgrade_condition": selected["complexity_upgrade_condition"],
            "validation_plan": list(selected["validation_plan"]),
        },
    }
    if "method_classes" in selected:
        result["method_classes"] = selected["method_classes"]
    return result


def route(task: str, explicit: str | None = None) -> dict[str, Any]:
    categories = _read()["categories"]
    if explicit:
        selected = next(
            (item for item in categories if item.get("id") == explicit), None
        )
        if selected is None:
            return {
                "operation": "competition-route",
                "status": "FAIL",
                "task": task,
                "findings": [f"unknown competition method category: {explicit}"],
                "source": str(ROUTER),
            }
        return _result(task, selected, [], "explicit") | {
            "candidate_families": [selected["id"]],
            "primary_family": selected["id"],
            "secondary_families": [],
            "dependency": [],
            "baseline_first": {
                "decision": "BASELINE_FIRST",
                "baseline": selected["recommended_baseline"],
                "upgrade_only_if": selected["complexity_upgrade_condition"],
            },
        }

    scored = [
        (len(_hits(task, item.get("triggers", []))), item) for item in categories
    ]
    scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    top_score = scored[0][0] if scored else 0
    if top_score == 0:
        return _unresolved(task)
    detected = [item for score, item in scored if score > 0]
    detected_in_task_order = sorted(
        detected,
        key=lambda item: (_first_hit_position(task, item.get("triggers", [])), item["id"]),
    )
    tied = [item for score, item in scored if score == top_score]
    selected = tied[0]
    conflicts = [item["id"] for item in tied[1:]]
    primary = detected_in_task_order[0]
    secondary = detected_in_task_order[1:]
    dependency = [
        f"{detected_in_task_order[index]['id']} -> {detected_in_task_order[index + 1]['id']}"
        for index in range(len(detected_in_task_order) - 1)
    ]
    return _result(task, selected, conflicts, "keyword") | {
        "candidate_families": [item["id"] for item in detected],
        "hybrid": len(detected) > 1,
        "primary_family": primary["id"],
        "secondary_families": [item["id"] for item in secondary],
        "dependency": dependency,
        "baseline_first": {
            "decision": "BASELINE_FIRST",
            "baseline": primary["recommended_baseline"],
            "upgrade_only_if": primary["complexity_upgrade_condition"],
        },
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    route_parser = sub.add_parser("route")
    route_parser.add_argument("task")
    route_parser.add_argument("--explicit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = route(args.task, args.explicit)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {"PASS", "CONDITIONAL"} else 1


if __name__ == "__main__":
    sys.exit(main())
