"""Shared project-local primitives for production providers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def state_dir(project: Path) -> Path:
    root = project.resolve()
    for name in (".research-state-v31", ".research-state-v3", ".research-state"):
        candidate = root / name
        if candidate.exists():
            return candidate
    return root / ".research-state"


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8", newline="\n")
    else:
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def relative(project: Path, path: Path) -> str:
    return path.resolve().relative_to(project.resolve()).as_posix()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def handoff(
    project: Path,
    provider_id: str,
    node: str,
    artifacts: list[Path],
    *,
    formal: bool = False,
    actions: list[str] | None = None,
    claims: list[dict[str, Any]] | None = None,
    uncertainties: list[str] | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value = {
        "status": "PASS",
        "provider_id": provider_id,
        "provider_version": "3.2.0",
        "node": node,
        "formal": formal,
        "artifacts": [relative(project, path) for path in artifacts],
        "claims": claims or [],
        "uncertainties": uncertainties or [],
        "actions_taken": actions or [],
        "tool_calls": tool_calls or [],
        "handoff": {"resume": "deterministic-runtime", "checker_required": True},
    }
    value.update(extra or {})
    return value
