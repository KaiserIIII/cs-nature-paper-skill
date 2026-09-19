#!/usr/bin/env python3
"""Evidence-derived V4.1 provider qualification and PUBLIC_CORE routing."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_RELATIVE_PATH = "assets/registry/v41_provider_registry.json"
QUALIFICATION_RELATIVE_PATH = "assets/registry/v41_provider_qualification.json"
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
VALID_RESULT_STATES = {"PASS", "FAIL", "NOT_RUN"}
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
}
REQUIRED_CHECKS = {
    "source_integrity",
    "license",
    "security",
    "utility",
    "output_contract",
    "behavior_comparison",
}
_AUTHORITY_SEAL = object()


class _ProviderAuthority:
    __slots__ = ("record", "state", "_seal")

    def __init__(self, record: dict[str, Any], state: dict[str, Any]) -> None:
        self.record = deepcopy(record)
        self.state = deepcopy(state)
        self._seal = _AUTHORITY_SEAL


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _file_hash(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _safe_artifact_path(root: Path, relative_path: Any) -> Path | None:
    if not isinstance(relative_path, str) or not relative_path:
        return None
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved


def _load_artifact(root: Path, descriptor: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(descriptor, dict):
        return None, "artifact descriptor must be an object"
    expected = descriptor.get("sha256")
    path = _safe_artifact_path(root, descriptor.get("path"))
    if SOURCE_HASH_RE.fullmatch(str(expected)) is None:
        return None, "artifact digest is invalid"
    if path is None or path.is_symlink() or not path.is_file():
        return None, "artifact path is unavailable or unsafe"
    try:
        payload = path.read_bytes()
        value = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "artifact is unreadable or invalid JSON"
    if _file_hash(payload) != expected or not isinstance(value, dict):
        return None, "artifact digest or type is invalid"
    return value, None


def validate_provider_record(record: dict[str, Any]) -> dict[str, Any]:
    """Validate immutable provider metadata without accepting authored state."""
    findings: list[str] = []
    if not isinstance(record, dict):
        return {"status": "FAIL", "findings": ["provider record must be an object"]}
    findings.extend(f"missing field: {field}" for field in sorted(REQUIRED_FIELDS - set(record)))
    if not isinstance(record.get("provider_id"), str) or not record.get("provider_id"):
        findings.append("provider_id must be a non-empty string")
    if not isinstance(record.get("type"), str) or not record.get("type"):
        findings.append("type must be a non-empty string")
    capabilities = record.get("capabilities")
    if (
        not isinstance(capabilities, list)
        or not capabilities
        or any(not isinstance(item, str) or not item for item in capabilities)
        or len(capabilities) != len(set(capabilities))
    ):
        findings.append("capabilities must be unique non-empty strings")
    if COMMIT_RE.fullmatch(str(record.get("exact_commit", ""))) is None:
        findings.append("exact_commit must be a 40-character lowercase commit hash")
    if SOURCE_HASH_RE.fullmatch(str(record.get("source_hash", ""))) is None:
        findings.append("source_hash must be sha256:<64 lowercase hex characters>")
    if record.get("license_decision") not in FORMAL_LICENSE_DECISIONS:
        findings.append("license_decision is not cleared for formal use")
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def _rejected_state(*findings: str) -> dict[str, Any]:
    return {
        "qualification_status": "REJECTED",
        "comparison_decision": "NOT_RUN",
        "utility_status": "NOT_RUN",
        "security_status": "NOT_RUN",
        "eligibility": "DISABLED",
        "findings": list(findings),
    }


def _valid_hash_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(SOURCE_HASH_RE.fullmatch(str(item)) is not None for item in value)
    )


def _valid_behavior_comparison(
    behavior: dict[str, Any], record: dict[str, Any], checker_id: str
) -> bool:
    run_ids = behavior.get("run_ids")
    return (
        behavior.get("status") == "PASS"
        and behavior.get("decision") in FORMAL_COMPARISONS
        and behavior.get("baseline_provider_id") == "PUBLIC_CORE"
        and behavior.get("counterbalanced") is True
        and behavior.get("provider_id") == record["provider_id"]
        and behavior.get("exact_commit") == record["exact_commit"]
        and behavior.get("source_hash") == record["source_hash"]
        and isinstance(run_ids, list)
        and len(run_ids) >= 2
        and len(run_ids) == len(set(run_ids))
        and all(isinstance(item, str) and item for item in run_ids)
        and _valid_hash_list(behavior.get("candidate_output_hashes"))
        and _valid_hash_list(behavior.get("public_core_output_hashes"))
        and isinstance(behavior.get("judge_id"), str)
        and bool(behavior["judge_id"])
        and behavior.get("checker_id") == checker_id
        and SOURCE_HASH_RE.fullmatch(str(behavior.get("judge_config_hash", "")))
        is not None
        and SOURCE_HASH_RE.fullmatch(str(behavior.get("artifact_manifest_hash", "")))
        is not None
        and isinstance(behavior.get("failures"), list)
    )


def derive_qualification(
    record: dict[str, Any],
    validation_bundle: dict[str, Any],
    *,
    root: Path | str = ROOT,
) -> dict[str, Any]:
    """Derive candidate state from source-bound artifacts; this alone grants no routing authority."""
    validation = validate_provider_record(record)
    if validation["status"] != "PASS":
        return _rejected_state(*validation["findings"])
    if not isinstance(validation_bundle, dict):
        return _rejected_state("validation bundle must be an object")
    identity_fields = ("provider_id", "exact_commit", "source_hash")
    if any(validation_bundle.get(field) != record.get(field) for field in identity_fields):
        return _rejected_state("validation bundle identity does not match provider metadata")
    producer_id = validation_bundle.get("producer_id")
    checker_id = validation_bundle.get("checker_id")
    if (
        not isinstance(producer_id, str)
        or not producer_id
        or not isinstance(checker_id, str)
        or not checker_id
        or producer_id == checker_id
        or producer_id == record["provider_id"]
        or checker_id == record["provider_id"]
    ):
        return _rejected_state("qualification producer and checker are not independent")
    checks = validation_bundle.get("checks")
    if not isinstance(checks, dict) or set(checks) != REQUIRED_CHECKS:
        return _rejected_state("validation bundle check set is incomplete or unexpected")
    artifact_root = Path(root).resolve()
    artifacts: dict[str, dict[str, Any]] = {}
    findings: list[str] = []
    for name in sorted(REQUIRED_CHECKS):
        artifact, error = _load_artifact(artifact_root, checks.get(name))
        if error is not None or artifact is None:
            findings.append(f"{name}: {error}")
        else:
            artifacts[name] = artifact
    if findings:
        return _rejected_state(*findings)
    evidence_set = {
        "provider_id": record["provider_id"],
        "exact_commit": record["exact_commit"],
        "source_hash": record["source_hash"],
        "producer_id": producer_id,
        "artifacts": {
            name: checks[name]["sha256"] for name in sorted(REQUIRED_CHECKS)
        },
    }
    checker_artifact, checker_error = _load_artifact(
        artifact_root, validation_bundle.get("checker_artifact")
    )
    expected_checker = {
        "status": "PASS",
        "provider_id": record["provider_id"],
        "producer_id": producer_id,
        "checker_id": checker_id,
        "evidence_set_hash": _canonical_hash(evidence_set),
    }
    if checker_error is not None or checker_artifact != expected_checker:
        return _rejected_state("independent checker artifact is missing or does not bind the evidence set")
    source = artifacts["source_integrity"]
    license_result = artifacts["license"]
    behavior = artifacts["behavior_comparison"]
    if source != {
        "status": "PASS",
        "provider_id": record["provider_id"],
        "exact_commit": record["exact_commit"],
        "source_hash": record["source_hash"],
    }:
        findings.append("source integrity artifact does not bind provider source")
    if license_result != {
        "status": "PASS",
        "license_decision": record["license_decision"],
    }:
        findings.append("license artifact does not bind the cleared decision")
    security_status = artifacts["security"].get("status")
    utility_status = artifacts["utility"].get("status")
    if security_status not in VALID_RESULT_STATES:
        findings.append("security artifact status is invalid")
        security_status = "NOT_RUN"
    if utility_status not in VALID_RESULT_STATES:
        findings.append("utility artifact status is invalid")
        utility_status = "NOT_RUN"
    output_contract_pass = artifacts["output_contract"] == {
        "status": "PASS",
        "typed_artifact": True,
    }
    if not output_contract_pass:
        findings.append("typed output contract did not pass")
    comparison_decision = "NOT_RUN"
    if behavior.get("status") == "PASS":
        if _valid_behavior_comparison(behavior, record, checker_id):
            comparison_decision = behavior["decision"]
        else:
            findings.append("behavior comparison artifact is incomplete or invalid")
    elif behavior.get("status") not in {"NOT_RUN", "FAIL"}:
        findings.append("behavior comparison status is invalid")
    qualified = (
        not findings
        and security_status == "PASS"
        and utility_status == "PASS"
        and output_contract_pass
        and comparison_decision in FORMAL_COMPARISONS
    )
    return {
        "qualification_status": "QUALIFIED" if qualified else ("REJECTED" if findings else "PROVISIONAL"),
        "comparison_decision": comparison_decision,
        "utility_status": utility_status,
        "security_status": security_status,
        "eligibility": "FORMAL_ELIGIBLE" if qualified else "NON_LOAD_BEARING",
        "evidence_set_hash": _canonical_hash(evidence_set),
        "checker_id": checker_id,
        "findings": findings,
    }


def _runtime(name: str, filename: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"runtime unavailable: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_authority(provider_id: str) -> _ProviderAuthority | None:
    if not isinstance(provider_id, str) or not provider_id:
        return None
    try:
        trust = _runtime("provider_release_trust", "release_trust.py")
        registry = trust.load_trusted_json(REGISTRY_RELATIVE_PATH)
        qualification = trust.load_trusted_json(QUALIFICATION_RELATIVE_PATH)
    except (OSError, ImportError, AttributeError, RuntimeError, TypeError, ValueError):
        return None
    if not isinstance(registry, dict) or not isinstance(qualification, dict):
        return None
    providers = registry.get("providers")
    bundles = qualification.get("bundles")
    if not isinstance(providers, list) or not isinstance(bundles, list):
        return None
    matches = [
        item for item in providers if isinstance(item, dict) and item.get("provider_id") == provider_id
    ]
    if len(matches) != 1:
        return None
    record = matches[0]
    bundle_id = record.get("validation_bundle_id")
    bundle_matches = [
        item for item in bundles if isinstance(item, dict) and item.get("bundle_id") == bundle_id
    ]
    if len(bundle_matches) == 1:
        state = derive_qualification(record, bundle_matches[0], root=ROOT)
    elif len(bundle_matches) > 1:
        state = _rejected_state("qualification bundle identity is ambiguous")
    else:
        validation = validate_provider_record(record)
        state = {
            "qualification_status": "UNAUDITED",
            "comparison_decision": "NOT_RUN",
            "utility_status": "NOT_RUN",
            "security_status": "NOT_RUN",
            "eligibility": "DISABLED",
            "findings": ["trusted qualification bundle is absent", *validation["findings"]],
        }
    return _ProviderAuthority(record, state)


def derive_eligibility(
    record: dict[str, Any], *, formal: bool, capability: str | None = None
) -> str:
    """Fail closed for legacy caller-authored state; formal authority is fixed-path only."""
    return "DISABLED"


def resolve_provider(
    record_or_provider_id: dict[str, Any] | str,
    public_core: dict[str, Any],
    *,
    formal: bool,
    capability: str | None = None,
) -> dict[str, Any]:
    """Resolve only trust-root-loaded provider evidence, otherwise use PUBLIC_CORE."""
    caller_record = record_or_provider_id if isinstance(record_or_provider_id, dict) else None
    provider_id = (
        record_or_provider_id.get("provider_id")
        if isinstance(record_or_provider_id, dict)
        else record_or_provider_id
    )
    authority = _load_authority(provider_id) if isinstance(provider_id, str) else None
    if authority is None:
        reason = "UNTRUSTED_CALLER_RECORD" if caller_record is not None else "UNKNOWN_PROVIDER"
        if (
            capability is not None
            and isinstance(caller_record, dict)
            and capability not in caller_record.get("capabilities", [])
        ):
            reason = "CAPABILITY_MISMATCH"
        return {
            "route": "FALLBACK_BUILT_IN",
            "provider": public_core,
            "candidate_eligibility": "DISABLED",
            "candidate_validation": {"status": "FAIL", "findings": [reason]},
            "reason": reason,
            "truth_authority": "V4_CONTROL_PLANE",
        }
    record = authority.record
    state = authority.state
    if capability is not None and capability not in record.get("capabilities", []):
        reason = "CAPABILITY_MISMATCH"
    elif state.get("eligibility") != "FORMAL_ELIGIBLE":
        reason = "FORMAL_EVIDENCE_INCOMPLETE"
    else:
        reason = "QUALIFIED"
    if state.get("eligibility") == "FORMAL_ELIGIBLE" and (
        formal or state.get("qualification_status") == "QUALIFIED"
    ) and reason == "QUALIFIED":
        return {
            "route": "EXTERNAL_PROVIDER",
            "provider": record,
            "eligibility": "FORMAL_ELIGIBLE" if formal else "ADVISORY_ONLY",
            "qualification": state,
            "truth_authority": "V4_CONTROL_PLANE",
        }
    return {
        "route": "FALLBACK_BUILT_IN",
        "provider": public_core,
        "candidate_eligibility": state.get("eligibility", "DISABLED"),
        "candidate_validation": {
            "status": "PASS" if state.get("qualification_status") != "REJECTED" else "FAIL",
            "findings": state.get("findings", []),
        },
        "candidate_state": state,
        "reason": reason,
        "truth_authority": "V4_CONTROL_PLANE",
    }
