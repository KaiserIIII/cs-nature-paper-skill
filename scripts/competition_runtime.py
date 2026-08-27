#!/usr/bin/env python3
"""Run deterministic CUMCM clock and competition policy operations."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SKILL_VERSION = "3.1.1"
ROOT = Path(__file__).resolve().parents[1]
CLOCK_TEMPLATE = ROOT / "assets" / "templates" / "competition" / "competition_clock.json"
CLOCK_EVENT_LOG = ".competition-clock-events.jsonl"


class CompetitionError(RuntimeError):
    """Raised when competition state cannot be trusted or updated."""


def _system_now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_now(value: datetime | None) -> datetime:
    current = value if value is not None else _system_now_utc()
    if current.tzinfo is None or current.utcoffset() is None:
        raise CompetitionError("current time must include a timezone")
    return current.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise CompetitionError("timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise CompetitionError(f"invalid ISO-8601 timestamp: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CompetitionError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _state_dir(project: Path) -> Path:
    project = project.resolve()
    for name in (".research-state-v31", ".research-state-v3", ".research-state"):
        candidate = project / name
        if candidate.exists():
            return candidate
    raise CompetitionError(f"research state not found under: {project}")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise CompetitionError(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CompetitionError(f"JSON root must be an object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def _event_hash(event: dict[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return "sha256:" + hashlib.sha256(_canonical(payload)).hexdigest()


def _load_and_verify_events(state_dir: Path) -> list[dict[str, Any]]:
    path = state_dir / CLOCK_EVENT_LOG
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CompetitionError(
                f"invalid clock event {line_number} in {path}"
            ) from exc
        if not isinstance(event, dict):
            raise CompetitionError(f"clock event {line_number} must be an object")
        events.append(event)

    predecessor = "GENESIS"
    for index, event in enumerate(events, start=1):
        expected_id = f"CE-{index:04d}"
        if event.get("event_id") != expected_id:
            raise CompetitionError(f"clock event {index} expected event_id {expected_id}")
        if event.get("predecessor_hash") != predecessor:
            raise CompetitionError(f"clock event {index} predecessor hash mismatch")
        expected_hash = _event_hash(event)
        if event.get("event_hash") != expected_hash:
            raise CompetitionError(f"clock event {index} hash mismatch")
        predecessor = expected_hash
    return events


def _append_clock_event(
    state_dir: Path,
    operation: str,
    actor: str,
    reason: str,
    old_value: Any,
    new_value: Any,
    now: datetime,
) -> dict[str, Any]:
    events = _load_and_verify_events(state_dir)
    event = {
        "event_id": f"CE-{len(events) + 1:04d}",
        "utc": _format_utc(now),
        "actor": actor,
        "operation": operation,
        "reason": reason,
        "old_value": old_value,
        "new_value": new_value,
        "predecessor_hash": events[-1]["event_hash"] if events else "GENESIS",
    }
    event["event_hash"] = _event_hash(event)
    with (state_dir / CLOCK_EVENT_LOG).open(
        "a", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def _base_clock(state_dir: Path) -> dict[str, Any]:
    value = _read_json(CLOCK_TEMPLATE)
    existing_path = state_dir / "competition_clock.json"
    if existing_path.exists():
        existing = _read_json(existing_path)
        value["created_utc"] = existing.get("created_utc", value.get("created_utc", ""))
    return value


def _replay_clock(state_dir: Path, events: list[dict[str, Any]]) -> dict[str, Any]:
    clock = _base_clock(state_dir)
    for event in events:
        operation = event.get("operation")
        new_value = event.get("new_value")
        if operation == "CONFIGURE_CLOCK" and isinstance(new_value, dict):
            clock.update(
                {
                    "contest_start_utc": new_value.get("contest_start_utc", ""),
                    "submission_deadline_utc": new_value.get(
                        "submission_deadline_utc", ""
                    ),
                    "official_source": new_value.get("official_source", ""),
                    "source_verified_utc": "",
                    "manual_time_offset_seconds": 0,
                    "paused_effective_now_utc": None,
                }
            )
        elif operation == "VERIFY_CLOCK" and isinstance(new_value, dict):
            clock["official_source"] = new_value.get("official_source", "")
            clock["source_verified_utc"] = new_value.get("source_verified_utc", "")
        elif operation == "ADJUST_CLOCK" and isinstance(new_value, dict):
            clock["manual_time_offset_seconds"] = int(
                new_value.get("manual_time_offset_seconds", 0)
            )
            clock["manual_override_reason"] = event.get("reason", "")
            clock["manual_override_actor"] = event.get("actor", "")
            clock["manual_override_utc"] = event.get("utc", "")
        elif operation == "PAUSE_CLOCK" and isinstance(new_value, dict):
            clock["paused_effective_now_utc"] = new_value.get(
                "paused_effective_now_utc"
            )
            clock["manual_override_reason"] = event.get("reason", "")
            clock["manual_override_actor"] = event.get("actor", "")
            clock["manual_override_utc"] = event.get("utc", "")
        elif operation == "RESUME_CLOCK" and isinstance(new_value, dict):
            clock["manual_time_offset_seconds"] = int(
                new_value.get("manual_time_offset_seconds", 0)
            )
            clock["paused_effective_now_utc"] = None
            clock["manual_override_reason"] = event.get("reason", "")
            clock["manual_override_actor"] = event.get("actor", "")
            clock["manual_override_utc"] = event.get("utc", "")
    return clock


def _configured_clock(state_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    events = _load_and_verify_events(state_dir)
    clock = _replay_clock(state_dir, events)
    if not clock.get("contest_start_utc") or not clock.get("submission_deadline_utc"):
        raise CompetitionError("competition clock is not configured")
    return clock, events


def refresh_clock(
    project: Path, now_utc: datetime | None = None
) -> dict[str, Any]:
    state_dir = _state_dir(project)
    current = _normalize_now(now_utc)
    events = _load_and_verify_events(state_dir)
    clock = _replay_clock(state_dir, events)
    clock_path = state_dir / "competition_clock.json"

    if not clock.get("contest_start_utc") or not clock.get("submission_deadline_utc"):
        clock.update(
            {
                "clock_status": "UNVERIFIED",
                "last_checked_utc": _format_utc(current),
                "authoritative_deadline": False,
            }
        )
        _write_json(clock_path, clock)
        return {
            "operation": "refresh-clock",
            "status": "CONDITIONAL",
            "clock": clock,
            "state_dir": str(state_dir),
        }

    start = parse_utc(clock["contest_start_utc"])
    deadline = parse_utc(clock["submission_deadline_utc"])
    duration = int((deadline - start).total_seconds())
    if duration <= 0:
        raise CompetitionError("submission deadline must be after contest start")

    paused = clock.get("paused_effective_now_utc")
    if paused:
        effective_now = parse_utc(paused)
    else:
        effective_now = current + timedelta(
            seconds=int(clock.get("manual_time_offset_seconds", 0))
        )
    elapsed = int((effective_now - start).total_seconds())
    remaining = int((deadline - effective_now).total_seconds())
    authoritative = bool(
        str(clock.get("official_source", "")).strip()
        and str(clock.get("source_verified_utc", "")).strip()
    )
    if not authoritative:
        lifecycle = "UNVERIFIED"
    elif paused:
        lifecycle = "PAUSED"
    elif effective_now < start:
        lifecycle = "SCHEDULED"
    elif effective_now >= deadline:
        lifecycle = "EXPIRED"
    else:
        lifecycle = "ACTIVE"

    clock.update(
        {
            "contest_duration_seconds": duration,
            "clock_status": lifecycle,
            "last_checked_utc": _format_utc(current),
            "effective_now_utc": _format_utc(effective_now),
            "elapsed_seconds": elapsed,
            "remaining_seconds": remaining,
            "elapsed_ratio": elapsed / duration,
            "authoritative_deadline": authoritative,
        }
    )
    _write_json(clock_path, clock)
    return {
        "operation": "refresh-clock",
        "status": "PASS" if authoritative else "CONDITIONAL",
        "clock": clock,
        "state_dir": str(state_dir),
    }


def configure_clock(
    project: Path,
    start: str,
    deadline: str,
    official_source: str,
    actor: str,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    if not str(actor).strip():
        raise CompetitionError("clock configuration actor is required")
    start_utc = parse_utc(start)
    deadline_utc = parse_utc(deadline)
    if deadline_utc <= start_utc:
        raise CompetitionError("submission deadline must be after contest start")
    state_dir = _state_dir(project)
    current = _normalize_now(now_utc)
    existing = _read_json(state_dir / "competition_clock.json")
    new_value = {
        "contest_start_utc": _format_utc(start_utc),
        "submission_deadline_utc": _format_utc(deadline_utc),
        "official_source": str(official_source).strip(),
    }
    _append_clock_event(
        state_dir,
        "CONFIGURE_CLOCK",
        str(actor).strip(),
        "configure authoritative time boundaries; source remains unverified",
        {
            "contest_start_utc": existing.get("contest_start_utc", ""),
            "submission_deadline_utc": existing.get("submission_deadline_utc", ""),
            "official_source": existing.get("official_source", ""),
        },
        new_value,
        current,
    )
    result = refresh_clock(project, now_utc=current)
    result["operation"] = "configure-clock"
    return result


def verify_clock(
    project: Path,
    official_source: str,
    actor: str,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    source = str(official_source).strip()
    verifier = str(actor).strip()
    if not source:
        raise CompetitionError("official source is required for clock verification")
    if not verifier:
        raise CompetitionError("clock verification actor is required")
    state_dir = _state_dir(project)
    clock, _ = _configured_clock(state_dir)
    current = _normalize_now(now_utc)
    new_value = {
        "official_source": source,
        "source_verified_utc": _format_utc(current),
    }
    _append_clock_event(
        state_dir,
        "VERIFY_CLOCK",
        verifier,
        "verify competition time against an explicit official source",
        {
            "official_source": clock.get("official_source", ""),
            "source_verified_utc": clock.get("source_verified_utc", ""),
        },
        new_value,
        current,
    )
    result = refresh_clock(project, now_utc=current)
    result["operation"] = "verify-clock"
    return result


def adjust_clock(
    project: Path,
    offset_seconds: int,
    reason: str,
    actor: str,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    if isinstance(offset_seconds, bool) or not isinstance(offset_seconds, int):
        raise CompetitionError("manual time offset must be an integer number of seconds")
    if not str(reason).strip() or not str(actor).strip():
        raise CompetitionError("manual clock adjustment requires reason and actor")
    state_dir = _state_dir(project)
    clock, _ = _configured_clock(state_dir)
    current = _normalize_now(now_utc)
    _append_clock_event(
        state_dir,
        "ADJUST_CLOCK",
        str(actor).strip(),
        str(reason).strip(),
        {"manual_time_offset_seconds": clock.get("manual_time_offset_seconds", 0)},
        {"manual_time_offset_seconds": offset_seconds},
        current,
    )
    result = refresh_clock(project, now_utc=current)
    result["operation"] = "adjust-clock"
    return result


def pause_clock(
    project: Path,
    reason: str,
    actor: str,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    if not str(reason).strip() or not str(actor).strip():
        raise CompetitionError("clock pause requires reason and actor")
    current = _normalize_now(now_utc)
    refreshed = refresh_clock(project, now_utc=current)["clock"]
    if not refreshed.get("authoritative_deadline"):
        raise CompetitionError("cannot pause an unverified competition clock")
    if refreshed.get("paused_effective_now_utc"):
        raise CompetitionError("competition clock is already paused")
    state_dir = _state_dir(project)
    _append_clock_event(
        state_dir,
        "PAUSE_CLOCK",
        str(actor).strip(),
        str(reason).strip(),
        {"paused_effective_now_utc": None},
        {"paused_effective_now_utc": refreshed["effective_now_utc"]},
        current,
    )
    result = refresh_clock(project, now_utc=current)
    result["operation"] = "pause-clock"
    return result


def resume_clock(
    project: Path,
    reason: str,
    actor: str,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    if not str(reason).strip() or not str(actor).strip():
        raise CompetitionError("clock resume requires reason and actor")
    current = _normalize_now(now_utc)
    state_dir = _state_dir(project)
    clock, _ = _configured_clock(state_dir)
    paused_value = clock.get("paused_effective_now_utc")
    if not paused_value:
        raise CompetitionError("competition clock is not paused")
    paused_effective = parse_utc(str(paused_value))
    new_offset = int((paused_effective - current).total_seconds())
    _append_clock_event(
        state_dir,
        "RESUME_CLOCK",
        str(actor).strip(),
        str(reason).strip(),
        {
            "manual_time_offset_seconds": clock.get("manual_time_offset_seconds", 0),
            "paused_effective_now_utc": paused_value,
        },
        {
            "manual_time_offset_seconds": new_offset,
            "paused_effective_now_utc": None,
        },
        current,
    )
    result = refresh_clock(project, now_utc=current)
    result["operation"] = "resume-clock"
    return result


def validate_clock(project: Path) -> dict[str, Any]:
    try:
        state_dir = _state_dir(project)
        clock, events = _configured_clock(state_dir)
        parse_utc(clock["contest_start_utc"])
        parse_utc(clock["submission_deadline_utc"])
    except CompetitionError as exc:
        return {"operation": "validate-clock", "status": "FAIL", "findings": [str(exc)]}
    return {
        "operation": "validate-clock",
        "status": "PASS",
        "event_count": len(events),
        "findings": [],
        "state_dir": str(state_dir),
    }
