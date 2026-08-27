#!/usr/bin/env python3
"""Bounded, resumable v3.2 director loop."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_VERSION = "3.2.0"
MAX_RECOVERIES = 3


def _load(name: str):
    path = Path(__file__).with_name(name + ".py")
    spec = importlib.util.spec_from_file_location("v32_director_" + name, path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


autonomy = _load("autonomy")
graph_runtime = _load("research_graph")


class DirectorError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _state(project: Path) -> Path:
    project = project.resolve()
    for name in (".research-state-v31", ".research-state-v3", ".research-state"):
        candidate = project / name
        if candidate.exists():
            return candidate
    return project / ".research-state"


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _hash_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _graph_hash(project: Path) -> str:
    return _hash_file(_state(project) / "research_graph.json")


def _policy_path(project: Path) -> Path:
    return _state(project) / "autonomy_policy.json"


def _session_path(project: Path) -> Path:
    return _state(project) / "director_session.json"


def _audit_path(project: Path) -> Path:
    return _state(project) / ".autonomy-audit.jsonl"


def load_session(project: Path) -> dict[str, Any]:
    value = _read(_session_path(project))
    if not isinstance(value, dict) or not value.get("session_id"):
        raise DirectorError("director session is missing or uninitialized")
    return value


def _new_session(project: Path, policy_hash: str, graph_hash: str, now: str) -> dict[str, Any]:
    session_id = "DS-" + hashlib.sha256(f"{project.resolve()}|{now}".encode("utf-8")).hexdigest()[:16]
    return {
        "schema_version": 1,
        "skill_version": SKILL_VERSION,
        "session_id": session_id,
        "status": "RUNNING",
        "policy_hash": policy_hash,
        "graph_hash": graph_hash,
        "iteration": 0,
        "current_node": None,
        "completed": [],
        "checkpoints": [],
        "recovery_count": 0,
        "last_decision": None,
        "blocked_reason": None,
    }


def _identity_findings(project: Path, session: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    policy_path = _policy_path(project)
    graph_path = _state(project) / "research_graph.json"
    if not policy_path.exists() or not graph_path.exists():
        return ["policy or graph is missing"]
    if session.get("policy_hash") != _hash_file(policy_path):
        findings.append("policy identity drift")
    if session.get("graph_hash") != _hash_file(graph_path):
        findings.append("graph identity drift")
    return findings


def _persist(project: Path, session: dict[str, Any]) -> None:
    _write(_session_path(project), session)


def run(project: Path, *, max_iterations: int = 8, actor: str = "director", now: str | None = None) -> dict[str, Any]:
    project = project.resolve()
    state = _state(project)
    policy_path = _policy_path(project)
    if not policy_path.exists():
        return {"operation": "director-run", "status": "BLOCKED", "reason": "autonomy policy is missing"}
    try:
        policy = autonomy.load_policy(policy_path)
        graph_runtime.validate_project(project)
    except Exception as exc:
        return {"operation": "director-run", "status": "BLOCKED", "reason": str(exc)}
    decision_time = now or _now()
    session_file = _session_path(project)
    session = _read(session_file)
    if not isinstance(session, dict) or not session.get("session_id"):
        session = _new_session(project, _hash_file(policy_path), _graph_hash(project), decision_time)
    else:
        identity = _identity_findings(project, session)
        if identity:
            session.update({"status": "BLOCKED", "blocked_reason": "; ".join(identity), "last_decision": "BLOCKED"})
            _persist(project, session)
            return {"operation": "director-run", "status": "BLOCKED", "session_id": session.get("session_id"), "reason": "; ".join(identity)}
    if max_iterations < 1:
        session.update({"status": "BLOCKED", "blocked_reason": "max_iterations must be positive", "last_decision": "BLOCKED"})
        _persist(project, session)
        return {"operation": "director-run", "status": "BLOCKED", "session_id": session["session_id"], "reason": session["blocked_reason"]}
    for _ in range(max_iterations):
        auth = autonomy.authorize(policy, "RUN_LOCAL_JOB", scope="project", risk="LOW", actor=actor, now=decision_time)
        autonomy.append_audit(_audit_path(project), "director-iteration", {"session_id": session["session_id"], "iteration": session["iteration"] + 1}, actor=actor, decision=auth["status"], utc=decision_time)
        if auth["status"] != "AUTHORIZED":
            session.update({"status": "BLOCKED", "blocked_reason": auth.get("reason"), "last_decision": "BLOCKED"})
            _persist(project, session)
            return {"operation": "director-run", "status": "BLOCKED", "session_id": session["session_id"], "reason": auth.get("reason")}
        plan = graph_runtime.plan_next(project)
        session["iteration"] += 1
        session["last_decision"] = {"ready": plan.get("ready", []), "actions": plan.get("actions", [])}
        session["checkpoints"].append({"iteration": session["iteration"], "utc": decision_time, "ready": plan.get("ready", []), "actions": plan.get("actions", [])})
        if plan.get("actions"):
            graph_runtime.advance(project, actor=actor)
        status = graph_runtime.status_graph(project)
        session["completed"] = [item["id"] for item in status.get("nodes", []) if item.get("status") in {"PASS", "CONDITIONAL"}]
        session["graph_hash"] = _graph_hash(project)
        if not plan.get("ready") and not plan.get("actions"):
            session.update({"status": "BLOCKED", "blocked_reason": "no ready graph work", "last_decision": "BLOCKED"})
            _persist(project, session)
            return {"operation": "director-run", "status": "BLOCKED", "session_id": session["session_id"], "reason": session["blocked_reason"]}
    session["status"] = "PAUSED"
    _persist(project, session)
    return {"operation": "director-run", "status": "PAUSED", "session_id": session["session_id"], "iteration": session["iteration"], "completed": session["completed"], "last_decision": session["last_decision"]}


def resume(project: Path, *, actor: str = "director", now: str | None = None) -> dict[str, Any]:
    project = project.resolve()
    try:
        session = load_session(project)
    except DirectorError as exc:
        return {"operation": "director-resume", "status": "BLOCKED", "reason": str(exc)}
    audit = autonomy.verify_audit(_audit_path(project))
    if audit["status"] != "PASS":
        session.update({"status": "BLOCKED", "blocked_reason": "autonomy audit integrity failed", "last_decision": "BLOCKED"})
        _persist(project, session)
        return {"operation": "director-resume", "status": "BLOCKED", "session_id": session["session_id"], "reason": session["blocked_reason"]}
    identity = _identity_findings(project, session)
    if identity:
        session.update({"status": "BLOCKED", "blocked_reason": "; ".join(identity), "last_decision": "BLOCKED"})
        _persist(project, session)
        return {"operation": "director-resume", "status": "BLOCKED", "session_id": session["session_id"], "reason": session["blocked_reason"]}
    result = run(project, max_iterations=1, actor=actor, now=now)
    result["operation"] = "director-resume"
    return result | {"session_id": session["session_id"]}


def recover(project: Path, node_id: str, *, reason: str, actor: str = "director") -> dict[str, Any]:
    project = project.resolve()
    try:
        session = load_session(project)
    except DirectorError:
        session = _new_session(project, _hash_file(_policy_path(project)), _graph_hash(project), _now())
    if session.get("recovery_count", 0) >= MAX_RECOVERIES:
        session.update({"status": "BLOCKED", "blocked_reason": "recovery budget exhausted", "last_decision": "BLOCKED"})
        _persist(project, session)
        return {"operation": "director-recover", "status": "BLOCKED", "session_id": session["session_id"], "reason": session["blocked_reason"]}
    try:
        current = next(item for item in graph_runtime.load_graph(project)[1]["nodes"] if item.get("id") == node_id)
        old = current.get("status")
        if old != "REOPENED":
            transition = graph_runtime.transition(project, node_id, "REOPENED", reason, actor, None)
        else:
            transition = {"to": "REOPENED", "from": old}
    except Exception as exc:
        return {"operation": "director-recover", "status": "BLOCKED", "reason": str(exc)}
    session["recovery_count"] = session.get("recovery_count", 0) + 1
    session["status"] = "PAUSED"
    session["graph_hash"] = _graph_hash(project)
    session["last_decision"] = {"recovery": node_id, "reason": reason}
    _persist(project, session)
    autonomy.append_audit(_audit_path(project), "recovery", {"node": node_id, "reason": reason, "count": session["recovery_count"]}, actor=actor, decision="REOPENED")
    return {"operation": "director-recover", "status": "PASS", "session_id": session["session_id"], "node": node_id, "from": transition.get("from"), "to": "REOPENED", "recovery_count": session["recovery_count"]}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run"); p.add_argument("project", type=Path); p.add_argument("--max-iterations", type=int, default=8)
    p = sub.add_parser("resume"); p.add_argument("project", type=Path)
    p = sub.add_parser("recover"); p.add_argument("project", type=Path); p.add_argument("--node", required=True); p.add_argument("--reason", required=True)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    if args.command == "run": result = run(args.project, max_iterations=args.max_iterations)
    elif args.command == "resume": result = resume(args.project)
    else: result = recover(args.project, args.node, reason=args.reason)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("status") in {"PASS", "PAUSED"} else 1)
