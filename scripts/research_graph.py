#!/usr/bin/env python3
"""Validate and advance the append-only V3 research graph."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUSES = {"PLANNED", "READY", "RUNNING", "BLOCKED", "PASS", "CONDITIONAL", "FAIL", "REOPENED", "SUPERSEDED", "WITHDRAWN"}
TERMINAL = {"PASS", "CONDITIONAL", "FAIL", "SUPERSEDED", "WITHDRAWN"}


class GraphError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _state_dir(project: Path) -> Path:
    v3 = project.resolve() / ".research-state-v3"
    return v3 if v3.exists() else project.resolve() / ".research-state"


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise GraphError(f"cannot read graph: {path}") from exc
    if not isinstance(value, dict):
        raise GraphError("graph root must be an object")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_graph(graph: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not nodes:
        findings.append("nodes must be a non-empty list")
        nodes = []
    if not isinstance(edges, list):
        findings.append("edges must be a list")
        edges = []
    ids: list[str] = []
    for index, node in enumerate(nodes):
        label = f"nodes[{index}]"
        if not isinstance(node, dict):
            findings.append(f"{label} must be an object")
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            findings.append(f"{label}.id is required")
        else:
            ids.append(node_id)
        if node.get("status") not in STATUSES:
            findings.append(f"{label}.status must be one of {sorted(STATUSES)}")
        for field in ("depends_on", "inputs", "outputs", "required_capabilities", "stop_when", "reopen_on"):
            if not isinstance(node.get(field), list): findings.append(f"{label}.{field} must be a list")
    duplicates = sorted({x for x in ids if ids.count(x) > 1})
    if duplicates: findings.append(f"node ids must be unique: {duplicates}")
    known = set(ids)
    for node in nodes:
        if not isinstance(node, dict): continue
        for dep in node.get("depends_on", []):
            if dep not in known: findings.append(f"node {node.get('id')} depends on unknown node {dep}")
    for index, edge in enumerate(edges):
        label = f"edges[{index}]"
        if not isinstance(edge, dict): findings.append(f"{label} must be an object"); continue
        if edge.get("from") not in known: findings.append(f"{label}.from is unknown")
        if edge.get("to") not in known and edge.get("to") != "evidence_ledger": findings.append(f"{label}.to is unknown")
        if not isinstance(edge.get("kind"), str) or not isinstance(edge.get("condition"), str): findings.append(f"{label} requires kind and condition")
    if not isinstance(graph.get("events"), list): findings.append("events must be a list")
    return {"status": "PASS" if not findings else "FAIL", "findings": findings, "node_count": len(nodes), "edge_count": len(edges)}


def load_graph(project: Path) -> tuple[Path, dict[str, Any]]:
    state = _state_dir(project); path = state / "research_graph.json"
    if not path.exists(): raise GraphError(f"research graph not found: {path}")
    return path, _read(path)


def status_graph(project: Path) -> dict[str, Any]:
    path, graph = load_graph(project); check = validate_graph(graph)
    nodes = [{"id": n.get("id"), "kind": n.get("kind"), "status": n.get("status")} for n in graph.get("nodes", []) if isinstance(n, dict)]
    return {"operation": "status", "status": check["status"], "state_dir": str(path.parent), "nodes": nodes, "events": len(graph.get("events", [])), "findings": check["findings"]}


def transition(project: Path, node_id: str, new_status: str, reason: str, actor: str, evidence: str | None) -> dict[str, Any]:
    if new_status not in STATUSES: raise GraphError(f"invalid status: {new_status}")
    path, graph = load_graph(project); check = validate_graph(graph)
    if check["status"] == "FAIL": raise GraphError("graph validation failed: " + "; ".join(check["findings"]))
    node = next((n for n in graph["nodes"] if isinstance(n, dict) and n.get("id") == node_id), None)
    if node is None: raise GraphError(f"unknown node: {node_id}")
    old_status = node.get("status")
    if old_status == new_status: raise GraphError(f"node {node_id} is already {new_status}")
    if new_status == "PASS" and not evidence: raise GraphError("PASS requires --evidence anchor")
    if new_status in {"RUNNING", "PASS", "CONDITIONAL"}:
        missing = [dep for dep in node.get("depends_on", []) if next((x for x in graph["nodes"] if x.get("id") == dep), {}).get("status") not in {"PASS", "CONDITIONAL"}]
        if missing: raise GraphError(f"node {node_id} dependencies are not complete: {missing}")
    node["status"] = new_status
    event = {"event_id": f"GE-{len(graph.get('events', [])) + 1:04d}", "utc": _now(), "actor": actor, "node": node_id, "from": old_status, "to": new_status, "reason": reason, "evidence": evidence}
    graph.setdefault("events", []).append(event)
    _write(path, graph)
    return {"operation": "transition", "status": "PASS", "node": node_id, "from": old_status, "to": new_status, "event": event, "state_dir": str(path.parent)}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); subs = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("validate", "validate graph structure"), ("status", "show graph status")):
        p = subs.add_parser(name, help=help_text); p.add_argument("project", type=Path)
    p = subs.add_parser("transition", help="append a graph transition"); p.add_argument("project", type=Path); p.add_argument("--node", required=True); p.add_argument("--status", required=True); p.add_argument("--reason", required=True); p.add_argument("--actor", default="ceo"); p.add_argument("--evidence")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate":
            _, graph = load_graph(args.project); result = validate_graph(graph); result.update({"operation": "validate"})
        elif args.command == "status": result = status_graph(args.project)
        else: result = transition(args.project, args.node, args.status, args.reason, args.actor, args.evidence)
    except GraphError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False)); return 2
    print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__": sys.exit(main())
