#!/usr/bin/env python3
"""Assess publication ambition without collapsing readiness into one score."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

LEVELS = {"A": "Coursework", "B": "Workshop", "C": "Standard peer-reviewed venue", "D": "Top field venue", "E": "Broad high-impact / Nature-family ambition"}
DIMENSIONS = ("importance", "novelty_depth", "mechanistic_insight", "technical_depth", "generality", "evidence_diversity", "robustness", "reproducibility", "external_relevance", "audience_breadth")


def assess(level: str, evidence: dict[str, Any]) -> dict[str, Any]:
    if level not in LEVELS: return {"operation": "assess", "status": "FAIL", "findings": [f"unknown ambition level: {level}"]}
    dimensions: dict[str, dict[str, Any]] = {}
    for dimension in DIMENSIONS:
        item = evidence.get(dimension, {})
        if isinstance(item, str): item = {"status": item, "reason": "author-provided status"}
        status = item.get("status", "MISSING") if isinstance(item, dict) else "MISSING"
        dimensions[dimension] = {"status": status, "reason": item.get("reason", "") if isinstance(item, dict) else ""}
    if any(item["status"] in {"MISSING", "FAIL", "NOT_YET_DEFENSIBLE"} for item in dimensions.values()): readiness = "NOT_YET_DEFENSIBLE"
    elif any(item["status"] in {"GAP", "CONDITIONAL", "PLAUSIBLE_WITH_GAPS"} for item in dimensions.values()): readiness = "PLAUSIBLE_WITH_GAPS"
    else: readiness = "READY"
    return {"operation": "assess", "status": "PASS", "ambition_level": level, "ambition_label": LEVELS[level], "readiness": readiness, "dimensions": dimensions, "decision": "ambition is a diagnosis of missing scientific contribution, not an acceptance probability"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("level", choices=sorted(LEVELS)); parser.add_argument("evidence_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv); evidence = json.loads(open(args.evidence_json, encoding="utf-8").read()); result = assess(args.level, evidence); print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__": sys.exit(main())
