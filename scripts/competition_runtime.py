#!/usr/bin/env python3
"""Run deterministic CUMCM clock and competition policy operations."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SKILL_VERSION = "3.2.1"
ROOT = Path(__file__).resolve().parents[1]
CLOCK_TEMPLATE = ROOT / "assets" / "templates" / "competition" / "competition_clock.json"
CUMCM_PROFILE = ROOT / "assets" / "competition" / "cumcm_profile.json"
CLOCK_EVENT_LOG = ".competition-clock-events.jsonl"
QUESTION_FIELDS = (
    "id", "goal", "inputs", "decision_variables", "state_variables", "target",
    "constraints", "outputs", "required_evidence", "assumptions",
    "candidate_methods", "validation", "dependencies",
)
ASSUMPTION_FIELDS = (
    "id", "assumption", "reason", "consequence", "risk_if_violated",
    "validation_or_sensitivity", "affected_questions",
)
RULE_FIELDS = (
    "contest_time", "ai_policy", "file_format", "page_limit",
    "submission_method", "problem_count", "discipline",
)
SCRIPT_DIR = str(ROOT / "scripts")
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
import research_graph  # noqa: E402
import autonomy  # noqa: E402
import competition_executor  # noqa: E402
import competition_problem  # noqa: E402
import competition_quality  # noqa: E402
import director_loop  # noqa: E402
import host_provider_runtime  # noqa: E402


class CompetitionError(RuntimeError):
    """Raised when competition state cannot be trusted or updated."""


RUNTIME_OPERATION_ERRORS = (
    CompetitionError,
    research_graph.GraphError,
    OSError,
    json.JSONDecodeError,
    ValueError,
)


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
        "event_type": operation.removesuffix("_CLOCK"),
        "reason": reason,
        "old_value": old_value,
        "new_value": new_value,
        "before": old_value,
        "after": new_value,
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


def _load_profile() -> dict[str, Any]:
    return _read_json(CUMCM_PROFILE)


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
        elif operation == "OFFICIAL_EXTENSION" and isinstance(new_value, dict):
            clock["submission_deadline_utc"] = new_value.get(
                "submission_deadline_utc", clock.get("submission_deadline_utc", "")
            )
            clock["official_source"] = new_value.get(
                "official_source", clock.get("official_source", "")
            )
            clock["source_verified_utc"] = event.get("utc", "")
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
    if authoritative:
        profile = _load_profile()
        clock["current_phase"] = phase_for(clock, profile)
        clock["control_mode"] = control_mode_for(clock, profile)
        clock["stop_rule_active"] = clock["control_mode"] in {
            "FINALIZATION_MODE",
            "HARD_FREEZE",
        }
        clock["hard_freeze_active"] = clock["control_mode"] == "HARD_FREEZE"
    else:
        clock["current_phase"] = "UNVERIFIED"
        clock["control_mode"] = "UNVERIFIED"
        clock["stop_rule_active"] = False
        clock["hard_freeze_active"] = False
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


def official_extension(
    project: Path,
    deadline: str,
    official_source: str,
    reason: str,
    actor: str,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Append and apply a verified official deadline extension."""
    if not all(str(value).strip() for value in (official_source, reason, actor)):
        raise CompetitionError(
            "official extension requires official source, reason, and actor"
        )
    state_dir = _state_dir(project)
    clock, _ = _configured_clock(state_dir)
    new_deadline = parse_utc(deadline)
    old_deadline = parse_utc(str(clock["submission_deadline_utc"]))
    if new_deadline <= old_deadline:
        raise CompetitionError("official extension must move the deadline later")
    current = _normalize_now(now_utc)
    _append_clock_event(
        state_dir,
        "OFFICIAL_EXTENSION",
        str(actor).strip(),
        str(reason).strip(),
        {
            "submission_deadline_utc": clock["submission_deadline_utc"],
            "official_source": clock.get("official_source", ""),
        },
        {
            "submission_deadline_utc": _format_utc(new_deadline),
            "official_source": str(official_source).strip(),
        },
        current,
    )
    result = refresh_clock(project, now_utc=current)
    result["operation"] = "official-extension"
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


def validate_competition_state(value: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    if not isinstance(value, dict):
        return {
            "operation": "validate-competition-state",
            "status": "FAIL",
            "findings": ["competition state must be an object"],
        }
    for field in ("competition", "profile_id", "mode", "canonical_references"):
        if field not in value or value[field] in (None, ""):
            findings.append(f"competition_state.{field} is required")
    questions = value.get("question_decomposition")
    if not isinstance(questions, list):
        findings.append("competition_state.question_decomposition must be a list")
        questions = []
    for index, question in enumerate(questions):
        prefix = f"question_decomposition[{index}]"
        if not isinstance(question, dict):
            findings.append(f"{prefix} must be an object")
            continue
        findings.extend(
            f"{prefix}.{field} is required"
            for field in QUESTION_FIELDS
            if field not in question
        )
        for field in (
            "inputs", "decision_variables", "state_variables", "constraints",
            "outputs", "required_evidence", "assumptions", "candidate_methods",
            "validation", "dependencies",
        ):
            if field in question and not isinstance(question[field], list):
                findings.append(f"{prefix}.{field} must be a list")
        for field in ("id", "goal", "target"):
            if field in question and not str(question[field]).strip():
                findings.append(f"{prefix}.{field} must be non-empty")
        for field in (
            "inputs", "decision_variables", "constraints", "outputs",
            "required_evidence", "assumptions", "candidate_methods", "validation",
        ):
            if isinstance(question.get(field), list) and not question[field]:
                findings.append(f"{prefix}.{field} must be non-empty")

    assumptions = value.get("assumptions")
    if not isinstance(assumptions, list):
        findings.append("competition_state.assumptions must be a list")
        assumptions = []
    for index, assumption in enumerate(assumptions):
        prefix = f"assumptions[{index}]"
        if not isinstance(assumption, dict):
            findings.append(f"{prefix} must be an object")
            continue
        findings.extend(
            f"{prefix}.{field} is required"
            for field in ASSUMPTION_FIELDS
            if field not in assumption
        )
        for field in ASSUMPTION_FIELDS[:-1]:
            if field in assumption and not str(assumption[field]).strip():
                findings.append(f"{prefix}.{field} must be non-empty")
        affected = assumption.get("affected_questions")
        if "affected_questions" in assumption and (
            not isinstance(affected, list) or not affected
        ):
            findings.append(f"{prefix}.affected_questions must be a non-empty list")

    references = value.get("canonical_references")
    expected_references = {
        "graph": "research_graph.json",
        "claims": "claims.json",
        "evidence": "evidence_ledger.json",
        "experiments": "experiment_registry.json",
        "artifacts": "artifact_manifest.json",
        "handoff": "handoff.json",
    }
    if isinstance(references, dict):
        for key, expected in expected_references.items():
            if references.get(key) != expected:
                findings.append(
                    f"competition_state.canonical_references.{key} must be {expected}"
                )
    return {
        "operation": "validate-competition-state",
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
    }


def decompose_problems(problems: list[dict[str, Any]]) -> dict[str, Any]:
    return competition_problem.decompose(problems)


def select_problem(candidates: list[dict[str, Any]], *, close_margin: float = 0.05) -> dict[str, Any]:
    """Select a clearly dominant contest problem; ask only for a close/unknown choice."""
    if any(isinstance(item.get("decision_profile"), dict) for item in candidates):
        return competition_problem.select(candidates)
    fields = (
        "completion_risk", "data_risk", "model_risk", "paper_potential",
        "resource_risk", "expected_workload",
    )
    records: list[dict[str, Any]] = []
    for candidate in candidates:
        missing = [field for field in ("id",) + fields if field not in candidate]
        if missing:
            records.append(dict(candidate) | {"score": None, "missing": missing})
            continue
        score = (
            0.30 * float(candidate["paper_potential"])
            - 0.20 * float(candidate["completion_risk"])
            - 0.15 * float(candidate["data_risk"])
            - 0.15 * float(candidate["model_risk"])
            - 0.10 * float(candidate["resource_risk"])
            - 0.10 * float(candidate["expected_workload"])
        )
        records.append(dict(candidate) | {"score": round(score, 6), "missing": []})
    ranked = sorted(records, key=lambda item: (item["score"] is None, -(item["score"] or -999), str(item.get("id", ""))))
    if not ranked or ranked[0]["score"] is None:
        return {"operation": "competition-problem-selection", "status": "BLOCKED", "decision": "ASK_AUTHOR", "selected_problem": None, "candidate_problems": ranked, "selection_rationale": "critical resource or scoring inputs are unknown"}
    gap = ranked[0]["score"] - ranked[1]["score"] if len(ranked) > 1 and ranked[1]["score"] is not None else 1.0
    clear = gap >= close_margin and not any(item["missing"] for item in ranked[:2])
    decision = "AUTO" if clear else "ASK_AUTHOR"
    selected = ranked[0]["id"] if clear else None
    return {
        "operation": "competition-problem-selection",
        "status": "PASS" if clear else "CONDITIONAL",
        "decision": decision,
        "selected_problem": selected,
        "candidate_problems": ranked,
        "score_gap": round(gap, 6),
        "selection_rationale": (
            f"{ranked[0]['id']} dominates by {gap:.3f} after completion, data, model, paper, resource, and workload risks"
            if clear else "the top two problems are too close or a key resource is unknown"
        ),
    }


def verify_rule_records(
    project: Path,
    records: list[dict[str, Any]],
    *,
    actor: str,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Verify rule records while reserving VERIFIED for current official sources."""
    verifier = str(actor).strip()
    if not verifier:
        raise CompetitionError("rule verification actor is required")
    current = _format_utc(_normalize_now(now_utc))
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        rule_id = str(record.get("rule_id", "")).strip()
        if rule_id:
            grouped.setdefault(rule_id, []).append(record)
    state_dir = _state_dir(project)
    value = _read_json(state_dir / "competition_rules.json")
    rules = value.setdefault("rules", {})
    for rule_id in competition_quality.REQUIRED_OFFICIAL_RULES:
        candidates = grouped.get(rule_id, [])
        official = [
            item
            for item in candidates
            if str(item.get("source_type", "")).upper() == "OFFICIAL_PRIMARY"
        ]
        distinct = {
            json.dumps(item.get("value"), ensure_ascii=False, sort_keys=True)
            for item in official
        }
        if len(distinct) > 1:
            status = "CONFLICTING"
            chosen = official[0]
        elif official:
            status = "VERIFIED"
            chosen = official[0]
        elif candidates:
            status = "BACKGROUND_ONLY"
            chosen = candidates[0]
        else:
            status = "UNVERIFIED"
            chosen = {}
        rules[rule_id] = {
            "rule_id": rule_id,
            "status": status,
            "value": chosen.get("value"),
            "official_source": str(chosen.get("official_source", "")),
            "retrieved_utc": str(chosen.get("retrieved_utc", "")),
            "verified_utc": current if status == "VERIFIED" else "",
            "verification_actor": verifier,
            "actor": verifier,
            "exact_region": str(chosen.get("exact_region", "")),
            "source_type": str(chosen.get("source_type", "")),
        }
    value["last_verification_utc"] = current
    _write_json(state_dir / "competition_rules.json", value)
    unverified = [
        rule_id
        for rule_id in competition_quality.REQUIRED_OFFICIAL_RULES
        if rules[rule_id]["status"] != "VERIFIED"
    ]
    return {
        "operation": "verify-competition-rule-records",
        "status": "PASS" if not unverified else "CONDITIONAL",
        "rules": rules,
        "unverified": unverified,
        "state_dir": str(state_dir),
    }


def audit_rules(project: Path, *, submission: bool = False) -> dict[str, Any]:
    state_dir = _state_dir(project)
    value = _read_json(state_dir / "competition_rules.json")
    rules = value.get("rules")
    findings: list[str] = []
    unverified: list[str] = []
    if not isinstance(rules, dict):
        return {
            "operation": "audit-competition-rules",
            "status": "FAIL",
            "unverified": list(RULE_FIELDS),
            "findings": ["competition_rules.rules must be an object"],
            "state_dir": str(state_dir),
        }
    required_fields = (
        competition_quality.REQUIRED_OFFICIAL_RULES if submission else RULE_FIELDS
    )
    for name in required_fields:
        item = rules.get(name)
        if not isinstance(item, dict) or item.get("status") != "VERIFIED":
            unverified.append(name)
            findings.append(f"competition rule {name} is UNVERIFIED")
            continue
        missing = [
            field
            for field in ("official_source", "verified_utc", "actor")
            if not str(item.get(field, "")).strip()
        ]
        if missing:
            unverified.append(name)
            findings.append(f"competition rule {name} missing {missing}")
            continue
        try:
            parse_utc(str(item["verified_utc"]))
        except CompetitionError:
            unverified.append(name)
            findings.append(
                f"competition rule {name} verified_utc must be timezone-aware ISO-8601"
            )
    return {
        "operation": "audit-competition-rules",
        "status": "PASS" if not findings else "FAIL",
        "unverified": unverified,
        "findings": findings,
        "state_dir": str(state_dir),
    }


def phase_for(clock: dict[str, Any], profile: dict[str, Any]) -> str:
    """Map elapsed time to a profile phase using the actual contest duration."""
    elapsed = int(clock["elapsed_seconds"])
    duration = int(clock["contest_duration_seconds"])
    if duration <= 0:
        raise CompetitionError("contest duration must be positive")
    if elapsed < 0:
        return "PRE_CONTEST"
    if elapsed >= duration:
        return "DEADLINE_PASSED"
    reference = int(profile["reference_duration_seconds"])
    if reference <= 0:
        raise CompetitionError("profile reference duration must be positive")
    scaled_elapsed = elapsed * reference
    for phase in profile.get("phases", []):
        if "start_seconds" in phase and "end_seconds" in phase:
            start = int(phase["start_seconds"])
            end = int(phase["end_seconds"])
            if start * duration <= scaled_elapsed < end * duration:
                return str(phase["id"])
        elif "start_ratio" in phase and "end_ratio" in phase:
            start_ratio = float(phase["start_ratio"])
            end_ratio = float(phase["end_ratio"])
            ratio = elapsed / duration
            if start_ratio <= ratio < end_ratio:
                return str(phase["id"])
    raise CompetitionError("competition profile does not cover elapsed contest time")


def control_mode_for(
    clock: dict[str, Any], profile: dict[str, Any] | None = None
) -> str:
    profile = profile or _load_profile()
    remaining = int(clock["remaining_seconds"])
    thresholds = profile.get("control_thresholds", {})
    finalization = int(thresholds.get("finalization_seconds", 6 * 3600))
    hard_freeze = int(thresholds.get("hard_freeze_seconds", 2 * 3600))
    if remaining <= 0:
        return "DEADLINE_PASSED"
    if remaining <= hard_freeze:
        return "HARD_FREEZE"
    if remaining <= finalization:
        return "FINALIZATION_MODE"
    return "NORMAL"


def _node_policy(profile: dict[str, Any], node_id: str) -> dict[str, Any]:
    policies = profile.get("node_policies", {})
    policy = policies.get(node_id, {})
    return policy if isinstance(policy, dict) else {}


def _graph_candidates(project: Path) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    path, graph = research_graph.load_graph(project)
    check = research_graph.validate_graph(graph)
    if check["status"] != "PASS":
        raise CompetitionError("graph validation failed: " + "; ".join(check["findings"]))
    plan = research_graph.plan_next(project)
    by_id = {
        node.get("id"): node
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and node.get("id")
    }
    candidates = set(plan.get("ready", []))
    candidates.update(
        node_id
        for node_id, node in by_id.items()
        if node.get("status") in {"READY", "REOPENED"}
    )
    return graph, by_id, sorted(candidates)


def _eta_check(
    node: dict[str, Any],
    estimate: Any,
    remaining: int,
    margin: dict[str, Any],
) -> tuple[bool, str, int | None]:
    if not node.get("job_required") and not node.get("job_required", False):
        return True, "", 0
    if estimate is None:
        return False, "new job requires an estimated runtime", None
    if isinstance(estimate, bool) or not isinstance(estimate, int) or estimate < 0:
        return False, "estimated runtime must be a non-negative integer", None
    safety = max(
        int(margin.get("minimum_seconds", 0)),
        math.ceil(estimate * float(margin.get("eta_multiplier", 0))),
    )
    if estimate + safety >= remaining:
        return (
            False,
            f"ETA plus safety margin ({estimate}+{safety}s) is not less than remaining time ({remaining}s)",
            safety,
        )
    return True, "", safety


def _node_is_job(node_id: str, policy: dict[str, Any]) -> bool:
    return bool(policy.get("job_required", False))


def _rank_key(
    node_id: str,
    policy: dict[str, Any],
    phase: str,
    graph_index: int,
    control: str,
) -> tuple[int, int, int, int]:
    affinity = 0 if phase in policy.get("phase_affinity", []) else 1
    relevance = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(
        str(policy.get("decision_relevance", "MEDIUM")), 1
    )
    risk = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}.get(
        str(policy.get("scientific_risk", "MEDIUM")), 1
    )
    if control != "NORMAL":
        risk *= 2
    return affinity, relevance, risk, graph_index


def _dynamic_priority(
    node_id: str,
    competition_state: dict[str, Any],
    clock: dict[str, Any],
) -> int:
    """Lower is earlier; use qualitative debts and the 12-hour baseline rule."""
    priority = 0
    elapsed = int(clock.get("elapsed_seconds", 0))
    baseline_missing = not bool(competition_state.get("baseline_available"))
    if baseline_missing and elapsed >= 10 * 3600 and node_id in {
        "minimal_viable_model",
        "pilot_solve",
    }:
        priority -= 8
    if str(competition_state.get("paper_debt", "LOW")) == "HIGH" and node_id in {
        "paper_draft",
        "revision",
    }:
        priority -= 5
    if str(competition_state.get("validation_debt", "LOW")) == "HIGH" and node_id in {
        "model_validation",
        "sensitivity_robustness",
    }:
        priority -= 5
    if str(competition_state.get("complexity_debt", "LOW")) == "HIGH" and node_id == "model_improvement":
        priority += 8
    return priority


def schedule(
    project: Path,
    job_estimates: dict[str, int] | None = None,
    critical_fix_nodes: set[str] | None = None,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Return a deterministic overlay decision without mutating graph state."""
    job_estimates = job_estimates or {}
    critical_fix_nodes = critical_fix_nodes or set()
    refreshed = refresh_clock(project, now_utc=now_utc)
    clock = refreshed["clock"]
    graph, by_id, candidate_ids = _graph_candidates(project)
    profile = _load_profile()
    authoritative = bool(clock.get("authoritative_deadline"))
    phase = str(clock.get("current_phase", "UNVERIFIED"))
    control = str(clock.get("control_mode", "UNVERIFIED"))
    eligible: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    policy_actions: list[dict[str, Any]] = []
    policy_path = _state_dir(project) / "autonomy_policy.json"
    policy_value = autonomy.load_policy(policy_path) if policy_path.exists() else None
    competition_state = _read_json(_state_dir(project) / "competition_state.json")
    for graph_index, node_id in enumerate(candidate_ids):
        node = by_id[node_id]
        policy = _node_policy(profile, node_id)
        if not authoritative:
            if _node_is_job(node_id, policy):
                reason = "clock is UNVERIFIED; cannot authorize a timed job"
                blocked.append({"node": node_id, "reason": reason, "policy_blocked": True, "policy_block_reason": reason, "canonical_status": node.get("status")})
            else:
                eligible.append(
                    {"node": node_id, "reason": "clock-unverified non-job work"}
                )
            continue
        if control == "DEADLINE_PASSED":
            reason = "deadline has passed"
            blocked.append({"node": node_id, "reason": reason, "policy_blocked": True, "policy_block_reason": reason, "canonical_status": node.get("status")})
        elif control == "HARD_FREEZE" and (
            not policy.get("submission_critical", False)
            and node_id not in critical_fix_nodes
        ):
            reason = "HARD_FREEZE permits only submission-critical work or CRITICAL fixes"
            blocked.append({"node": node_id, "reason": reason, "policy_blocked": True, "policy_block_reason": reason, "canonical_status": node.get("status")})
        elif control in {"FINALIZATION_MODE", "HARD_FREEZE"} and (
            policy.get("high_risk_change", False) and node_id not in critical_fix_nodes
        ):
            reason = f"{control} blocks high-risk scientific direction changes"
            blocked.append({"node": node_id, "reason": reason, "policy_blocked": True, "policy_block_reason": reason, "canonical_status": node.get("status")})
        elif node_id == "submission_preflight" and audit_rules(project, submission=True)["status"] != "PASS":
            reason = "current official rules are not fully verified"
            blocked.append({"node": node_id, "reason": reason, "policy_blocked": True, "policy_block_reason": reason, "canonical_status": node.get("status")})
        else:
            margin = profile["safety_margins"].get(
                control, profile["safety_margins"]["NORMAL"]
            )
            allowed, reason, safety = _eta_check(
                {**node, **policy},
                job_estimates.get(node_id),
                int(clock["remaining_seconds"]),
                margin,
            )
            if not allowed:
                blocked.append({"node": node_id, "reason": reason, "policy_blocked": True, "policy_block_reason": reason, "canonical_status": node.get("status")})
            else:
                auth = autonomy.authorize(
                    policy_value,
                    "RUN_LOCAL_JOB" if _node_is_job(node_id, policy) else "WRITE_LOCAL",
                    scope=f"competition/{node_id}",
                    risk="MEDIUM" if policy.get("high_risk_change") else "LOW",
                ) if policy_value else {"status": "BLOCKED", "decision": "DENY", "reason": "autonomy policy is missing"}
                if auth.get("status") != "AUTHORIZED":
                    reason = auth.get("reason", "competition action is not authorized")
                    blocked.append({"node": node_id, "reason": reason, "policy_blocked": True, "policy_block_reason": reason, "canonical_status": node.get("status"), "autonomy": auth})
                    continue
                eligible.append(
                    {
                        "node": node_id,
                        "reason": "policy and ETA gate passed",
                        "safety_margin_seconds": safety,
                        "autonomy": auth,
                        "scientific_risk": policy.get("scientific_risk", "MEDIUM"),
                        "scoring_risk": policy.get("scoring_risk", "MEDIUM"),
                        "decision_relevance": policy.get("decision_relevance", "MEDIUM"),
                        "expected_information_gain": policy.get("expected_information_gain", "MEDIUM"),
                        "paper_debt": competition_state.get("paper_debt", "LOW"),
                        "validation_debt": competition_state.get("validation_debt", "LOW"),
                        "complexity_debt": competition_state.get("complexity_debt", "LOW"),
                    }
                )

    eligible.sort(
        key=lambda item: (
            _dynamic_priority(item["node"], competition_state, clock),
        )
        + _rank_key(
            item["node"],
            _node_policy(profile, item["node"]),
            phase,
            next(
                index
                for index, node in enumerate(graph.get("nodes", []))
                if node.get("id") == item["node"]
            ),
            control,
        )
    )
    result = {
        "operation": "competition-schedule",
        "status": "PASS" if authoritative else "CONDITIONAL",
        "authoritative_deadline": authoritative,
        "current_phase": phase,
        "control_mode": control,
        "stop_rule_active": bool(clock.get("stop_rule_active")),
        "hard_freeze_active": bool(clock.get("hard_freeze_active")),
        "remaining_seconds": clock.get("remaining_seconds"),
        "baseline_rule": {
            "baseline_missing": not bool(competition_state.get("baseline_available")),
            "risk_high_at_t_plus_10h": (
                not bool(competition_state.get("baseline_available"))
                and int(clock.get("elapsed_seconds", 0)) >= 10 * 3600
            ),
            "scope_reduction_required_at_t_plus_12h": (
                not bool(competition_state.get("baseline_available"))
                and int(clock.get("elapsed_seconds", 0)) >= 12 * 3600
            ),
        },
        "eligible": [item["node"] for item in eligible],
        "eligible_details": eligible,
        "blocked": blocked,
        "policy_actions": [],
        "policy_projection": {item["node"]: {"policy_blocked": True, "policy_block_reason": item["reason"], "canonical_status": item.get("canonical_status")} for item in blocked},
        "next_action": eligible[0] if eligible else None,
        "state_dir": str(_state_dir(project)),
    }
    return result


def advance(
    project: Path,
    actor: str = "competition-scheduler",
    job_estimates: dict[str, int] | None = None,
    critical_fix_nodes: set[str] | None = None,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Refresh the read-only policy projection without mutating scientific status."""
    plan = schedule(
        project,
        job_estimates=job_estimates,
        critical_fix_nodes=critical_fix_nodes,
        now_utc=now_utc,
    )
    return {
        "operation": "competition-advance",
        "status": plan["status"],
        "changed": [],
        "overlay_only": True,
        "plan": plan,
    }


def execute_next(
    project: Path,
    *,
    actor: str = "competition-director",
    job_estimates: dict[str, int] | None = None,
    critical_fix_nodes: set[str] | None = None,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Run the highest-value eligible node through shared authorization and graph contracts."""
    _, graph_value = research_graph.load_graph(project)
    running = [item for item in graph_value.get("nodes", []) if item.get("status") == "RUNNING"]
    resuming_host = False
    if running:
        node_id = str(running[0].get("id"))
        active = host_provider_runtime.active_for_node(project, node_id)
        if not active:
            return {"operation": "competition-execute-next", "status": "BLOCKED", "reason": "RUNNING node has no resumable host request", "node": node_id}
        if active.get("status") != "ACCEPTED":
            return {
                "operation": "competition-execute-next", "status": "HOST_EXECUTION_REQUIRED",
                "node": node_id, "request_path": active.get("request_path"),
                "host_request_created": True, "ordinary_author_prompts": 0,
            }
        plan = {"control_mode": "HOST_HANDOFF_RESUME", "next_action": {"node": node_id}}
        authorization = {"status": "AUTHORIZED", "decision": "AUTO", "reason": "resume independently checked host handoff"}
        resuming_host = True
    else:
        plan = schedule(project, job_estimates=job_estimates, critical_fix_nodes=critical_fix_nodes, now_utc=now_utc)
        selected = plan.get("next_action")
        if not selected:
            return {"operation": "competition-execute-next", "status": "BLOCKED", "reason": "no overlay-eligible node", "plan": plan}
        node_id = selected["node"]
        authorization = selected.get("autonomy", {"status": "BLOCKED", "decision": "DENY"})
        if authorization.get("status") != "AUTHORIZED":
            return {"operation": "competition-execute-next", "status": "BLOCKED", "reason": authorization.get("reason"), "authorization": authorization, "plan": plan}
        research_graph.transition(project, node_id, "RUNNING", "competition Director dispatch", actor, None)
    execution = competition_executor.execute_node(project, node_id)
    if execution.get("status") == "HOST_EXECUTION_REQUIRED":
        return {
            "operation": "competition-execute-next", "status": "HOST_EXECUTION_REQUIRED",
            "node": node_id, "authorization": authorization, "execution": execution,
            "request_path": execution.get("request_path"), "host_request_created": True,
            "resuming_host": resuming_host, "plan": plan,
        }
    if execution.get("status") != "PASS":
        research_graph.transition(project, node_id, "FAIL", "competition executor failed output contract", actor, None)
        recovery = director_loop.recovery_decision(project, node_id, f"competition:{node_id}:output-contract", previous_result="FAIL")
        if recovery.get("status") == "PASS":
            research_graph.transition(project, node_id, "REOPENED", f"competition recovery: {recovery['strategy']}", actor, None)
        return {"operation": "competition-execute-next", "status": "FAIL", "node": node_id, "authorization": authorization, "execution": execution, "recovery": recovery, "plan": plan}
    evidence = ",".join(execution.get("evidence", []))
    research_graph.transition(project, node_id, "PASS", "competition executor output contract passed", actor, evidence)
    audit_path = _state_dir(project) / ".autonomy-audit.jsonl"
    autonomy.append_audit(
        audit_path,
        "competition-node-execution",
        {"node": node_id, "artifacts": execution.get("artifacts", []), "evidence": execution.get("evidence", []), "control_mode": plan.get("control_mode")},
        actor=actor,
        decision=authorization.get("decision", "AUTO"),
        utc=_format_utc(_normalize_now(now_utc)),
    )
    return {"operation": "competition-execute-next", "status": "PASS", "node": node_id, "authorization": authorization, "execution": execution, "plan": plan}


def _duration_text(seconds: int) -> str:
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    return f"{sign}{hours}h {minutes}m"


def dashboard(
    project: Path, now_utc: datetime | None = None
) -> dict[str, Any]:
    current = _normalize_now(now_utc)
    refreshed = refresh_clock(project, now_utc=current)
    clock = refreshed["clock"]
    scheduled = schedule(project, now_utc=current)
    _, graph = research_graph.load_graph(project)
    state_dir = _state_dir(project)
    competition_state = _read_json(state_dir / "competition_state.json")
    nodes = [item for item in graph.get("nodes", []) if isinstance(item, dict)]
    completed = [
        item.get("id")
        for item in nodes
        if item.get("status") in {"PASS", "CONDITIONAL"}
    ]
    running = [item.get("id") for item in nodes if item.get("status") == "RUNNING"]
    blocked = [item.get("id") for item in nodes if item.get("status") == "BLOCKED"]
    policy_blocked = [item.get("node") for item in scheduled.get("blocked", [])]
    next_action = scheduled.get("next_action")
    next_node = next_action.get("node") if isinstance(next_action, dict) else None
    return {
        "operation": "competition-dashboard",
        "status": refreshed["status"],
        "competition": competition_state.get("competition", "CUMCM"),
        "problem_selected": competition_state.get("selected_problem"),
        "competition_time": {
            "start_utc": clock.get("contest_start_utc"),
            "deadline_utc": clock.get("submission_deadline_utc"),
        },
        "elapsed": _duration_text(int(clock.get("elapsed_seconds", 0))),
        "remaining": _duration_text(int(clock.get("remaining_seconds", 0))),
        "elapsed_seconds": clock.get("elapsed_seconds", 0),
        "remaining_seconds": clock.get("remaining_seconds", 0),
        "current_phase": clock.get("current_phase", "UNVERIFIED"),
        "control_mode": clock.get("control_mode", "UNVERIFIED"),
        "stop_rule": "ON" if clock.get("stop_rule_active") else "OFF",
        "hard_freeze": "ON" if clock.get("hard_freeze_active") else "OFF",
        "completed": completed,
        "running": running,
        "blocked": blocked,
        "blocked_by_science": blocked,
        "policy_blocked": policy_blocked,
        "blocked_by_policy": policy_blocked,
        "blocked_by_time": [
            item.get("node")
            for item in scheduled.get("blocked", [])
            if any(token in item.get("reason", "") for token in ("ETA", "remaining time", "HARD_FREEZE", "FINALIZATION", "deadline"))
        ],
        "policy_projection": scheduled.get("policy_projection", {}),
        "current_best_model": competition_state.get("current_best_model"),
        "baseline": competition_state.get("baseline_model"),
        "primary_model": competition_state.get("primary_model"),
        "largest_scientific_risk": competition_state.get("largest_scientific_risk", "not assessed"),
        "largest_scoring_risk": competition_state.get("largest_scoring_risk"),
        "paper_debt": competition_state.get("paper_debt", "LOW"),
        "validation_debt": competition_state.get("validation_debt", "LOW"),
        "complexity_debt": competition_state.get("complexity_debt", "LOW"),
        "highest_roi_next_action": next_node
        or competition_state.get("highest_roi_next_action"),
        "submission_readiness": competition_state.get("submission_readiness"),
        "time_source": "competition_runtime",
        "authoritative_deadline": clock.get("authoritative_deadline", False),
        "author_action_required": competition_state.get("author_action_required", "NONE"),
    }


def _job_estimates(path: Path | None) -> dict[str, int]:
    if path is None:
        return {}
    value = _read_json(path)
    estimates: dict[str, int] = {}
    for node_id, estimate in value.items():
        if isinstance(estimate, bool) or not isinstance(estimate, int):
            raise CompetitionError(
                f"job estimate for {node_id} must be an integer number of seconds"
            )
        estimates[str(node_id)] = estimate
    return estimates


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {SKILL_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in (
        "status",
        "dashboard",
        "refresh-clock",
        "validate-clock",
        "audit-rules",
    ):
        command = sub.add_parser(name)
        command.add_argument("project", type=Path)

    configure = sub.add_parser("configure-clock")
    configure.add_argument("project", type=Path)
    configure.add_argument("--start", required=True)
    configure.add_argument("--deadline", required=True)
    configure.add_argument("--official-source", default="")
    configure.add_argument("--actor", required=True)

    verify = sub.add_parser("verify-clock")
    verify.add_argument("project", type=Path)
    verify.add_argument("--official-source", required=True)
    verify.add_argument("--actor", required=True)

    verify_rules_parser = sub.add_parser("verify-rules")
    verify_rules_parser.add_argument("project", type=Path)
    verify_rules_parser.add_argument("--records", required=True, type=Path)
    verify_rules_parser.add_argument("--actor", required=True)

    extension = sub.add_parser("official-extension")
    extension.add_argument("project", type=Path)
    extension.add_argument("--deadline", required=True)
    extension.add_argument("--official-source", required=True)
    extension.add_argument("--reason", required=True)
    extension.add_argument("--actor", required=True)

    adjust = sub.add_parser("adjust-clock")
    adjust.add_argument("project", type=Path)
    adjust.add_argument("--offset-seconds", required=True, type=int)
    adjust.add_argument("--reason", required=True)
    adjust.add_argument("--actor", required=True)

    for name in ("pause-clock", "resume-clock"):
        command = sub.add_parser(name)
        command.add_argument("project", type=Path)
        command.add_argument("--reason", required=True)
        command.add_argument("--actor", required=True)

    for name in ("schedule", "advance", "execute-next"):
        command = sub.add_parser(name)
        command.add_argument("project", type=Path)
        command.add_argument("--job-estimates", type=Path)
        command.add_argument("--critical-fix-node", action="append", default=[])
        if name in {"advance", "execute-next"}:
            command.add_argument("--actor", default="competition-scheduler")
    return parser


def _with_dashboard(project: Path, result: dict[str, Any]) -> dict[str, Any]:
    """Attach a runtime projection whenever the remaining state is readable."""
    try:
        result["dashboard"] = dashboard(project)
    except RUNTIME_OPERATION_ERRORS:
        if result.get("status") in {"PASS", "CONDITIONAL"}:
            raise
    return result


def _dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "status":
        value = dashboard(args.project)
        return {
            "operation": "competition-status",
            "status": value["status"],
            "dashboard": value,
        }
    if args.command == "dashboard":
        return dashboard(args.project)
    if args.command == "refresh-clock":
        return _with_dashboard(args.project, refresh_clock(args.project))
    if args.command == "validate-clock":
        return _with_dashboard(args.project, validate_clock(args.project))
    if args.command == "audit-rules":
        return _with_dashboard(args.project, audit_rules(args.project))
    if args.command == "configure-clock":
        return _with_dashboard(
            args.project,
            configure_clock(
                args.project,
                args.start,
                args.deadline,
                args.official_source,
                args.actor,
            ),
        )
    if args.command == "verify-clock":
        return _with_dashboard(
            args.project,
            verify_clock(args.project, args.official_source, args.actor),
        )
    if args.command == "adjust-clock":
        return _with_dashboard(
            args.project,
            adjust_clock(
                args.project,
                args.offset_seconds,
                args.reason,
                args.actor,
            ),
        )
    if args.command == "pause-clock":
        return _with_dashboard(
            args.project,
            pause_clock(args.project, args.reason, args.actor),
        )
    if args.command == "resume-clock":
        return _with_dashboard(
            args.project,
            resume_clock(args.project, args.reason, args.actor),
        )
    estimates = _job_estimates(args.job_estimates)
    critical = set(args.critical_fix_node)
    if args.command == "schedule":
        return _with_dashboard(
            args.project,
            schedule(
                args.project,
                job_estimates=estimates,
                critical_fix_nodes=critical,
            ),
        )
    if args.command == "verify-rules":
        records_value = _read_json(args.records)
        records = records_value.get("rules")
        if not isinstance(records, list):
            raise CompetitionError("rule records file must contain a rules list")
        return _with_dashboard(
            args.project,
            verify_rule_records(args.project, records, actor=args.actor),
        )
    if args.command == "official-extension":
        return _with_dashboard(
            args.project,
            official_extension(
                args.project,
                args.deadline,
                args.official_source,
                args.reason,
                args.actor,
            ),
        )
    if args.command == "execute-next":
        return _with_dashboard(
            args.project,
            execute_next(
                args.project,
                actor=args.actor,
                job_estimates=estimates,
                critical_fix_nodes=critical,
            ),
        )
    return _with_dashboard(
        args.project,
        advance(
            args.project,
            actor=args.actor,
            job_estimates=estimates,
            critical_fix_nodes=critical,
        ),
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = _dispatch(args)
    except RUNTIME_OPERATION_ERRORS as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") in {"PASS", "CONDITIONAL"} else 1


if __name__ == "__main__":
    sys.exit(main())
