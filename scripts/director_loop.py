#!/usr/bin/env python3
"""Resumable v3.2 research executor: authorize, dispatch, check, evidence, transition."""

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
GLOBAL_RECOVERY_BUDGET = 20
NODE_RECOVERY_BUDGETS = {"implementation": 5, "formal_experiment": 4, "analysis": 3}
IDENTICAL_FAILURE_LIMIT = 3
MAX_RECOVERIES = IDENTICAL_FAILURE_LIMIT


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
executor_runtime = _load("research_executor")
marketplace_runtime = _load("skill_marketplace_runtime")


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
        "schema_version": 2,
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
        "recovery": {"global_budget": GLOBAL_RECOVERY_BUDGET, "nodes": {}, "failures": {}},
        "ordinary_author_prompts": 0,
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


def _node_map(project: Path) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in graph_runtime.load_graph(project)[1].get("nodes", []) if isinstance(item, dict) and item.get("id")}


def _dependencies_complete(nodes: dict[str, dict[str, Any]], node: dict[str, Any]) -> bool:
    return all(nodes.get(dep, {}).get("status") in {"PASS", "CONDITIONAL"} for dep in node.get("depends_on", []))


def _next_node(project: Path) -> str | None:
    nodes = _node_map(project)
    for node_id in executor_runtime.MAIN_SEQUENCE:
        node = nodes.get(node_id)
        if not node or node.get("status") in {"PASS", "CONDITIONAL"}:
            continue
        if node.get("status") in {"READY", "PLANNED", "REOPENED"} and _dependencies_complete(nodes, node):
            return node_id
        return None
    return None


def _complete(project: Path) -> bool:
    nodes = _node_map(project)
    return all(nodes.get(node_id, {}).get("status") in {"PASS", "CONDITIONAL"} for node_id in executor_runtime.MAIN_SEQUENCE)


def _authorization_for(policy: dict[str, Any], node: str, actor: str, now: str) -> dict[str, Any]:
    if node == "literature":
        return autonomy.authorize(policy, "NETWORK_READ", scope="literature/public", risk="LOW", actor=actor, now=now)
    if node == "protocol_freeze":
        return autonomy.authorize(policy, "PROTOCOL_CHANGE", scope="protocol", risk="MEDIUM", actor=actor, now=now, decision_kind="bounded_protocol_amendment")
    if node in {"innovation", "feasibility", "analysis", "evidence_update", "figures", "review", "revision"}:
        decision = {
            "innovation": "narrow_claim_scope",
            "feasibility": "choose_implementation_method",
            "analysis": "choose_statistical_test",
            "evidence_update": "remove_unsupported_claim",
            "figures": "choose_visualization",
            "review": "ordinary",
            "revision": "repair_implementation",
        }[node]
        return autonomy.authorize(policy, "SCIENTIFIC_DECISION", scope=node, risk="LOW", actor=actor, now=now, decision_kind=decision)
    action = "RUN_LOCAL_JOB" if node in {"implementation", "pilot", "formal_experiment", "validation"} else "WRITE_LOCAL"
    return autonomy.authorize(policy, action, scope=f"project/{node}", risk="LOW", actor=actor, now=now)


def resolve_capability(
    project: Path,
    capability: str,
    *,
    candidate_pool: list[dict[str, Any]] | None = None,
    payload: dict[str, Any] | None = None,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    native = set(executor_runtime.EXECUTORS)
    registry = _read(_state(project) / "employee_registry.json", {})
    installed = registry.get("employees", []) if isinstance(registry, dict) else []
    vacancy = marketplace_runtime.capability_vacancy(capability, native, installed)
    if vacancy["status"] == "COVERED":
        return {"operation": "resolve-capability", "status": "PASS", "source": "native-or-installed", "vacancy": vacancy}
    if not candidate_pool or policy is None:
        return {"operation": "resolve-capability", "status": "BLOCKED", "reason": "missing capability and no candidate pool", "recovery": "AUTO_HIRE", "vacancy": vacancy}
    hire = marketplace_runtime.hire_and_execute(project, capability, candidate_pool, payload or {}, policy=policy)
    return {"operation": "resolve-capability", "status": "PASS" if hire.get("status") == "ACCEPTED" else "BLOCKED", "source": "AUTO_HIRE", "hire": hire, "vacancy": vacancy}


def recovery_decision(project: Path, node_id: str, failure_signature: str, *, previous_result: str) -> dict[str, Any]:
    project = project.resolve()
    policy_path = _policy_path(project)
    graph_path = _state(project) / "research_graph.json"
    try:
        session = load_session(project)
    except DirectorError:
        session = _new_session(project, _hash_file(policy_path), _hash_file(graph_path), _now())
    recovery = session.setdefault("recovery", {"global_budget": GLOBAL_RECOVERY_BUDGET, "nodes": {}, "failures": {}})
    failures = recovery.setdefault("failures", {})
    key = f"{node_id}|{failure_signature}"
    attempt = int(failures.get(key, {}).get("attempt_count", 0)) + 1
    node_attempt = int(recovery.setdefault("nodes", {}).get(node_id, 0)) + 1
    global_attempt = int(session.get("recovery_count", 0)) + 1
    if attempt >= IDENTICAL_FAILURE_LIMIT:
        strategy, status, reason = "STOP", "BLOCKED", "repeated identical failure"
    elif global_attempt > int(recovery.get("global_budget", GLOBAL_RECOVERY_BUDGET)):
        strategy, status, reason = "STOP", "BLOCKED", "global recovery budget exhausted"
    elif node_attempt > NODE_RECOVERY_BUDGETS.get(node_id, 3):
        strategy, status, reason = "STOP", "BLOCKED", "node recovery budget exhausted"
    else:
        strategy = {
            "implementation": "REPAIR",
            "formal_experiment": "RETRY",
            "analysis": "REPLAN",
            "capability": "AUTO_HIRE",
            "scope": "REDUCE_SCOPE",
        }.get(node_id, "RETRY")
        status, reason = "PASS", "bounded automatic recovery selected"
    failures[key] = {"failure_signature": failure_signature, "attempt_count": attempt, "repair_strategy": strategy, "previous_result": previous_result}
    recovery["nodes"][node_id] = node_attempt
    session["recovery_count"] = global_attempt
    session["last_decision"] = {"recovery": node_id, "strategy": strategy, "failure_signature": failure_signature}
    if status == "BLOCKED":
        session.update({"status": "BLOCKED", "blocked_reason": reason})
    _persist(project, session)
    return {"operation": "recovery-decision", "status": status, "node": node_id, "strategy": strategy, "reason": reason, "attempt_count": attempt, "failure_signature": failure_signature, "previous_result": previous_result}


def run(project: Path, *, max_iterations: int = 32, actor: str = "director", now: str | None = None) -> dict[str, Any]:
    project = project.resolve()
    policy_path = _policy_path(project)
    if not policy_path.exists():
        return {"operation": "director-run", "status": "BLOCKED", "reason": "autonomy policy is missing"}
    try:
        policy = autonomy.load_policy(policy_path)
        graph_runtime.validate_project(project)
    except Exception as exc:
        return {"operation": "director-run", "status": "BLOCKED", "reason": str(exc)}
    decision_time = now or _now()
    session = _read(_session_path(project))
    if not isinstance(session, dict) or not session.get("session_id"):
        session = _new_session(project, _hash_file(policy_path), _graph_hash(project), decision_time)
    else:
        identity = _identity_findings(project, session)
        if identity:
            session.update({"status": "BLOCKED", "blocked_reason": "; ".join(identity), "last_decision": "BLOCKED"})
            _persist(project, session)
            return {"operation": "director-run", "status": "BLOCKED", "session_id": session.get("session_id"), "reason": "; ".join(identity)}
    if max_iterations < 1:
        return {"operation": "director-run", "status": "BLOCKED", "reason": "max_iterations must be positive", "session_id": session["session_id"]}
    for _ in range(max_iterations):
        if _complete(project):
            session.update({"status": "READY_FOR_SUBMISSION", "current_node": None, "blocked_reason": None, "graph_hash": _graph_hash(project)})
            _persist(project, session)
            return {"operation": "director-run", "status": "READY_FOR_SUBMISSION", "session_id": session["session_id"], "iteration": session["iteration"], "completed": session["completed"], "ordinary_author_prompts": session.get("ordinary_author_prompts", 0)}
        resuming_host = session.get("status") == "HOST_EXECUTION_REQUIRED" and bool(session.get("current_node"))
        if resuming_host:
            node_id = str(session["current_node"])
            authorization = session.get("pending_authorization") or {
                "status": "AUTHORIZED", "decision": "AUTO", "reason": "resume accepted host handoff",
            }
        else:
            node_id = _next_node(project)
            if node_id is None:
                session.update({"status": "BLOCKED", "blocked_reason": "no executable node; dependency or graph state prevents progress", "last_decision": "BLOCKED", "graph_hash": _graph_hash(project)})
                _persist(project, session)
                return {"operation": "director-run", "status": "BLOCKED", "session_id": session["session_id"], "reason": session["blocked_reason"], "ordinary_author_prompts": session.get("ordinary_author_prompts", 0)}
            authorization = _authorization_for(policy, node_id, actor, decision_time)
            autonomy.append_audit(_audit_path(project), "node-authorization", {"session_id": session["session_id"], "node": node_id, "authorization": authorization.get("decision")}, actor=actor, decision=authorization["status"], utc=decision_time)
            if authorization["status"] != "AUTHORIZED":
                if authorization.get("decision") == "ASK_AUTHOR":
                    session["ordinary_author_prompts"] = int(session.get("ordinary_author_prompts", 0)) + 1
                session.update({"status": "BLOCKED", "blocked_reason": authorization.get("reason"), "last_decision": authorization})
                _persist(project, session)
                return {"operation": "director-run", "status": "BLOCKED", "session_id": session["session_id"], "reason": authorization.get("reason"), "ordinary_author_prompts": session.get("ordinary_author_prompts", 0)}
            session["current_node"] = node_id
            session["iteration"] += 1
            graph_runtime.transition(project, node_id, "RUNNING", "authorized executor dispatch", actor, None)
        result = executor_runtime.execute_node(project, node_id)
        if result.get("status") == "HOST_EXECUTION_REQUIRED":
            session.update({
                "status": "HOST_EXECUTION_REQUIRED",
                "current_node": node_id,
                "pending_authorization": authorization,
                "pending_host_request": result.get("request_path"),
                "blocked_reason": None,
                "last_decision": {
                    "node": node_id,
                    "executor": "HOST_EXECUTION_REQUIRED",
                    "request_path": result.get("request_path"),
                },
                "graph_hash": _graph_hash(project),
            })
            _persist(project, session)
            return {
                "operation": "director-run",
                "status": "HOST_EXECUTION_REQUIRED",
                "session_id": session["session_id"],
                "node": node_id,
                "request_path": result.get("request_path"),
                "host_request_created": result.get("host_request_created", True),
                "ordinary_author_prompts": session.get("ordinary_author_prompts", 0),
            }
        if result.get("status") == "PASS":
            evidence = ",".join(result.get("evidence", []))
            graph_runtime.transition(project, node_id, "PASS", "executor output contract passed", actor, evidence)
            session.setdefault("completed", []).append(node_id)
            session["completed"] = list(dict.fromkeys(session["completed"]))
            session["last_decision"] = {"node": node_id, "authorization": authorization.get("decision"), "executor": "PASS", "artifacts": result.get("artifacts", []), "evidence": result.get("evidence", [])}
            session.pop("pending_authorization", None)
            session.pop("pending_host_request", None)
            session.setdefault("checkpoints", []).append({"iteration": session["iteration"], "utc": decision_time, "node": node_id, "status": "PASS", "artifacts": result.get("artifacts", [])})
        else:
            graph_runtime.transition(project, node_id, "FAIL", "executor output contract failed", actor, None)
            signature = result.get("failure_signature") or f"{node_id}:{'|'.join(result.get('findings', []))}"
            recovery = recovery_decision(project, node_id, signature, previous_result=result.get("status", "FAIL"))
            session = load_session(project)
            if recovery["status"] == "BLOCKED":
                session["graph_hash"] = _graph_hash(project)
                _persist(project, session)
                return {"operation": "director-run", "status": "BLOCKED", "session_id": session["session_id"], "reason": recovery["reason"], "recovery": recovery, "ordinary_author_prompts": session.get("ordinary_author_prompts", 0)}
            graph_runtime.transition(project, node_id, "REOPENED", f"automatic recovery: {recovery['strategy']}", actor, None)
            autonomy.append_audit(_audit_path(project), "automatic-recovery", recovery, actor=actor, decision="AUTO_WITH_AUDIT", utc=decision_time)
            session["last_decision"] = {"node": node_id, "executor": result.get("status"), "recovery": recovery}
        session["graph_hash"] = _graph_hash(project)
        session["status"] = "RUNNING"
        _persist(project, session)
    if _complete(project):
        session.update({"status": "READY_FOR_SUBMISSION", "current_node": None, "blocked_reason": None, "graph_hash": _graph_hash(project)})
        _persist(project, session)
        return {"operation": "director-run", "status": "READY_FOR_SUBMISSION", "session_id": session["session_id"], "iteration": session["iteration"], "completed": session["completed"], "ordinary_author_prompts": session.get("ordinary_author_prompts", 0)}
    session.update({"status": "PAUSED", "graph_hash": _graph_hash(project)})
    _persist(project, session)
    return {"operation": "director-run", "status": "PAUSED", "session_id": session["session_id"], "iteration": session["iteration"], "completed": session["completed"], "last_decision": session["last_decision"], "ordinary_author_prompts": session.get("ordinary_author_prompts", 0)}


def resume(project: Path, *, actor: str = "director", now: str | None = None) -> dict[str, Any]:
    project = project.resolve()
    try:
        session = load_session(project)
    except DirectorError as exc:
        return {"operation": "director-resume", "status": "BLOCKED", "reason": str(exc)}
    audit = autonomy.verify_audit(_audit_path(project))
    if audit["status"] != "PASS":
        return {"operation": "director-resume", "status": "BLOCKED", "session_id": session["session_id"], "reason": "autonomy audit integrity failed"}
    identity = _identity_findings(project, session)
    if identity:
        session.update({"status": "BLOCKED", "blocked_reason": "; ".join(identity), "last_decision": "BLOCKED"})
        _persist(project, session)
        return {"operation": "director-resume", "status": "BLOCKED", "session_id": session["session_id"], "reason": session["blocked_reason"]}
    result = run(project, max_iterations=1, actor=actor, now=now)
    result["operation"] = "director-resume"
    return result


def recover(project: Path, node_id: str, *, reason: str, actor: str = "director") -> dict[str, Any]:
    project = project.resolve()
    decision = recovery_decision(project, node_id, reason, previous_result="FAIL")
    session = load_session(project)
    if decision["status"] == "BLOCKED":
        return {"operation": "director-recover", "status": "BLOCKED", "session_id": session["session_id"], "reason": decision["reason"]}
    try:
        current = _node_map(project)[node_id]
        old = current.get("status")
        if old != "REOPENED":
            graph_runtime.transition(project, node_id, "REOPENED", reason, actor, None)
    except Exception as exc:
        return {"operation": "director-recover", "status": "BLOCKED", "reason": str(exc)}
    session = load_session(project)
    session.update({"status": "PAUSED", "graph_hash": _graph_hash(project), "last_decision": {"recovery": node_id, "reason": reason, "strategy": decision["strategy"]}})
    _persist(project, session)
    autonomy.append_audit(_audit_path(project), "recovery", {"node": node_id, "reason": reason, "count": session["recovery_count"], "strategy": decision["strategy"]}, actor=actor, decision="REOPENED")
    return {"operation": "director-recover", "status": "PASS", "session_id": session["session_id"], "node": node_id, "from": old, "to": "REOPENED", "recovery_count": session["recovery_count"], "strategy": decision["strategy"]}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run"); p.add_argument("project", type=Path); p.add_argument("--max-iterations", type=int, default=32)
    p = sub.add_parser("resume"); p.add_argument("project", type=Path)
    p = sub.add_parser("recover"); p.add_argument("project", type=Path); p.add_argument("--node", required=True); p.add_argument("--reason", required=True)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    if args.command == "run":
        result = run(args.project, max_iterations=args.max_iterations)
    elif args.command == "resume":
        result = resume(args.project)
    else:
        result = recover(args.project, args.node, reason=args.reason)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("status") in {"PASS", "PAUSED", "READY_FOR_SUBMISSION"} else 1)
