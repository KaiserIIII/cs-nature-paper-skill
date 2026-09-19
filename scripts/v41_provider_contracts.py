#!/usr/bin/env python3
"""Pure V4.1 provider qualification, eligibility, and PUBLIC_CORE routing."""

from __future__ import annotations

import re
from typing import Any


QUALIFICATION_STATUSES = {"UNAUDITED", "AUDITED", "PROVISIONAL", "QUALIFIED", "REJECTED"}
COMPARISON_DECISIONS = {
    "NOT_RUN",
    "INTERNAL_BETTER",
    "EXTERNAL_BETTER",
    "COMPLEMENTARY",
    "EQUIVALENT",
    "INCONCLUSIVE",
}
ELIGIBILITY_STATES = {
    "DISCOVERY_ONLY",
    "ADVISORY_ONLY",
    "NON_LOAD_BEARING",
    "FORMAL_ELIGIBLE",
    "DISABLED",
}
VALID_UTILITY = {"PASS", "FAIL", "NOT_RUN"}
VALID_SECURITY = {"PASS", "FAIL", "NOT_RUN"}
FORMAL_COMPARISONS = {"EXTERNAL_BETTER", "COMPLEMENTARY"}
FORMAL_LICENSE_DECISIONS = {"CLEAR", "CLEAR_FOR_BOUNDED_ADAPTER"}
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SOURCE_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

REQUIRED_FIELDS = {
    "provider_id",
    "type",
    "capabilities",
    "exact_commit",
    "source_hash",
    "license_decision",
    "qualification_status",
    "comparison_decision",
    "utility_status",
    "security_status",
}


def _is_distinct_checker(record: dict[str, Any]) -> bool:
    provider_id = str(record.get("provider_id", ""))
    trial = record.get("behavior_trial")
    if not isinstance(trial, dict):
        return False
    checker_id = str(trial.get("checker_id") or record.get("checker_id") or "")
    return bool(checker_id) and checker_id != provider_id


def validate_provider_record(record: dict[str, Any]) -> dict[str, Any]:
    """Validate the immutable/provider evidence envelope without selecting it."""
    findings: list[str] = []
    if not isinstance(record, dict):
        return {"status": "FAIL", "findings": ["provider record must be an object"]}
    findings.extend(f"missing field: {field}" for field in sorted(REQUIRED_FIELDS - set(record)))
    if not isinstance(record.get("provider_id"), str) or not record.get("provider_id"):
        findings.append("provider_id must be a non-empty string")
    if not isinstance(record.get("capabilities"), list) or not record.get("capabilities"):
        findings.append("capabilities must be a non-empty list")
    if not COMMIT_RE.fullmatch(str(record.get("exact_commit", ""))):
        findings.append("exact_commit must be a 40-character lowercase commit hash")
    if not SOURCE_HASH_RE.fullmatch(str(record.get("source_hash", ""))):
        findings.append("source_hash must be sha256:<64 lowercase hex characters>")
    if not isinstance(record.get("license_decision"), str) or not record.get("license_decision"):
        findings.append("license_decision must be non-empty")
    if record.get("qualification_status") not in QUALIFICATION_STATUSES:
        findings.append("qualification_status is invalid")
    if record.get("comparison_decision") not in COMPARISON_DECISIONS:
        findings.append("comparison_decision is invalid")
    if record.get("utility_status") not in VALID_UTILITY:
        findings.append("utility_status is invalid")
    if record.get("security_status") not in VALID_SECURITY:
        findings.append("security_status is invalid")
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def _has_formal_evidence(record: dict[str, Any], capability: str | None) -> bool:
    if capability is not None and capability not in record.get("capabilities", []):
        return False
    if record.get("qualification_status") != "QUALIFIED":
        return False
    if record.get("comparison_decision") not in FORMAL_COMPARISONS:
        return False
    if record.get("license_decision") not in FORMAL_LICENSE_DECISIONS:
        return False
    if record.get("utility_status") != "PASS" or record.get("security_status") != "PASS":
        return False
    trial = record.get("behavior_trial")
    return (
        isinstance(trial, dict)
        and trial.get("status") == "PASS"
        and trial.get("output_contract") == "PASS"
        and _is_distinct_checker(record)
    )


def derive_eligibility(
    record: dict[str, Any], *, formal: bool, capability: str | None = None
) -> str:
    """Derive eligibility from evidence; ignore any hand-entered eligibility field."""
    validation = validate_provider_record(record)
    if validation["status"] != "PASS":
        return "DISABLED"
    if capability is not None and capability not in record["capabilities"]:
        return "DISABLED"
    if record.get("security_status") == "FAIL" or record.get("utility_status") == "FAIL":
        return "DISABLED"
    if record.get("discovery_only") is True:
        return "DISCOVERY_ONLY"
    if _has_formal_evidence(record, capability):
        return "FORMAL_ELIGIBLE" if formal else "ADVISORY_ONLY"
    return "NON_LOAD_BEARING" if formal else "ADVISORY_ONLY"


def resolve_provider(
    record: dict[str, Any],
    public_core: dict[str, Any],
    *,
    formal: bool,
    capability: str | None = None,
) -> dict[str, Any]:
    """Select a qualified candidate or deterministically fall back to PUBLIC_CORE."""
    validation = validate_provider_record(record)
    eligibility = derive_eligibility(record, formal=formal, capability=capability)
    if capability is not None and capability not in record.get("capabilities", []):
        reason = "CAPABILITY_MISMATCH"
    elif validation["status"] != "PASS":
        reason = "INVALID_PROVIDER_RECORD"
    elif eligibility != "FORMAL_ELIGIBLE" and formal:
        reason = "FORMAL_EVIDENCE_INCOMPLETE"
    elif eligibility in {"DISABLED", "DISCOVERY_ONLY"}:
        reason = "PROVIDER_DISABLED"
    else:
        reason = "PUBLIC_CORE_PRECEDENCE"
    if not formal and eligibility in {"FORMAL_ELIGIBLE", "ADVISORY_ONLY"}:
        return {
            "route": "EXTERNAL_PROVIDER",
            "provider": record,
            "eligibility": eligibility,
            "candidate_validation": validation,
            "truth_authority": "V4_CONTROL_PLANE",
        }
    if formal and eligibility == "FORMAL_ELIGIBLE":
        return {
            "route": "EXTERNAL_PROVIDER",
            "provider": record,
            "eligibility": eligibility,
            "candidate_validation": validation,
            "truth_authority": "V4_CONTROL_PLANE",
        }
    return {
        "route": "FALLBACK_BUILT_IN",
        "provider": public_core,
        "candidate_eligibility": eligibility,
        "candidate_validation": validation,
        "reason": reason,
        "truth_authority": "V4_CONTROL_PLANE",
    }
