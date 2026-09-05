#!/usr/bin/env python3
"""Fail-closed v3.2 autonomy policy, authorization, and audit primitives."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKILL_VERSION = "3.2.1"
POLICY_SCHEMA_VERSION = 1
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
RISK_ORDER = {value: index for index, value in enumerate(RISK_LEVELS)}
KNOWN_ACTIONS = {
    "RUN_LOCAL_JOB",
    "READ_PRIVATE",
    "WRITE_LOCAL",
    "EXECUTE",
    "AUTO_HIRE",
    "NETWORK_READ",
    "EXTERNAL_WRITE",
    "PUBLISH",
    "SUBMIT",
    "PROTOCOL_CHANGE",
    "SCIENTIFIC_DECISION",
    "DELETE",
}
PERMISSION_FOR_ACTION = {
    "RUN_LOCAL_JOB": "execute",
    "READ_PRIVATE": "local_read",
    "WRITE_LOCAL": "local_write",
    "EXECUTE": "execute",
    "AUTO_HIRE": "auto_hire",
    "NETWORK_READ": "network",
    "EXTERNAL_WRITE": "external_write",
    "PUBLISH": "publish",
    "SUBMIT": "submit",
    "PROTOCOL_CHANGE": "protocol_change",
    "SCIENTIFIC_DECISION": "scientific_decision",
    "DELETE": "delete",
}
IMMUTABLE_REF = re.compile(r"^[0-9a-f]{40}$")
AUTO_SCIENTIFIC_DECISIONS = {
    "ordinary",
    "choose_baseline",
    "choose_statistical_test",
    "choose_implementation_method",
    "change_optimizer",
    "add_ablation",
    "add_sensitivity_analysis",
    "change_hyperparameters",
    "replace_failed_model",
    "remove_unsupported_claim",
    "narrow_claim_scope",
    "repair_implementation",
    "choose_visualization",
}
AUDITED_SCIENTIFIC_DECISIONS = {
    "bounded_protocol_amendment",
    "switch_primary_model",
    "remove_secondary_rq",
    "reduce_experiment_scope",
}
AUTHOR_SCIENTIFIC_DECISIONS = {
    "replace_core_research_question",
    "fundamental_target_population_change",
    "change_scientific_phenomenon",
    "introduce_human_subjects",
    "material_budget_expansion",
    "change_confidential_data_policy",
    "fundamental_redesign_after_formal_results",
}
AUDITED_ACTIONS = {"NETWORK_READ"}
AUTHOR_ACTIONS = {"EXTERNAL_WRITE", "PUBLISH", "SUBMIT", "DELETE"}


class AutonomyError(RuntimeError):
    """Raised only for malformed local operations, never ordinary denials."""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_time(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AutonomyError(f"cannot read JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AutonomyError(f"JSON root must be an object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _policy_findings(policy: Any) -> list[str]:
    findings: list[str] = []
    if not isinstance(policy, dict):
        return ["policy must be an object"]
    if policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        findings.append("policy.schema_version must be 1")
    if policy.get("skill_version") != SKILL_VERSION:
        findings.append("policy.skill_version must be 3.2.1")
    if policy.get("mode") != "maximum-autonomy":
        findings.append("policy.mode must be maximum-autonomy")
    if policy.get("risk_cap") not in RISK_LEVELS:
        findings.append("policy.risk_cap must be a known risk level")
    if policy.get("fail_closed") is not True:
        findings.append("policy.fail_closed must be true")
    if not isinstance(policy.get("budgets"), dict):
        findings.append("policy.budgets must be an object")
    if not isinstance(policy.get("permissions"), dict):
        findings.append("policy.permissions must be an object")
    grants = policy.get("standing_authorizations")
    if not isinstance(grants, list):
        findings.append("policy.standing_authorizations must be a list")
    elif any(not isinstance(item, dict) for item in grants):
        findings.append("policy.standing_authorizations entries must be objects")
    return findings


def load_policy(path: Path) -> dict[str, Any]:
    """Load a policy and reject malformed state before any action is considered."""
    value = _read_json(path)
    findings = _policy_findings(value)
    if findings:
        raise AutonomyError("invalid autonomy policy: " + "; ".join(findings))
    return value


def _scope_matches(grant_scope: str, requested: str) -> bool:
    if grant_scope in {"", "*"}:
        return True
    if requested == grant_scope:
        return True
    return requested.startswith(grant_scope.rstrip("/") + "/")


def _active_grant(policy: dict[str, Any], action: str, scope: str, risk: str, now: str) -> dict[str, Any] | None:
    moment = _parse_time(now)
    if moment is None:
        return None
    for grant in policy.get("standing_authorizations", []):
        if not isinstance(grant, dict) or grant.get("active") is not True:
            continue
        if grant.get("action") != action or not _scope_matches(str(grant.get("scope", "")), scope):
            continue
        expires = _parse_time(grant.get("expires_utc"))
        if expires is None or moment >= expires:
            continue
        grant_risk = grant.get("risk")
        if grant_risk not in RISK_ORDER or RISK_ORDER[risk] > RISK_ORDER[grant_risk]:
            continue
        return grant
    return None


def authorize(
    policy: dict[str, Any],
    action: str,
    *,
    scope: str = "",
    risk: str = "LOW",
    reversible: bool = True,
    actor: str = "director",
    now: str | None = None,
    decision_kind: str | None = None,
) -> dict[str, Any]:
    """Return a structured authorization decision without performing the action."""
    decision_time = now or _now()
    base = {
        "operation": "authorize",
        "skill_version": SKILL_VERSION,
        "action": action,
        "scope": scope,
        "risk": risk,
        "reversible": reversible,
        "actor": actor,
        "utc": decision_time,
        "requires_author": False,
        "decision_kind": decision_kind,
    }
    findings = _policy_findings(policy)
    if findings:
        return base | {"status": "BLOCKED", "decision": "DENY", "reason": "malformed policy", "findings": findings, "requires_author": True}
    if action not in KNOWN_ACTIONS:
        return base | {"status": "BLOCKED", "decision": "DENY", "reason": "unknown action", "requires_author": True}
    if risk not in RISK_ORDER:
        return base | {"status": "BLOCKED", "decision": "DENY", "reason": "unknown risk", "requires_author": True}
    permission = PERMISSION_FOR_ACTION[action]
    permissions = policy.get("permissions", {})
    grant = _active_grant(policy, action, scope, risk, decision_time)
    if action in AUTHOR_ACTIONS:
        return base | {"status": "BLOCKED", "decision": "ASK_AUTHOR", "reason": "author-only external or irreversible action", "requires_author": True}
    if action in {"SCIENTIFIC_DECISION", "PROTOCOL_CHANGE"}:
        kind = decision_kind or ("ordinary" if action == "SCIENTIFIC_DECISION" else "unspecified_protocol_change")
        if kind in AUTHOR_SCIENTIFIC_DECISIONS or (action == "PROTOCOL_CHANGE" and kind == "fundamental"):
            return base | {"status": "BLOCKED", "decision": "ASK_AUTHOR", "reason": "fundamental scientific scope decision", "requires_author": True}
        if action == "PROTOCOL_CHANGE" and kind not in {"bounded_protocol_amendment", "minor", "corrective", "outcome_bearing_correction"}:
            return base | {"status": "BLOCKED", "decision": "ASK_AUTHOR", "reason": "protocol change is not bounded", "requires_author": True}
        if action == "SCIENTIFIC_DECISION" and kind not in AUTO_SCIENTIFIC_DECISIONS | AUDITED_SCIENTIFIC_DECISIONS:
            return base | {"status": "BLOCKED", "decision": "ASK_AUTHOR", "reason": "scientific decision class is not authorized", "requires_author": True}
    if not reversible and action not in {"PROTOCOL_CHANGE", "SCIENTIFIC_DECISION"}:
        return base | {"status": "BLOCKED", "decision": "ASK_AUTHOR", "reason": "irreversible action", "requires_author": True}
    if permissions.get(permission) is not True and grant is None:
        return base | {"status": "BLOCKED", "decision": "ASK_AUTHOR", "reason": f"permission {permission} is not granted", "requires_author": True}
    if action == "NETWORK_READ" and permissions.get("network") is not True and grant is None:
        return base | {"status": "BLOCKED", "decision": "ASK_AUTHOR", "reason": "network access is not granted", "requires_author": True}
    cap = policy.get("risk_cap")
    if grant is None and RISK_ORDER[risk] > RISK_ORDER[cap]:
        return base | {"status": "BLOCKED", "decision": "ASK_AUTHOR", "reason": f"risk {risk} exceeds policy cap {cap}", "requires_author": True}
    if action == "AUTO_HIRE" and risk in {"HIGH", "CRITICAL"} and grant is None:
        return base | {"status": "BLOCKED", "decision": "ASK_AUTHOR", "reason": "high-risk capability hire requires author authorization", "requires_author": True}
    if action == "AUTO_HIRE" and risk == "MEDIUM":
        decision = "AUTO_WITH_AUDIT"
    elif action in AUDITED_ACTIONS or action == "PROTOCOL_CHANGE" or decision_kind in AUDITED_SCIENTIFIC_DECISIONS:
        decision = "AUTO_WITH_AUDIT"
    else:
        decision = "AUTO"
    result = base | {"status": "AUTHORIZED", "decision": decision, "reason": "within declared maximum-autonomy envelope"}
    if grant is not None:
        result.update({"authorization_id": grant.get("authorization_id"), "standing_authorization": True})
    else:
        result["standing_authorization"] = False
    return result


def create_standing_authorization(
    policy: dict[str, Any],
    *,
    action: str,
    scope: str,
    risk: str,
    granted_by: str,
    expires_utc: str,
    constraints: list[str] | None = None,
    authorization_id: str | None = None,
) -> dict[str, Any]:
    findings = _policy_findings(policy)
    if findings:
        return {"operation": "standing-authorization", "status": "FAIL", "findings": findings}
    if action not in KNOWN_ACTIONS or risk not in RISK_ORDER or not scope or not granted_by or _parse_time(expires_utc) is None:
        return {"operation": "standing-authorization", "status": "FAIL", "findings": ["action, scope, risk, grantor, and valid expiry are required"]}
    if action in {"PUBLISH", "SUBMIT", "EXTERNAL_WRITE", "PROTOCOL_CHANGE", "SCIENTIFIC_DECISION", "DELETE"}:
        return {"operation": "standing-authorization", "status": "FAIL", "findings": ["irreversible actions cannot receive standing authorization"]}
    grant = {
        "action": action,
        "scope": scope,
        "risk": risk,
        "granted_by": granted_by,
        "granted_utc": _now(),
        "expires_utc": expires_utc,
        "constraints": constraints or [],
        "active": True,
    }
    grant["authorization_id"] = authorization_id or _digest(grant)
    policy.setdefault("standing_authorizations", []).append(grant)
    return {"operation": "standing-authorization", "status": "PASS", "authorization_id": grant["authorization_id"], "record": grant}


def revoke_standing_authorization(policy: dict[str, Any], authorization_id: str, *, actor: str, reason: str) -> dict[str, Any]:
    for grant in policy.get("standing_authorizations", []):
        if isinstance(grant, dict) and grant.get("authorization_id") == authorization_id:
            if grant.get("active") is not True:
                return {"operation": "revoke-standing-authorization", "status": "CONDITIONAL", "authorization_id": authorization_id, "reason": "already inactive"}
            grant.update({"active": False, "revoked_by": actor, "revoked_utc": _now(), "revocation_reason": reason})
            return {"operation": "revoke-standing-authorization", "status": "PASS", "authorization_id": authorization_id}
    return {"operation": "revoke-standing-authorization", "status": "FAIL", "findings": ["authorization_id not found"]}


def auto_hire_gate(policy: dict[str, Any], candidate: dict[str, Any], *, actor: str = "director", now: str | None = None) -> dict[str, Any]:
    required = ("id", "exact_ref", "license", "source_audit", "behavior_trial", "security_audit", "permission_scope", "risk")
    missing = [field for field in required if not candidate.get(field)] if isinstance(candidate, dict) else list(required)
    if missing:
        return {"operation": "auto-hire", "status": "BLOCKED", "reason": "candidate evidence incomplete", "findings": [f"missing {field}" for field in missing], "requires_author": True}
    findings: list[str] = []
    risk = candidate.get("risk")
    if not IMMUTABLE_REF.fullmatch(str(candidate.get("exact_ref", ""))): findings.append("exact_ref must be a 40-character commit SHA")
    if candidate.get("source_audit") != "PASS": findings.append("source audit is not PASS")
    if candidate.get("behavior_trial") != "PASS": findings.append("behavior trial is not PASS")
    if candidate.get("security_audit") != "PASS": findings.append("security audit is not PASS")
    if candidate.get("license_compatible") is False: findings.append("license is incompatible")
    for field in ("credentials", "paid", "admin", "system_wide_write", "private_data_export", "dangerous_hooks"):
        if candidate.get(field) is True: findings.append(f"{field} requires author review")
    if risk in {"LOW", "MEDIUM"} and candidate.get("isolated") is False: findings.append("bounded hire must be isolated")
    if not isinstance(candidate.get("permission_scope"), list) or not candidate["permission_scope"]: findings.append("permission_scope must be a non-empty list")
    if risk not in RISK_ORDER: findings.append("candidate risk is invalid")
    if findings:
        return {"operation": "auto-hire", "status": "BLOCKED", "decision": "ASK_AUTHOR", "reason": "candidate qualification failed", "findings": findings, "requires_author": True}
    scope = str(candidate["permission_scope"][0])
    decision = authorize(policy, "AUTO_HIRE", scope=scope, risk=risk, reversible=True, actor=actor, now=now)
    if decision["status"] != "AUTHORIZED":
        return decision | {"operation": "auto-hire", "candidate_id": candidate["id"], "reason": "AUTO_HIRE authorization required"}
    return decision | {"operation": "auto-hire", "candidate_id": candidate["id"], "qualification": "PASS"}


EVENT_PREFIX = "AA-"


def _event_hash(event: dict[str, Any]) -> str:
    return _digest({key: value for key, value in event.items() if key != "event_hash"})


def _head_path(path: Path) -> Path:
    return Path(str(path) + ".head")


def _load_audit(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    findings: list[str] = []
    if not path.exists():
        return [], findings
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return [], [str(exc)]
    if raw and not raw.endswith(b"\n"):
        findings.append("audit log must end with a newline")
    events: list[dict[str, Any]] = []
    for index, line in enumerate(raw.decode("utf-8", errors="replace").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            findings.append(f"event {index} is malformed JSON")
            continue
        if not isinstance(item, dict):
            findings.append(f"event {index} is not an object")
            continue
        events.append(item)
    previous = "GENESIS"
    for index, event in enumerate(events, start=1):
        expected_id = f"{EVENT_PREFIX}{index:04d}"
        if event.get("event_id") != expected_id: findings.append(f"event {index} expected event_id {expected_id}")
        if event.get("predecessor_hash", "GENESIS") != previous: findings.append(f"event {index} predecessor hash mismatch")
        if event.get("event_hash") != _event_hash(event): findings.append(f"event {index} hash mismatch")
        previous = event.get("event_hash") or _event_hash(event)
    head = _head_path(path)
    if events:
        if not head.exists():
            findings.append("audit head sidecar is missing")
        else:
            stored = head.read_text(encoding="utf-8").strip()
            if stored != previous: findings.append("audit head sidecar does not match final event")
    elif path.exists() and path.stat().st_size:
        findings.append("audit log has no valid events")
    return events, findings


def append_audit(path: Path, operation: str, payload: dict[str, Any], *, actor: str, decision: str, utc: str | None = None) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    events, findings = _load_audit(path)
    if findings:
        raise AutonomyError("refusing to append to invalid audit log: " + "; ".join(findings))
    previous = events[-1].get("event_hash") if events else "GENESIS"
    event = {
        "event_id": f"{EVENT_PREFIX}{len(events) + 1:04d}",
        "utc": utc or _now(),
        "actor": actor,
        "operation": operation,
        "payload": payload,
        "decision": decision,
        "predecessor_hash": previous,
    }
    event["event_hash"] = _event_hash(event)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    _head_path(path).write_text(event["event_hash"] + "\n", encoding="utf-8")
    return {"operation": "audit-append", "status": "PASS", "event": event, "head_hash": event["event_hash"]}


def verify_audit(path: Path) -> dict[str, Any]:
    events, findings = _load_audit(path)
    return {"operation": "audit-verify", "status": "PASS" if not findings else "FAIL", "event_count": len(events), "findings": findings, "head_hash": events[-1].get("event_hash") if events else "GENESIS"}


def audit_head(path: Path) -> str:
    result = verify_audit(path)
    if result["status"] != "PASS":
        raise AutonomyError("audit integrity failed: " + "; ".join(result["findings"]))
    return str(result["head_hash"])


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=SKILL_VERSION)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check-policy"); check.add_argument("path", type=Path)
    verify = sub.add_parser("verify-audit"); verify.add_argument("path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "check-policy":
            value = load_policy(args.path); result = {"operation": "check-policy", "status": "PASS", "mode": value["mode"]}
        else:
            result = verify_audit(args.path)
    except AutonomyError as exc:
        result = {"status": "FAIL", "error": str(exc)}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
