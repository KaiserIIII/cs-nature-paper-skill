#!/usr/bin/env python3
"""Validate CUMCM review findings and a bounded contest score radar."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SEVERITIES = {"CRITICAL", "MAJOR", "MINOR"}
SEVERITY_ORDER = {"CRITICAL": 0, "MAJOR": 1, "MINOR": 2}
FINDING_FIELDS = (
    "issue",
    "severity",
    "location",
    "why_it_matters",
    "smallest_sufficient_fix",
    "estimated_scoring_impact",
    "evidence_anchors",
)
RADAR_FIELDS = (
    "problem_understanding",
    "model_appropriateness",
    "mathematical_rigor",
    "implementation",
    "validation",
    "innovation",
    "visualization",
    "writing",
    "reproducibility",
    "overall_coherence",
)
SUMMARY_FIELDS = (
    "current_strongest_point",
    "current_weakest_point",
    "largest_award_level_blocker",
    "highest_roi_remaining_improvement",
)
FORBIDDEN_AWARD_PATTERNS = (
    "award probability",
    "probability of winning",
    "chance of first prize",
    "guaranteed prize",
    "guaranteed first prize",
    "获奖概率",
    "稳拿",
    "保送一等奖",
)


def _load(value_or_path: dict[str, Any] | Path) -> dict[str, Any]:
    if isinstance(value_or_path, Path):
        value = json.loads(value_or_path.read_text(encoding="utf-8"))
    else:
        value = value_or_path
    if not isinstance(value, dict):
        raise ValueError("competition review must be an object")
    return value


def validate_finding(value: Any) -> dict[str, Any]:
    problems: list[str] = []
    if not isinstance(value, dict):
        return {"status": "FAIL", "findings": ["finding must be an object"]}
    for field in FINDING_FIELDS:
        if field not in value:
            problems.append(f"{field} is required")
    if value.get("severity") not in SEVERITIES:
        problems.append("severity must be CRITICAL, MAJOR, or MINOR")
    for field in FINDING_FIELDS:
        if field in {"evidence_anchors", "severity"}:
            continue
        if field in value and not str(value[field]).strip():
            problems.append(f"{field} must be non-empty")
    anchors = value.get("evidence_anchors")
    if "evidence_anchors" in value and (
        not isinstance(anchors, list) or not anchors
    ):
        problems.append("evidence_anchors must be a non-empty list")
    return {"status": "PASS" if not problems else "FAIL", "findings": problems}


def audit(value_or_path: dict[str, Any] | Path) -> dict[str, Any]:
    value = _load(value_or_path)
    problems: list[str] = []
    source_findings = value.get("findings")
    if not isinstance(source_findings, list):
        problems.append("findings must be a list")
        source_findings = []
    for index, finding in enumerate(source_findings):
        check = validate_finding(finding)
        problems.extend(
            f"findings[{index}].{message}" for message in check["findings"]
        )

    radar = value.get("score_radar")
    if not isinstance(radar, dict):
        problems.append("score_radar must be an object")
        radar = {}
    missing_radar = [field for field in RADAR_FIELDS if field not in radar]
    if missing_radar:
        problems.append(f"score_radar missing {missing_radar}")
    extra_radar = sorted(set(radar) - set(RADAR_FIELDS))
    if extra_radar:
        problems.append(f"score_radar has unknown fields {extra_radar}")
    for field in RADAR_FIELDS:
        score = radar.get(field)
        if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 10:
            problems.append(f"score_radar.{field} must be an integer from 0 through 10")

    for field in SUMMARY_FIELDS:
        if not str(value.get(field, "")).strip():
            problems.append(f"{field} is required")

    serialized = json.dumps(value, ensure_ascii=False).casefold()
    if any(pattern.casefold() in serialized for pattern in FORBIDDEN_AWARD_PATTERNS):
        problems.append("award probability or guarantee language is forbidden")

    ordered = sorted(
        [item for item in source_findings if isinstance(item, dict)],
        key=lambda item: SEVERITY_ORDER.get(str(item.get("severity")), 99),
    )
    return {
        "operation": "competition-review-audit",
        "status": "PASS" if not problems else "FAIL",
        "findings": problems,
        "finding_count": len(source_findings),
        "ordered_findings": ordered,
        "score_radar": radar,
        "current_strongest_point": value.get("current_strongest_point", ""),
        "current_weakest_point": value.get("current_weakest_point", ""),
        "largest_award_level_blocker": value.get(
            "largest_award_level_blocker", ""
        ),
        "highest_roi_remaining_improvement": value.get(
            "highest_roi_remaining_improvement", ""
        ),
    }


def summary(value_or_path: dict[str, Any] | Path) -> dict[str, Any]:
    result = audit(value_or_path)
    counts = {severity: 0 for severity in ("CRITICAL", "MAJOR", "MINOR")}
    for finding in result["ordered_findings"]:
        severity = finding.get("severity")
        if severity in counts:
            counts[severity] += 1
    return result | {"severity_counts": counts}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("audit", "summary"):
        command = sub.add_parser(name)
        command.add_argument("path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = audit(args.path) if args.command == "audit" else summary(args.path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
