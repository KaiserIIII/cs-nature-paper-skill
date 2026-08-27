#!/usr/bin/env python3
"""Prepare, run, score, compare, and report behavior evaluations.

Prepared case files intentionally contain only prompt and fixture. Required and
forbidden behavior labels stay in the evaluator input and are never exposed to
the agent-facing directory.
"""

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


def _now() -> str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
def _read(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))
def _write(path: Path, value: Any) -> None: path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _behavior_match(answer: str, behavior: str) -> bool:
    """Match a behavior as a phrase or complete set of meaningful words.

    Matching any single word creates false positives for negations and for
    behaviors that intentionally share terms (for example, ``data``).
    """
    normalized_answer = " ".join(answer.lower().split())
    normalized_behavior = " ".join(str(behavior).lower().split())
    if normalized_behavior in normalized_answer:
        return True
    tokens = [token for token in normalized_behavior.replace("/", " ").split() if len(token) > 3]
    return bool(tokens) and all(token in normalized_answer for token in tokens)


def _commit() -> str:
    try: return subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError): return "UNKNOWN"


def prepare(cases_path: Path, output_dir: Path) -> dict[str, Any]:
    source = _read(cases_path); cases = source.get("cases", [])
    output_dir.mkdir(parents=True, exist_ok=True); prepared: list[str] = []
    for case in cases:
        public = {key: case.get(key) for key in ("id", "type", "prompt", "fixture") if key in case}
        path = output_dir / f"{case['id']}.json"; _write(path, public); prepared.append(str(path))
    manifest = {"runner_version":"3.1.0","cases_source":str(cases_path),"prepared_utc":_now(),"skill_commit":_commit(),"prepared_cases":prepared,"answers_hidden":True,"environment":{"host":platform.platform(),"python":platform.python_version()}}
    _write(output_dir / "manifest.json", manifest); return {"operation":"prepare","status":"PASS","manifest":str(output_dir / "manifest.json"),"prepared_cases":len(prepared),"answers_hidden":True}


def run_record(manifest_path: Path, case_id: str, answer_path: Path, *, model: str, host: str, reasoning_mode: str, network: bool, tools: list[str], token_cost: int = 0, tool_calls: int = 0, human_interventions: int = 0) -> dict[str, Any]:
    manifest = _read(manifest_path); answer = answer_path.read_text(encoding="utf-8"); start = time.monotonic()
    record = {"case_id":case_id,"answer":answer,"environment":{"skill_commit":manifest.get("skill_commit"),"model":model,"host":host,"reasoning_mode":reasoning_mode,"tools":tools,"network":network,"employee_registry":None,"date_utc":_now(),"token_cost":token_cost,"tool_calls":tool_calls,"wall_time_seconds":round(time.monotonic()-start,6),"human_interventions":human_interventions}}
    run_path = manifest_path.parent / "runs" / f"{case_id}.json"; _write(run_path, record)
    return {"operation":"run-record","status":"PASS","record":str(run_path),"case_id":case_id,"environment":record["environment"]}


def score(cases_path: Path, runs_dir: Path, output_path: Path) -> dict[str, Any]:
    cases = {case["id"]: case for case in _read(cases_path).get("cases", [])}; results: list[dict[str, Any]] = []
    for case_id, case in cases.items():
        path = runs_dir / f"{case_id}.json"
        if not path.exists():
            results.append({"case_id":case_id,"verdict":"NOT_RUN","critical_failures":[],"major_failures":["no run record"]}); continue
        answer = str(_read(path).get("answer", "")).lower(); required = case.get("required_behaviors", []); forbidden = case.get("forbidden_behaviors", [])
        missing = [item for item in required if not _behavior_match(answer, item)]
        violations = [item for item in forbidden if _behavior_match(answer, item)]
        verdict = "FAIL" if violations else ("CONDITIONAL" if missing else "PASS")
        results.append({"case_id":case_id,"verdict":verdict,"critical_failures":violations,"major_failures":missing,"environment":_read(path).get("environment", {})})
    value = {"runner_version":"3.1.0","scored_utc":_now(),"cases_source":str(cases_path),"results":results,"summary":{"pass":sum(item["verdict"]=="PASS" for item in results),"conditional":sum(item["verdict"]=="CONDITIONAL" for item in results),"fail":sum(item["verdict"]=="FAIL" for item in results),"not_run":sum(item["verdict"]=="NOT_RUN" for item in results)}}
    _write(output_path, value); return {"operation":"score","status":"PASS","output":str(output_path),"summary":value["summary"]}


def compare(left: Path, right: Path, output_path: Path) -> dict[str, Any]:
    a, b = _read(left), _read(right); by_a = {item["case_id"]: item for item in a.get("results", [])}; by_b = {item["case_id"]: item for item in b.get("results", [])}; cases = []
    for case_id in sorted(set(by_a) | set(by_b)):
        cases.append({"case_id":case_id,"left":by_a.get(case_id, {"verdict":"NOT_RUN"}).get("verdict"),"right":by_b.get(case_id, {"verdict":"NOT_RUN"}).get("verdict"),"critical_failures_left":by_a.get(case_id, {}).get("critical_failures", []),"critical_failures_right":by_b.get(case_id, {}).get("critical_failures", [])})
    value = {"operation":"compare","status":"PASS","left":str(left),"right":str(right),"case_results":cases,"average_score":"NOT_USED","note":"comparison is case-level; aggregate averages are intentionally omitted"}; _write(output_path, value); return value | {"output":str(output_path)}


def report(score_path: Path) -> dict[str, Any]:
    value = _read(score_path); results = value.get("results", []); critical = [item for item in results if item.get("critical_failures")]; major = [item for item in results if item.get("major_failures")]; return {"operation":"report","status":"FAIL" if critical else ("CONDITIONAL" if major or any(item.get("verdict")=="NOT_RUN" for item in results) else "PASS"),"case_level_verdicts":results,"critical_failures":[item["case_id"] for item in critical],"major_or_unresolved":[item["case_id"] for item in major],"not_run":[item["case_id"] for item in results if item.get("verdict")=="NOT_RUN"],"average_score":"NOT_USED"}


def _parser() -> argparse.ArgumentParser:
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("prepare"); p.add_argument("cases",type=Path); p.add_argument("output",type=Path)
    p=sub.add_parser("run-record"); p.add_argument("manifest",type=Path); p.add_argument("case_id"); p.add_argument("answer",type=Path); p.add_argument("--model",default="local-deterministic"); p.add_argument("--host",default=platform.platform()); p.add_argument("--reasoning-mode",default="deterministic"); p.add_argument("--network",action="store_true"); p.add_argument("--tool",action="append",default=[]); p.add_argument("--token-cost",type=int,default=0); p.add_argument("--tool-calls",type=int,default=0); p.add_argument("--human-interventions",type=int,default=0)
    p=sub.add_parser("score"); p.add_argument("cases",type=Path); p.add_argument("runs",type=Path); p.add_argument("output",type=Path)
    p=sub.add_parser("compare"); p.add_argument("left",type=Path); p.add_argument("right",type=Path); p.add_argument("output",type=Path)
    p=sub.add_parser("report"); p.add_argument("score",type=Path)
    return parser


def main(argv: list[str] | None=None) -> int:
    args=_parser().parse_args(argv)
    if args.command=="prepare": result=prepare(args.cases,args.output)
    elif args.command=="run-record": result=run_record(args.manifest,args.case_id,args.answer,model=args.model,host=args.host,reasoning_mode=args.reasoning_mode,network=args.network,tools=args.tool,token_cost=args.token_cost,tool_calls=args.tool_calls,human_interventions=args.human_interventions)
    elif args.command=="score": result=score(args.cases,args.runs,args.output)
    elif args.command=="compare": result=compare(args.left,args.right,args.output)
    else: result=report(args.score)
    print(json.dumps(result,indent=2,ensure_ascii=False)); return 0 if result.get("status") in {"PASS","CONDITIONAL"} else 1


if __name__=="__main__": sys.exit(main())
