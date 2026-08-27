#!/usr/bin/env python3
"""Route CUMCM questions to defensible model families and baselines."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SKILL_VERSION = "3.1.1"
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
        return _result(task, selected, [], "explicit")

    scored = [
        (len(_hits(task, item.get("triggers", []))), item) for item in categories
    ]
    scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    top_score = scored[0][0] if scored else 0
    if top_score == 0:
        return _unresolved(task)
    tied = [item for score, item in scored if score == top_score]
    selected = tied[0]
    conflicts = [item["id"] for item in tied[1:]]
    return _result(task, selected, conflicts, "keyword")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    route_parser = sub.add_parser("route")
    route_parser.add_argument("task")
    route_parser.add_argument("--explicit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = route(args.task, args.explicit)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] in {"PASS", "CONDITIONAL"} else 1


if __name__ == "__main__":
    sys.exit(main())
