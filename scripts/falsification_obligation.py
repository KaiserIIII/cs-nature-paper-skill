#!/usr/bin/env python3
"""Profile-aware claim falsification obligations with no truth authority."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

FIELDS = ("confirmation_test", "falsification_attempt", "boundary_condition_test", "strongest_surviving_alternative", "residual_confidence")
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

FAMILIES = {
    ("machine-learning", "ml-benchmark"): ("MACHINE_LEARNING", "ML-HELD-OUT"),
    ("software-engineering", "empirical"): ("SOFTWARE_ENGINEERING", "SE-MATCHED-WORKFLOW"),
    ("systems", "engineering-system"): ("SYSTEMS", "SYS-MATCHED-WORKLOAD"),
    ("theory", "theory"): ("THEORY", "THEORY-INDEPENDENT-DERIVATION"),
    ("hci", "human-study"): ("HUMAN_STUDY", "HUMAN-CONSTRUCT-CHECK"),
}
GENERIC_FAMILY = ("GENERIC_CONSERVATIVE", "GENERIC-INDEPENDENT-CHECK")
CHECK_DESCRIPTIONS = {
    "confirmation_test": "Seek independent confirming evidence under the resolved profile.",
    "falsification_attempt": "Attempt the strongest profile-appropriate disconfirmation.",
    "boundary_condition_test": "Test the claim at its declared scope boundary.",
    "strongest_surviving_alternative": "Record the strongest rival explanation that survives testing.",
    "residual_confidence": "Record bounded residual confidence without upgrading claim status.",
}
PROFILE_SCOPE_FIELDS = (
    "domain", "study_type", "claim_type", "venue", "article_type", "design"
)
ROOT = Path(__file__).resolve().parents[1]
REGISTRY_RELATIVE_PATH = "assets/registry/publication_profiles.json"
REGISTRY_PATH = ROOT / REGISTRY_RELATIVE_PATH
SOURCE_MANIFEST_PATH = ROOT / "SHA256SUMS.txt"
MANIFEST_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_AUTHORITY_TOKEN = object()


class _AuthorityContext:
    __slots__ = ("claim", "profile", "snapshot_hash", "token")

    def __init__(
        self,
        claim: dict[str, Any],
        profile: dict[str, Any],
        snapshot_hash: str,
        token: object | None,
    ) -> None:
        self.claim = deepcopy(claim)
        self.profile = deepcopy(profile)
        self.snapshot_hash = snapshot_hash
        self.token = token


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _manifest_bound_registry() -> dict[str, Any] | None:
    try:
        trust_runtime = _runtime("falsification_release_trust", "release_trust.py")
        trusted_registry = trust_runtime.load_trusted_json(REGISTRY_RELATIVE_PATH)
    except (OSError, ImportError, AttributeError, RuntimeError, TypeError, ValueError):
        return None
    if not isinstance(trusted_registry, dict):
        return None
    try:
        registry_bytes = REGISTRY_PATH.read_bytes()
        manifest_lines = SOURCE_MANIFEST_PATH.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    canonical_bytes = registry_bytes
    try:
        canonical_bytes = (
            registry_bytes.decode("utf-8")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .encode("utf-8")
        )
    except UnicodeDecodeError:
        pass
    expected = []
    for line in manifest_lines:
        parts = line.split("  ", 1)
        if (
            len(parts) == 2
            and parts[1] == REGISTRY_RELATIVE_PATH
            and MANIFEST_DIGEST_RE.fullmatch(parts[0]) is not None
        ):
            expected.append(parts[0])
    if len(expected) != 1 or hashlib.sha256(canonical_bytes).hexdigest() != expected[0]:
        return None
    try:
        registry = json.loads(registry_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(registry, dict) or registry != trusted_registry:
        return None
    return registry


def _trusted_profile(profile: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(profile, dict):
        return None
    scope = {
        key: profile[key]
        for key in PROFILE_SCOPE_FIELDS
        if key in profile
    }
    resolver_path = Path(__file__).with_name("publication_profiles.py")
    try:
        spec = importlib.util.spec_from_file_location("publication_profiles_authority", resolver_path)
        if spec is None or spec.loader is None:
            return None
        resolver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(resolver)
        registry = _manifest_bound_registry()
        if registry is None:
            return None
        profiles = registry.get("profiles")
        if not isinstance(profiles, list):
            return None
        resolved = resolver.resolve_profile(scope, profiles)
        return resolved if resolved.get("status") == "PROFILE_RESOLVED" else None
    except (OSError, json.JSONDecodeError, ImportError, AttributeError, TypeError, ValueError):
        return None


def _valid_profile(profile: Any) -> bool:
    if not isinstance(profile, dict):
        return False
    expected = profile.get("canonical_output_hash")
    body = {key: value for key, value in profile.items() if key != "canonical_output_hash"}
    if profile.get("status") != "PROFILE_RESOLVED" or not isinstance(expected, str):
        return False
    normalized = expected if expected.startswith("sha256:") else "sha256:" + expected
    if HASH_RE.fullmatch(normalized) is None or normalized != canonical_hash(body):
        return False
    trusted = _trusted_profile(profile)
    if trusted is None:
        return False
    trusted_body = {key: value for key, value in trusted.items() if key != "canonical_output_hash"}
    return body == trusted_body


def _runtime(name: str, filename: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"runtime unavailable: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _control_plane_context(
    project_dir: Path | str, claim_id: str
) -> tuple[dict[str, Any], dict[str, Any], str]:
    if not isinstance(project_dir, (str, Path)) or not isinstance(claim_id, str) or not claim_id.strip():
        raise ValueError("invalid control-plane context selector")
    project = Path(project_dir).resolve()
    research_state = _runtime("falsification_research_state", "research_state.py")
    resolver = _runtime("falsification_publication_profiles", "publication_profiles.py")
    state_dir = research_state._state_dir(project)
    try:
        state_dir.resolve().relative_to(project)
    except ValueError as exc:
        raise ValueError("research state escapes project boundary") from exc
    paths = {
        "project": state_dir / "project.json",
        "contract": state_dir / "research_contract.json",
        "claims": state_dir / "claims.json",
    }
    if any(path.is_symlink() or not path.is_file() for path in paths.values()):
        raise ValueError("required authoritative state file is missing or redirected")
    documents = {name: research_state._read_json(path) for name, path in paths.items()}
    project_doc = documents["project"]
    contract_doc = documents["contract"]
    claims_doc = documents["claims"]
    if (
        project_doc.get("schema_version") != 3
        or project_doc.get("skill_version") != "4.1.0"
        or Path(str(project_doc.get("project_dir", ""))).resolve() != project
        or claims_doc.get("schema_version") != 1
        or claims_doc.get("skill_version") != "4.1.0"
    ):
        raise ValueError("unsupported or mismatched authoritative state identity")
    domain = project_doc.get("domain")
    study_type = project_doc.get("study_type")
    contract_project = contract_doc.get("project")
    if (
        not isinstance(domain, str)
        or not domain.strip()
        or not isinstance(study_type, str)
        or not study_type.strip()
        or not isinstance(contract_project, dict)
        or contract_project.get("domain") != domain
        or contract_project.get("study_type") != study_type
    ):
        raise ValueError("project and research contract disagree")
    claims = claims_doc.get("claims")
    if not isinstance(claims, list):
        raise ValueError("claims registry is invalid")
    matches = [
        item
        for item in claims
        if isinstance(item, dict) and item.get("id") == claim_id
    ]
    ids = [item.get("id") for item in claims if isinstance(item, dict)]
    if len(matches) != 1 or len(ids) != len(set(ids)):
        raise ValueError("claim identity is missing or ambiguous")
    claim = deepcopy(matches[0])
    if "claim_id" in claim and claim["claim_id"] != claim_id:
        raise ValueError("claim identity fields disagree")
    claim.pop("id", None)
    claim["claim_id"] = claim_id
    request: dict[str, Any] = {"domain": domain, "study_type": study_type}
    if isinstance(claim.get("type"), str) and claim["type"].strip():
        request["claim_type"] = claim["type"]
    registry = _manifest_bound_registry()
    if registry is None or not isinstance(registry.get("profiles"), list):
        raise ValueError("publication profile authority is unavailable")
    profile = resolver.resolve_profile(request, registry["profiles"])
    if profile.get("status") != "PROFILE_RESOLVED" or not _valid_profile(profile):
        raise ValueError("publication profile authority rejected the project scope")
    snapshot = {
        "claim_id": claim_id,
        "state_files": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in sorted(paths.items())
        },
        "profile_hash": profile.get("canonical_output_hash"),
    }
    return claim, profile, canonical_hash(snapshot)


def _sealed_context(
    claim: dict[str, Any],
    profile: dict[str, Any],
    snapshot_hash: str,
    *,
    _token: object | None = None,
) -> _AuthorityContext:
    return _AuthorityContext(claim, profile, snapshot_hash, _token)


def _load_authority_context(
    project_dir: Path | str, claim_id: str
) -> _AuthorityContext:
    claim, profile, snapshot_hash = _control_plane_context(project_dir, claim_id)
    return _sealed_context(
        claim,
        profile,
        snapshot_hash,
        _token=_AUTHORITY_TOKEN,
    )


def _valid_authority_context(context: Any) -> bool:
    return (
        isinstance(context, _AuthorityContext)
        and context.token is _AUTHORITY_TOKEN
        and isinstance(context.claim, dict)
        and isinstance(context.profile, dict)
        and isinstance(context.snapshot_hash, str)
        and HASH_RE.fullmatch(context.snapshot_hash) is not None
    )


def _base(status: str, required: bool) -> dict[str, Any]:
    return {"operation": "falsification-obligation", "status": status, "required": required, "claim_status_change_authorized": False, "evidence_upgrade_authorized": False, "graph_transition_authorized": False, "publication_pass": False}


def _check_specs(family: str, confirmation: str) -> dict[str, dict[str, str]]:
    return {
        "confirmation_test": {
            "check_id": confirmation,
            "description": CHECK_DESCRIPTIONS["confirmation_test"],
        },
        "falsification_attempt": {
            "check_id": family + "-FALSIFICATION",
            "description": CHECK_DESCRIPTIONS["falsification_attempt"],
        },
        "boundary_condition_test": {
            "check_id": family + "-BOUNDARY",
            "description": CHECK_DESCRIPTIONS["boundary_condition_test"],
        },
        "strongest_surviving_alternative": {
            "check_id": family + "-ALTERNATIVE",
            "description": CHECK_DESCRIPTIONS["strongest_surviving_alternative"],
        },
        "residual_confidence": {
            "check_id": family + "-RESIDUAL",
            "description": CHECK_DESCRIPTIONS["residual_confidence"],
        },
    }


def _valid_required_artifact_semantics(artifact: dict[str, Any]) -> bool:
    if (
        artifact.get("operation") != "falsification-obligation"
        or artifact.get("status") != "OBLIGATION_REQUIRED"
        or artifact.get("required") is not True
        or not isinstance(artifact.get("claim_id"), str)
        or not artifact["claim_id"].strip()
    ):
        return False
    family = artifact.get("profile_family")
    confirmations = {item[0]: item[1] for item in FAMILIES.values()}
    confirmations[GENERIC_FAMILY[0]] = GENERIC_FAMILY[1]
    if family not in confirmations:
        return False
    return all(
        artifact.get(field) == expected
        for field, expected in _check_specs(family, confirmations[family]).items()
    )


def derive_obligation(
    claim: dict[str, Any], profile: dict[str, Any], *, producer_id: str
) -> dict[str, Any]:
    producer = producer_id.strip() if isinstance(producer_id, str) else ""
    if not isinstance(claim, dict) or not isinstance(profile, dict):
        return {**_base("OBLIGATION_REJECTED", False), "error_code": "INVALID_INPUT_TYPE"}
    if (
        not isinstance(claim.get("claim_id"), str)
        or not claim["claim_id"].strip()
        or ("strength" in claim and not isinstance(claim["strength"], str))
        or ("load_bearing" in claim and not isinstance(claim["load_bearing"], bool))
    ):
        return {**_base("OBLIGATION_REJECTED", False), "error_code": "INVALID_CLAIM"}
    for key in PROFILE_SCOPE_FIELDS:
        if key in claim and (
            not isinstance(claim[key], str)
            or not claim[key].strip()
            or claim[key] != profile.get(key)
        ):
            return {**_base("OBLIGATION_REJECTED", False), "error_code": "PROFILE_SCOPE_MISMATCH"}
    if not producer or not _valid_profile(profile):
        return {**_base("OBLIGATION_REJECTED", False), "error_code": "UNTRUSTED_PROFILE"}
    required = bool(claim.get("load_bearing")) or str(claim.get("strength", "")).upper() in {"HIGH", "STRONG", "LOAD_BEARING"}
    if not required:
        return _base("NOT_REQUIRED", False)
    family, confirmation = FAMILIES.get((str(profile.get("domain", "")), str(profile.get("study_type", ""))), GENERIC_FAMILY)
    artifact = {
        **_base("OBLIGATION_REQUIRED", True),
        "claim_id": str(claim.get("claim_id", "")),
        "claim_hash": canonical_hash(claim),
        "profile_hash": str(profile["canonical_output_hash"]),
        "profile_family": family,
        "producer_id": producer,
        **_check_specs(family, confirmation),
    }
    artifact["obligation_hash"] = canonical_hash(artifact)
    return artifact


def _bind_authority_snapshot(
    artifact: dict[str, Any], snapshot_hash: str
) -> dict[str, Any]:
    artifact = deepcopy(artifact)
    if artifact.get("status") == "OBLIGATION_REQUIRED":
        artifact["authority_snapshot_hash"] = snapshot_hash
        artifact["obligation_hash"] = canonical_hash(
            {key: value for key, value in artifact.items() if key != "obligation_hash"}
        )
    return artifact


def _derive_obligation_with_context(
    authority_context: _AuthorityContext, *, producer_id: str
) -> dict[str, Any]:
    if not isinstance(authority_context, _AuthorityContext):
        return {
            **_base("OBLIGATION_REJECTED", False),
            "error_code": "UNTRUSTED_CHECK_CONTEXT",
        }
    return _bind_authority_snapshot(
        derive_obligation(
            authority_context.claim,
            authority_context.profile,
            producer_id=producer_id,
        ),
        authority_context.snapshot_hash,
    )


def _check_obligation_with_context(
    artifact: dict[str, Any],
    evidence: dict[str, Any],
    *,
    producer_id: str,
    checker_id: str,
    authority_context: _AuthorityContext,
) -> dict[str, Any]:
    if not isinstance(artifact, dict) or not isinstance(evidence, dict):
        return {
            **_base("OBLIGATION_REJECTED", False),
            "error_code": "INVALID_INPUT_TYPE",
            "checker_id": checker_id,
            "missing_evidence": [],
        }
    artifact = deepcopy(artifact)
    evidence = deepcopy(evidence)
    result = {
        **_base("OBLIGATION_REJECTED", bool(artifact.get("required"))),
        "checker_id": checker_id,
        "missing_evidence": [],
    }
    if not _valid_authority_context(authority_context):
        result["error_code"] = "UNTRUSTED_CHECK_CONTEXT"
        return result
    trusted_producer = producer_id.strip() if isinstance(producer_id, str) else ""
    checker = checker_id.strip() if isinstance(checker_id, str) else ""
    artifact_producer = artifact.get("producer_id")
    if (
        not trusted_producer
        or not isinstance(artifact_producer, str)
        or not artifact_producer.strip()
        or artifact_producer != trusted_producer
        or not checker
        or checker == trusted_producer
    ):
        return result
    stored_hash = artifact.get("obligation_hash")
    body = {key: value for key, value in artifact.items() if key != "obligation_hash"}
    if not isinstance(stored_hash, str) or stored_hash != canonical_hash(body):
        return result
    if not _valid_required_artifact_semantics(artifact):
        return result
    expected_artifact = _derive_obligation_with_context(
        authority_context,
        producer_id=trusted_producer,
    )
    if (
        expected_artifact.get("status") != "OBLIGATION_REQUIRED"
        or artifact != expected_artifact
    ):
        result["error_code"] = "OBLIGATION_BINDING_MISMATCH"
        return result
    authority_fields = (
        "claim_status_change_authorized",
        "evidence_upgrade_authorized",
        "graph_transition_authorized",
        "publication_pass",
    )
    if any(artifact.get(field) is not False for field in authority_fields):
        return result
    if any(
        evidence.get(key) != artifact.get(key)
        for key in ("claim_hash", "profile_hash", "obligation_hash")
    ):
        if not evidence:
            result["status"] = "OBLIGATION_FAILED"
            result["missing_evidence"] = list(FIELDS)
        return result
    checks = evidence.get("checks", {})
    if not isinstance(checks, dict):
        result["status"] = "OBLIGATION_FAILED"
        result["missing_evidence"] = list(FIELDS)
        return result
    missing = [
        field
        for field in FIELDS
        if not isinstance(checks.get(field), dict)
        or checks[field].get("status") != "OBSERVED"
        or HASH_RE.fullmatch(str(checks[field].get("evidence_hash", ""))) is None
        or not isinstance(checks[field].get("summary"), str)
        or not checks[field]["summary"].strip()
    ]
    result["missing_evidence"] = missing
    result["status"] = (
        "OBLIGATION_VERIFIED"
        if not missing
        else (
            "OBLIGATION_CONDITIONAL"
            if len(missing) < len(FIELDS)
            else "OBLIGATION_FAILED"
        )
    )
    return result


def check_obligation(
    artifact: dict[str, Any],
    evidence: dict[str, Any],
    *,
    producer_id: str,
    checker_id: str,
    **_untrusted_authority: Any,
) -> dict[str, Any]:
    if not isinstance(artifact, dict) or not isinstance(evidence, dict):
        return {**_base("OBLIGATION_REJECTED", False), "error_code": "INVALID_INPUT_TYPE", "checker_id": checker_id, "missing_evidence": []}
    result = {
        **_base("OBLIGATION_REJECTED", bool(artifact.get("required"))),
        "checker_id": checker_id,
        "missing_evidence": [],
        "error_code": "UNTRUSTED_CHECK_CONTEXT",
    }
    return result


def derive_project_obligation(
    project_dir: Path | str, claim_id: str, *, producer_id: str
) -> dict[str, Any]:
    try:
        authority_context = _load_authority_context(project_dir, claim_id)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        return {
            **_base("OBLIGATION_REJECTED", False),
            "error_code": "UNTRUSTED_CHECK_CONTEXT",
            "reason": type(exc).__name__,
        }
    return _derive_obligation_with_context(
        authority_context,
        producer_id=producer_id,
    )


def check_project_obligation(
    project_dir: Path | str,
    claim_id: str,
    artifact: dict[str, Any],
    evidence: dict[str, Any],
    *,
    producer_id: str,
    checker_id: str,
) -> dict[str, Any]:
    try:
        authority_context = _load_authority_context(project_dir, claim_id)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        return {
            **_base("OBLIGATION_REJECTED", False),
            "error_code": "UNTRUSTED_CHECK_CONTEXT",
            "reason": type(exc).__name__,
            "checker_id": checker_id,
            "missing_evidence": [],
        }
    return _check_obligation_with_context(
        artifact,
        evidence,
        producer_id=producer_id,
        checker_id=checker_id,
        authority_context=authority_context,
    )
