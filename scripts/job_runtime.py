#!/usr/bin/env python3
"""Recoverable long-job manifest/checkpoint runtime (stdlib only)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def init(path: Path, command: str, outputs: list[str], retries: int = 2) -> dict[str, Any]:
    value = {"schema_version": 1, "skill_version": "3.1.0", "job_id": path.stem, "command": command, "status": "READY", "created_utc": _now(), "checkpoints": [], "outputs": outputs, "bounded_retries": retries, "partial_output_quarantine": True, "completion": None}
    _write(path, value); return {"operation": "init", "status": "PASS", "manifest": str(path), "job_id": value["job_id"]}


def checkpoint(path: Path, label: str, progress: float, artifacts: list[str]) -> dict[str, Any]:
    value = _read(path)
    if value.get("status") not in {"READY", "RUNNING", "PAUSED"}:
        return {"operation": "checkpoint", "status": "FAIL", "findings": [f"cannot checkpoint job in {value.get('status')}"]}
    value["status"] = "RUNNING"; record = {"label": label, "progress": max(0, min(progress, 1)), "artifacts": artifacts, "utc": _now(), "artifact_hashes": {item: "sha256:" + hashlib.sha256(Path(item).read_bytes()).hexdigest() for item in artifacts if Path(item).is_file()}}
    value.setdefault("checkpoints", []).append(record); _write(path, value); return {"operation": "checkpoint", "status": "PASS", "checkpoint": record}


def resume(path: Path) -> dict[str, Any]:
    value = _read(path)
    if value.get("status") not in {"RUNNING", "PAUSED"}:
        return {"operation": "resume", "status": "FAIL", "findings": ["job has no resumable running state"]}
    return {"operation": "resume", "status": "READY", "job_id": value.get("job_id"), "command": value.get("command"), "last_checkpoint": value.get("checkpoints", [])[-1] if value.get("checkpoints") else None}


def complete(path: Path, exit_status: int, known_warnings: list[str] | None = None) -> dict[str, Any]:
    value = _read(path); outputs = value.get("outputs", []); missing = [item for item in outputs if not Path(item).exists()]
    if exit_status != 0 or missing:
        value["status"] = "FAILED"; _write(path, value); return {"operation": "complete", "status": "FAIL", "exit_status": exit_status, "missing_outputs": missing, "partial_outputs_quarantined": bool(missing)}
    output_hashes = {item: "sha256:" + hashlib.sha256(Path(item).read_bytes()).hexdigest() for item in outputs if Path(item).is_file()}
    value.update({"status": "VERIFIED", "completion": {"exit_status": exit_status, "output_hashes": output_hashes, "known_warnings": known_warnings or [], "verified_utc": _now()}}); _write(path, value); return {"operation": "complete", "status": "VERIFIED", "completion": value["completion"]}


def status(path: Path) -> dict[str, Any]:
    value = _read(path); return {"operation": "status", "status": value.get("status"), "job_id": value.get("job_id"), "progress": value.get("checkpoints", [])[-1].get("progress", 0) if value.get("checkpoints") else 0, "checkpoints": len(value.get("checkpoints", [])), "completion": value.get("completion")}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init"); p.add_argument("manifest", type=Path); p.add_argument("--command", required=True); p.add_argument("--output", action="append", default=[]); p.add_argument("--retries", type=int, default=2)
    p = sub.add_parser("checkpoint"); p.add_argument("manifest", type=Path); p.add_argument("--label", required=True); p.add_argument("--progress", type=float, required=True); p.add_argument("--artifact", action="append", default=[])
    p = sub.add_parser("resume"); p.add_argument("manifest", type=Path)
    p = sub.add_parser("complete"); p.add_argument("manifest", type=Path); p.add_argument("--exit-status", type=int, required=True); p.add_argument("--warning", action="append", default=[])
    p = sub.add_parser("status"); p.add_argument("manifest", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "init": result = init(args.manifest, args.command, args.output, args.retries)
    elif args.command == "checkpoint": result = checkpoint(args.manifest, args.label, args.progress, args.artifact)
    elif args.command == "resume": result = resume(args.manifest)
    elif args.command == "complete": result = complete(args.manifest, args.exit_status, args.warning)
    else: result = status(args.manifest)
    print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result.get("status") in {"PASS", "READY", "VERIFIED", "RUNNING", "PAUSED"} else 1


if __name__ == "__main__": sys.exit(main())
