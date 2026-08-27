#!/usr/bin/env python3
"""Route a research task to a bounded methods playbook."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "assets" / "registry" / "method_router.json"


def _read() -> dict[str, Any]:
    return json.loads(ROUTER.read_text(encoding="utf-8"))


def route(task: str, explicit: str | None = None) -> dict[str, Any]:
    methods = _read()["methods"]
    if explicit:
        matches = [item for item in methods if item["id"] == explicit]
        if not matches:
            return {"operation": "route", "status": "FAIL", "findings": [f"unknown method: {explicit}"]}
        selected = matches[0]
        confidence = "explicit"
    else:
        text = task.lower()
        scored = []
        for item in methods:
            hits = [trigger for trigger in item.get("triggers", []) if trigger.lower() in text]
            scored.append((len(hits), item))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
        score, selected = scored[0]
        confidence = "keyword" if score else "descriptive-fallback"
    return {"operation": "route", "status": "PASS", "task": task, "method": selected["id"], "confidence": confidence, "required_definitions": selected["required_definitions"], "estimands": selected["common_estimands"], "evidence_requirements": selected["evidence_requirements"], "minimum_checks": selected["minimum_checks"], "specialist_escalation": selected["specialist_escalation"], "forbidden_claims": selected["forbidden_claims"], "source": str(ROUTER)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("route"); p.add_argument("task"); p.add_argument("--method")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv); result = route(args.task, args.method); print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__": sys.exit(main())
