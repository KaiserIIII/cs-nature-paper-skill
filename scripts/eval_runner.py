#!/usr/bin/env python3
"""Prepare and score hidden behavior cases with explicit evaluation classes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_VERSION = "3.1.1"


def _now() -> str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def _read(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))
def _write(path: Path, value: Any) -> None: path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _behavior_match(answer: str, behavior: str) -> bool:
    """Match semantics, including explicit negation, for harness sanity checks."""
    normalized_answer = " ".join(answer.lower().split()); phrase = " ".join(str(behavior).lower().split())
    index = normalized_answer.find(phrase)
    if index < 0: return False
    prefix = normalized_answer[max(0, index - 48):index]
    if any(marker in prefix.split()[-6:] for marker in ("not", "never", "no", "cannot", "can't", "won't", "do", "avoid")):
        return False
    return True


def _commit() -> str:
    try: return subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError): return "UNKNOWN"


def prepare(cases_path: Path, output_dir: Path) -> dict[str, Any]:
    source = _read(cases_path); cases = source.get("cases", []); output_dir.mkdir(parents=True, exist_ok=True); prepared: list[str] = []
    for case in cases:
        public = {key: case.get(key) for key in ("id", "type", "prompt", "fixture") if key in case}; path = output_dir / f"{case['id']}.json"; _write(path, public); prepared.append(path.name)
    manifest = {"runner_version": SKILL_VERSION, "evaluation_class": "HARNESS_SELF_TEST", "cases_source": "assets/evals/behavior_cases.json", "prepared_utc": _now(), "skill_commit": _commit(), "prepared_cases": prepared, "answers_hidden": True, "environment": {"host": platform.platform(), "python": platform.python_version()}}
    _write(output_dir / "manifest.json", manifest); return {"operation": "prepare", "status": "PASS", "manifest": str(output_dir / "manifest.json"), "prepared_cases": len(prepared), "answers_hidden": True, "evaluation_class": "HARNESS_SELF_TEST"}


def run_record(manifest_path: Path, case_id: str, answer_path: Path, *, model: str, host: str, reasoning_mode: str, network: bool, tools: list[str], token_cost: int = 0, tool_calls: int = 0, human_interventions: int = 0, evaluation_class: str = "HARNESS_SELF_TEST", artifact_checks: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = _read(manifest_path); answer = answer_path.read_text(encoding="utf-8"); start = time.monotonic()
    if evaluation_class not in {"HARNESS_SELF_TEST", "MODEL_BEHAVIOR", "END_TO_END_AGENT"}: raise ValueError("invalid evaluation_class")
    record = {"case_id": case_id, "answer": answer, "evaluation_class": evaluation_class, "artifact_checks": artifact_checks or {}, "environment": {"skill_commit": manifest.get("skill_commit"), "model": model, "host": host, "reasoning_mode": reasoning_mode, "tools": tools, "network": network, "employee_registry": None, "date_utc": _now(), "token_cost": token_cost, "tool_calls": tool_calls, "wall_time_seconds": round(time.monotonic() - start, 6), "human_interventions": human_interventions}}
    run_path = manifest_path.parent / "runs" / f"{case_id}.json"; _write(run_path, record); return {"operation": "run-record", "status": "PASS", "record": str(run_path), "case_id": case_id, "evaluation_class": evaluation_class, "environment": record["environment"]}


def _artifact_findings(case: dict[str, Any], record: dict[str, Any]) -> list[str]:
    if record.get("evaluation_class", "HARNESS_SELF_TEST") == "HARNESS_SELF_TEST":
        return []
    required = case.get("required_artifacts", []); checks = record.get("artifact_checks", {})
    if not required: return []
    return [f"required artifact not observed: {name}" for name in required if checks.get(name) is not True]


def score(cases_path: Path, runs_dir: Path, output_path: Path) -> dict[str, Any]:
    cases = {case["id"]: case for case in _read(cases_path).get("cases", [])}; results: list[dict[str, Any]] = []; current = _commit()
    for case_id, case in cases.items():
        path = runs_dir / f"{case_id}.json"
        if not path.exists(): results.append({"case_id": case_id, "verdict": "NOT_RUN", "critical_failures": [], "major_failures": ["no run record"]}); continue
        record = _read(path); answer = str(record.get("answer", "")); required = case.get("required_behaviors", []); forbidden = case.get("forbidden_behaviors", [])
        stale = record.get("environment", {}).get("skill_commit") != current and current != "UNKNOWN"
        missing = [item for item in required if not _behavior_match(answer, item)]; violations = [item for item in forbidden if _behavior_match(answer, item)]; artifacts = _artifact_findings(case, record)
        critical = list(violations); major = list(missing) + artifacts
        if stale: critical.append("benchmark skill_commit does not match current tested commit")
        verdict = "FAIL" if critical else "CONDITIONAL" if major else "PASS"
        results.append({"case_id": case_id, "verdict": verdict, "critical_failures": critical, "major_failures": major, "evaluation_class": record.get("evaluation_class", "HARNESS_SELF_TEST"), "environment": record.get("environment", {}), "artifact_checks": record.get("artifact_checks", {})})
    value = {"runner_version": SKILL_VERSION, "scored_utc": _now(), "cases_source": "assets/evals/behavior_cases.json", "tested_skill_commit": current, "results": results, "summary": {"pass": sum(item["verdict"] == "PASS" for item in results), "conditional": sum(item["verdict"] == "CONDITIONAL" for item in results), "fail": sum(item["verdict"] == "FAIL" for item in results), "not_run": sum(item["verdict"] == "NOT_RUN" for item in results)}}
    _write(output_path, value); return {"operation": "score", "status": "PASS", "output": str(output_path), "summary": value["summary"], "tested_skill_commit": current}


def compare(left: Path, right: Path, output_path: Path) -> dict[str, Any]:
    a, b = _read(left), _read(right); by_a = {item["case_id"]: item for item in a.get("results", [])}; by_b = {item["case_id"]: item for item in b.get("results", [])}; cases = [{"case_id": case_id, "left": by_a.get(case_id, {"verdict": "NOT_RUN"}).get("verdict"), "right": by_b.get(case_id, {"verdict": "NOT_RUN"}).get("verdict"), "critical_failures_left": by_a.get(case_id, {}).get("critical_failures", []), "critical_failures_right": by_b.get(case_id, {}).get("critical_failures", [])} for case_id in sorted(set(by_a) | set(by_b))]
    value = {"operation": "compare", "status": "PASS", "left": str(left), "right": str(right), "case_results": cases, "average_score": "NOT_USED", "note": "case-level comparison; aggregate averages omitted"}; _write(output_path, value); return value | {"output": str(output_path)}


def report(score_path: Path) -> dict[str, Any]:
    value = _read(score_path); results = value.get("results", []); critical = [item for item in results if item.get("critical_failures")]; major = [item for item in results if item.get("major_failures")]; classes = sorted({item.get("evaluation_class", "HARNESS_SELF_TEST") for item in results}); return {"operation": "report", "status": "FAIL" if critical else "CONDITIONAL" if major or any(item.get("verdict") == "NOT_RUN" for item in results) else "PASS", "evaluation_classes": classes, "case_level_verdicts": results, "critical_failures": [item["case_id"] for item in critical], "major_or_unresolved": [item["case_id"] for item in major], "not_run": [item["case_id"] for item in results if item.get("verdict") == "NOT_RUN"], "average_score": "NOT_USED"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare"); p.add_argument("cases", type=Path); p.add_argument("output", type=Path)
    p = sub.add_parser("run-record"); p.add_argument("manifest", type=Path); p.add_argument("case_id"); p.add_argument("answer", type=Path); p.add_argument("--model", default="local-deterministic"); p.add_argument("--host", default=platform.platform()); p.add_argument("--reasoning-mode", default="deterministic"); p.add_argument("--network", action="store_true"); p.add_argument("--tool", action="append", default=[]); p.add_argument("--token-cost", type=int, default=0); p.add_argument("--tool-calls", type=int, default=0); p.add_argument("--human-interventions", type=int, default=0)
    p = sub.add_parser("score"); p.add_argument("cases", type=Path); p.add_argument("runs", type=Path); p.add_argument("output", type=Path)
    p = sub.add_parser("compare"); p.add_argument("left", type=Path); p.add_argument("right", type=Path); p.add_argument("output", type=Path)
    p = sub.add_parser("report"); p.add_argument("score", type=Path)
    args = parser.parse_args()
    if args.command == "prepare": result = prepare(args.cases, args.output)
    elif args.command == "run-record": result = run_record(args.manifest, args.case_id, args.answer, model=args.model, host=args.host, reasoning_mode=args.reasoning_mode, network=args.network, tools=args.tool, token_cost=args.token_cost, tool_calls=args.tool_calls, human_interventions=args.human_interventions)
    elif args.command == "score": result = score(args.cases, args.runs, args.output)
    elif args.command == "compare": result = compare(args.left, args.right, args.output)
    else: result = report(args.score)
    print(json.dumps(result, indent=2, ensure_ascii=False)); sys.exit(0 if result.get("status") in {"PASS", "CONDITIONAL"} else 1)
