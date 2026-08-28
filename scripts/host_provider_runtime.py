#!/usr/bin/env python3
"""Persist host requests, validate external handoffs, and resume checker-gated work."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import py_compile
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_VERSION = "3.2.0"
STATES = {
    "REQUEST_CREATED",
    "HOST_EXECUTION_REQUIRED",
    "HOST_HANDOFF_RECEIVED",
    "CHECKING",
    "ACCEPTED",
    "REJECTED",
}
REQUEST_FIELDS = {
    "task_id",
    "node",
    "capability",
    "formal",
    "inputs",
    "constraints",
    "required_outputs",
    "evidence_requirements",
    "forbidden_claims",
    "permissions",
    "budget",
}
HANDOFF_FIELDS = {
    "task_id",
    "provider_id",
    "status",
    "artifacts",
    "claims",
    "uncertainties",
    "actions_taken",
    "tool_calls",
    "commands",
    "checker_notes",
}
CODE_FIELDS = {
    "changed_files",
    "entrypoint",
    "config",
    "tests",
    "commands",
    "expected_outputs",
    "limitations",
}


class HostProviderError(RuntimeError):
    """Raised when persisted host lifecycle state cannot be trusted."""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _state_dir(project: Path) -> Path:
    root = project.resolve()
    for name in (".research-state-v31", ".research-state-v3", ".research-state"):
        candidate = root / name
        if candidate.exists():
            return candidate
    return root / ".research-state"


def _root(project: Path) -> Path:
    return _state_dir(project) / "host_provider"


def _key(task_id: str) -> str:
    slug = "".join(char if char.isalnum() or char in "-_." else "-" for char in task_id).strip("-.")
    digest = hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:12]
    return f"{slug[:48] or 'task'}-{digest}"


def _record_path(project: Path, task_id: str) -> Path:
    return _root(project) / "requests" / f"{_key(task_id)}.json"


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _transition(record: dict[str, Any], state: str) -> None:
    if state not in STATES:
        raise HostProviderError(f"unknown host provider state: {state}")
    if not record.get("lifecycle") or record["lifecycle"][-1] != state:
        record.setdefault("lifecycle", []).append(state)
    record["state"] = state
    record["updated_utc"] = _now()


def validate_request(value: Any) -> dict[str, Any]:
    findings: list[str] = []
    if not isinstance(value, dict):
        return {"status": "FAIL", "findings": ["host request must be an object"]}
    missing = sorted(REQUEST_FIELDS - set(value))
    if missing:
        findings.append("missing request fields: " + ", ".join(missing))
    for field in ("task_id", "node", "capability"):
        if field in value and not str(value.get(field, "")).strip():
            findings.append(f"{field} must be non-empty")
    for field in ("inputs", "constraints", "required_outputs", "evidence_requirements", "forbidden_claims"):
        if field in value and not isinstance(value.get(field), list):
            findings.append(f"{field} must be a list")
    if "permissions" in value and not isinstance(value.get("permissions"), dict):
        findings.append("permissions must be an object")
    if "budget" in value and not isinstance(value.get("budget"), dict):
        findings.append("budget must be an object")
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def create_request(project: Path, value: dict[str, Any]) -> dict[str, Any]:
    """Create only a request; no host artifact or handoff is synthesized here."""
    project = project.resolve()
    check = validate_request(value)
    if check["status"] != "PASS":
        return {"operation": "host-request", "status": "REJECTED", "findings": check["findings"]}
    task_id = str(value["task_id"])
    path = _record_path(project, task_id)
    existing = _read(path)
    if isinstance(existing, dict):
        if existing.get("request") == value:
            return _public(existing, path, created=False)
        return {
            "operation": "host-request",
            "status": "REJECTED",
            "state": "REJECTED",
            "findings": ["task_id already exists with a different request contract"],
            "task_id": task_id,
        }
    record = {
        "schema_version": 1,
        "skill_version": SKILL_VERSION,
        "task_id": task_id,
        "node": value["node"],
        "capability": value["capability"],
        "request": value,
        "handoff": None,
        "checker": None,
        "artifact_hashes": {},
        "lifecycle": [],
        "created_utc": _now(),
    }
    _transition(record, "REQUEST_CREATED")
    _transition(record, "HOST_EXECUTION_REQUIRED")
    _write(path, record)
    return _public(record, path, created=True)


def _public(record: dict[str, Any], path: Path, *, created: bool | None = None) -> dict[str, Any]:
    state = str(record.get("state", "HOST_EXECUTION_REQUIRED"))
    status = "ACCEPTED" if state == "ACCEPTED" else "REJECTED" if state == "REJECTED" else "HOST_EXECUTION_REQUIRED"
    output = {
        "operation": "host-provider-lifecycle",
        "status": status,
        "state": state,
        "task_id": record.get("task_id"),
        "node": record.get("node"),
        "capability": record.get("capability"),
        "request_path": str(path),
        "lifecycle": list(record.get("lifecycle", [])),
        "host_request_created": True,
    }
    if created is not None:
        output["created"] = created
    if state in {"HOST_HANDOFF_RECEIVED", "CHECKING", "ACCEPTED", "REJECTED"}:
        output["host_handoff_received"] = bool(record.get("handoff"))
    if record.get("checker"):
        output["checker"] = record["checker"]
    if record.get("handoff"):
        output["handoff"] = record["handoff"]
    return output


def _records(project: Path) -> list[tuple[Path, dict[str, Any]]]:
    folder = _root(project.resolve()) / "requests"
    output = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        value = _read(path)
        if isinstance(value, dict):
            output.append((path, value))
    return output


def pending(project: Path) -> dict[str, Any]:
    requests = [
        _public(record, path)
        for path, record in _records(project)
        if record.get("state") in {"REQUEST_CREATED", "HOST_EXECUTION_REQUIRED", "HOST_HANDOFF_RECEIVED", "CHECKING"}
    ]
    return {
        "operation": "host-provider-pending",
        "status": "HOST_EXECUTION_REQUIRED" if requests else "PASS",
        "requests": requests,
    }


def receive(project: Path, value: dict[str, Any] | Path) -> dict[str, Any]:
    project = project.resolve()
    handoff = _read(value) if isinstance(value, Path) else value
    if not isinstance(handoff, dict) or not str(handoff.get("task_id", "")).strip():
        return {"operation": "host-handoff-receive", "status": "REJECTED", "state": "REJECTED", "findings": ["handoff task_id is required"]}
    task_id = str(handoff["task_id"])
    path = _record_path(project, task_id)
    record = _read(path)
    if not isinstance(record, dict):
        return {"operation": "host-handoff-receive", "status": "REJECTED", "state": "REJECTED", "findings": ["no matching host request"]}
    if record.get("state") not in {"HOST_EXECUTION_REQUIRED", "HOST_HANDOFF_RECEIVED", "REJECTED"}:
        return {"operation": "host-handoff-receive", "status": "REJECTED", "state": "REJECTED", "findings": [f"request is not awaiting a handoff: {record.get('state')}"]}
    if record.get("state") == "REJECTED":
        record["checker"] = None
        record["artifact_hashes"] = {}
        record.pop("qualification", None)
        record.pop("reopened_downstream", None)
    record["handoff"] = handoff
    record["handoff_received_utc"] = _now()
    _transition(record, "HOST_HANDOFF_RECEIVED")
    _write(path, record)
    output = _public(record, path)
    output["operation"] = "host-handoff-receive"
    return output


def _artifact(project: Path, relative: Any) -> tuple[Path | None, str | None]:
    path = (project / str(relative)).resolve()
    try:
        path.relative_to(project.resolve())
    except ValueError:
        return None, f"artifact escapes project: {relative}"
    if not path.is_file() or path.stat().st_size == 0:
        return None, f"artifact is missing or empty: {relative}"
    return path, None


def _host_findings(project: Path, record: dict[str, Any], checker_id: str) -> tuple[list[str], dict[str, str]]:
    handoff = record.get("handoff")
    findings: list[str] = []
    hashes: dict[str, str] = {}
    if not isinstance(handoff, dict):
        return ["host handoff has not been received"], hashes
    missing = sorted(HANDOFF_FIELDS - set(handoff))
    if missing:
        findings.append("missing handoff fields: " + ", ".join(missing))
    if handoff.get("task_id") != record.get("task_id"):
        findings.append("handoff task_id does not match request")
    if handoff.get("status") != "PASS":
        findings.append("host handoff status is not PASS")
    provider_id = str(handoff.get("provider_id", ""))
    if not provider_id:
        findings.append("provider_id is required")
    if provider_id == checker_id or provider_id.split(":", 1)[0] == checker_id.split(":", 1)[0]:
        findings.append("host producer cannot certify its own output")
    artifacts = handoff.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        findings.append("host handoff must contain observed artifacts")
    else:
        for relative in artifacts:
            path, error = _artifact(project, relative)
            if error:
                findings.append(error)
            elif path is not None:
                hashes[str(relative)] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    for field in ("claims", "uncertainties", "actions_taken", "tool_calls", "commands", "checker_notes"):
        if field in handoff and not isinstance(handoff.get(field), list):
            findings.append(f"{field} must be a list")
    if not handoff.get("actions_taken"):
        findings.append("actions_taken must record real host work")
    if not handoff.get("checker_notes"):
        findings.append("checker_notes are required")
    capability = str(record.get("capability", ""))
    if any(token in capability for token in ("code", "implementation", "software")):
        missing_code = sorted(CODE_FIELDS - set(handoff))
        if missing_code:
            findings.append("code handoff missing fields: " + ", ".join(missing_code))
        if not handoff.get("commands"):
            findings.append("code handoff must declare deterministic execution commands")
        if not handoff.get("entrypoint"):
            findings.append("code handoff must identify an entrypoint")
        else:
            entrypoint, entrypoint_error = _artifact(project, handoff.get("entrypoint"))
            if entrypoint_error:
                findings.append(entrypoint_error)
            elif entrypoint is not None and entrypoint.suffix.casefold() == ".py":
                try:
                    py_compile.compile(str(entrypoint), doraise=True)
                except py_compile.PyCompileError as exc:
                    findings.append(f"entrypoint syntax check failed: {exc}")
        changed = handoff.get("changed_files", [])
        if not isinstance(changed, list) or not changed:
            findings.append("code handoff must list changed_files")
        elif not set(map(str, changed)).issubset(set(map(str, artifacts or []))):
            findings.append("changed_files must be present in artifacts")
    return findings, hashes


def _load_research_graph():
    path = Path(__file__).with_name("research_graph.py")
    spec = importlib.util.spec_from_file_location("host_provider_research_graph", path)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise HostProviderError(f"cannot load {path}")
    spec.loader.exec_module(module)
    return module


def invalidate_downstream(project: Path, changed_node: str, *, actor: str = "host-provider-runtime") -> list[str]:
    """Reopen completed dependency descendants after an accepted host artifact changes."""
    try:
        graph_runtime = _load_research_graph()
        _, graph = graph_runtime.load_graph(project)
    except Exception:
        return []
    nodes = {item.get("id"): item for item in graph.get("nodes", []) if isinstance(item, dict)}
    affected: list[str] = []
    frontier = {changed_node}
    while frontier:
        next_frontier: set[str] = set()
        for node_id, node in nodes.items():
            if node_id == changed_node or node_id in affected:
                continue
            dependencies = set(node.get("depends_on", node.get("dependencies", [])))
            if dependencies & frontier:
                affected.append(str(node_id))
                next_frontier.add(str(node_id))
        frontier = next_frontier
    reopened = []
    for node_id in affected:
        if nodes[node_id].get("status") in {"PASS", "CONDITIONAL"}:
            try:
                graph_runtime.transition(project, node_id, "REOPENED", f"accepted host artifact changed upstream node {changed_node}", actor, None)
                reopened.append(node_id)
            except Exception:
                continue
    return reopened


def check(project: Path, task_id: str, *, checker_id: str) -> dict[str, Any]:
    project = project.resolve()
    path = _record_path(project, task_id)
    record = _read(path)
    if not isinstance(record, dict):
        return {"operation": "host-handoff-check", "status": "REJECTED", "state": "REJECTED", "findings": ["host request is missing"]}
    if record.get("state") != "HOST_HANDOFF_RECEIVED":
        output = _public(record, path)
        output["operation"] = "host-handoff-check"
        output["findings"] = ["host handoff has not reached HOST_HANDOFF_RECEIVED"]
        return output
    _transition(record, "CHECKING")
    findings, hashes = _host_findings(project, record, checker_id)
    checker = {
        "checker_id": checker_id,
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
        "artifact_hashes": hashes,
        "independence": "INDEPENDENT",
        "checked_utc": _now(),
    }
    record["checker"] = checker
    record["artifact_hashes"] = hashes
    _transition(record, "ACCEPTED" if not findings else "REJECTED")
    if not findings:
        record["qualification"] = "REQUEST_CHECKED"
        record["reopened_downstream"] = invalidate_downstream(project, str(record.get("node", "")))
    _write(path, record)
    if not findings:
        _write(_root(project) / "accepted" / f"{_key(task_id)}.json", record)
    output = _public(record, path)
    output["operation"] = "host-handoff-check"
    output["findings"] = findings
    output["artifact_hashes"] = hashes
    output["status"] = "ACCEPTED" if not findings else "REJECTED"
    return output


def resolve(project: Path, task_id: str) -> dict[str, Any]:
    path = _record_path(project.resolve(), task_id)
    record = _read(path)
    if not isinstance(record, dict):
        return {"operation": "host-provider-resolve", "status": "UNAVAILABLE", "task_id": task_id}
    output = _public(record, path)
    output["operation"] = "host-provider-resolve"
    return output


def accepted_handoff(project: Path, task_id: str) -> dict[str, Any] | None:
    result = resolve(project, task_id)
    if result.get("status") != "ACCEPTED":
        return None
    handoff = result.get("handoff")
    return handoff if isinstance(handoff, dict) else None


def active_for_node(project: Path, node: str) -> dict[str, Any] | None:
    matching = [
        _public(record, path)
        for path, record in _records(project)
        if record.get("node") == node and record.get("state") not in {"REJECTED"}
    ]
    return matching[-1] if matching else None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("pending")
    command.add_argument("project", type=Path)
    command = sub.add_parser("receive")
    command.add_argument("project", type=Path)
    command.add_argument("handoff", type=Path)
    command.add_argument("--checker", default="deterministic-output-checker")
    command = sub.add_parser("check")
    command.add_argument("project", type=Path)
    command.add_argument("task_id")
    command.add_argument("--checker", default="deterministic-output-checker")
    command = sub.add_parser("show")
    command.add_argument("project", type=Path)
    command.add_argument("task_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "pending":
        result = pending(args.project)
    elif args.command == "receive":
        received = receive(args.project, args.handoff)
        result = check(args.project, str((_read(args.handoff) or {}).get("task_id", "")), checker_id=args.checker) if received.get("state") == "HOST_HANDOFF_RECEIVED" else received
    elif args.command == "check":
        result = check(args.project, args.task_id, checker_id=args.checker)
    else:
        result = resolve(args.project, args.task_id)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") in {"PASS", "ACCEPTED", "HOST_EXECUTION_REQUIRED"} else 1


if __name__ == "__main__":
    sys.exit(main())
