#!/usr/bin/env python3
"""Deterministic, fail-closed V4.1 publication profile resolution."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


LAYER_ORDER = (
    "fallback", "domain", "study_type", "claim_type", "venue", "article_type", "design"
)
CATEGORIES = ("required", "recommended", "not_applicable")
RESEARCH_SCOPE_KEYS = {
    "domain", "study_type", "claim_type", "venue", "article_type", "design"
}
SOURCE_HASH_RE = re.compile(r"^[0-9a-fA-F]{64}$")
OVERRIDE_PROVENANCE_FIELDS = {"source_id", "source_hash", "profile_version"}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _conflict(code: str, dimension: str = "", **details: Any) -> dict[str, Any]:
    return {"code": code, "dimension": dimension, **details}


def _scope_matches(scope: Any, request: dict[str, Any]) -> bool:
    return isinstance(scope, dict) and all(
        request.get(key) == value for key, value in scope.items()
    )


def _normalized_strings(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        return None
    return sorted(set(value))


def _override_payload(override: Any) -> Any:
    if not isinstance(override, dict):
        return override
    normalized = {
        str(key): value
        for key, value in override.items()
        if key not in OVERRIDE_PROVENANCE_FIELDS
        and key not in {"layer_rank", "scope_specificity"}
    }
    if isinstance(normalized.get("scope"), dict):
        normalized["scope"] = {
            str(key): value for key, value in sorted(normalized["scope"].items())
        }
    return normalized


def _override_sort_key(override: Any) -> str:
    return json.dumps(
        _override_payload(override),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _effective_payload(profile: dict[str, Any]) -> dict[str, Any] | None:
    categories: dict[str, list[str]] = {}
    for category in CATEGORIES:
        normalized = _normalized_strings(profile.get(category, []))
        if normalized is None:
            return None
        categories[category] = normalized
    overrides = profile.get("overrides", [])
    if not isinstance(overrides, list):
        return None
    payload: dict[str, Any] = {
        **categories,
        "overrides": sorted(
            (_override_payload(item) for item in overrides), key=_override_sort_key
        ),
    }
    if "na_justifications" in profile:
        justifications = profile.get("na_justifications")
        if not isinstance(justifications, dict):
            return None
        payload["na_justifications"] = {
            str(key): value for key, value in sorted(justifications.items())
        }
    return payload


def _normalize_profile(profile: Any) -> dict[str, Any]:
    if not isinstance(profile, dict):
        return {"invalid_profile": profile}
    normalized = {str(key): value for key, value in profile.items()}
    for category in CATEGORIES:
        values = _normalized_strings(normalized.get(category, []))
        normalized[category] = values if values is not None else normalized.get(category)
    if isinstance(normalized.get("scope"), dict):
        normalized["scope"] = {
            str(key): value for key, value in sorted(normalized["scope"].items())
        }
    if isinstance(normalized.get("source_hash"), str):
        normalized["source_hash"] = normalized["source_hash"].lower()
    if isinstance(normalized.get("na_justifications"), dict):
        normalized["na_justifications"] = {
            str(key): value
            for key, value in sorted(normalized["na_justifications"].items())
        }
    if isinstance(normalized.get("overrides"), list):
        overrides = []
        for item in normalized["overrides"]:
            if not isinstance(item, dict):
                overrides.append(item)
                continue
            value = {str(key): entry for key, entry in item.items()}
            if isinstance(value.get("scope"), dict):
                value["scope"] = {
                    str(key): entry for key, entry in sorted(value["scope"].items())
                }
            if isinstance(value.get("source_hash"), str):
                value["source_hash"] = value["source_hash"].lower()
            overrides.append(value)
        normalized["overrides"] = sorted(overrides, key=_override_sort_key)
    payload = normalized.get("source_payload")
    if isinstance(payload, dict):
        normalized_payload = _effective_payload(payload)
        normalized["source_payload"] = (
            normalized_payload if normalized_payload is not None else payload
        )
    return normalized


def _profile_sort_key(profile: dict[str, Any]) -> tuple[int, int, str, str]:
    layer = str(profile.get("layer", ""))
    rank = LAYER_ORDER.index(layer) if layer in LAYER_ORDER else len(LAYER_ORDER)
    scope = profile.get("scope")
    scope_specificity = len(scope) if isinstance(scope, dict) else 0
    return rank, scope_specificity, str(profile.get("profile_id", "")), canonical_hash(profile)


def _validate_profile_source(
    profile: dict[str, Any], conflicts: list[dict[str, Any]]
) -> None:
    profile_id = str(profile.get("profile_id", ""))
    status = profile.get("status")
    if status == "PROFILE_DEPRECATED":
        conflicts.append(_conflict("PROFILE_DEPRECATED", profile_id=profile_id))
    elif status != "PROFILE_ACTIVE":
        conflicts.append(_conflict("INVALID_PROFILE_STATUS", profile_id=profile_id))
    source_hash = profile.get("source_hash")
    if not isinstance(source_hash, str) or not SOURCE_HASH_RE.fullmatch(source_hash):
        conflicts.append(_conflict("INVALID_SOURCE_HASH", profile_id=profile_id))
        return
    payload = profile.get("source_payload")
    if not isinstance(payload, dict):
        conflicts.append(_conflict("MISSING_SOURCE_PAYLOAD", profile_id=profile_id))
        return
    effective = _effective_payload(profile)
    normalized_payload = _effective_payload(payload)
    if effective is None or normalized_payload is None:
        conflicts.append(_conflict("INVALID_SOURCE_PAYLOAD", profile_id=profile_id))
        return
    if normalized_payload != effective:
        conflicts.append(_conflict("SOURCE_PAYLOAD_MISMATCH", profile_id=profile_id))
    if canonical_hash(normalized_payload).lower() != source_hash.lower():
        conflicts.append(_conflict("STALE_SOURCE_HASH", profile_id=profile_id))
    provenance = profile.get("provenance")
    if not isinstance(provenance, dict):
        conflicts.append(_conflict("MISSING_PROFILE_PROVENANCE", profile_id=profile_id))
        return
    provenance_hash = provenance.get("source_hash")
    if (
        set(provenance) != {"source_id", "source_hash", "profile_version"}
        or
        provenance.get("source_id") != profile_id
        or provenance.get("profile_version") != profile.get("version")
        or not isinstance(provenance_hash, str)
        or not SOURCE_HASH_RE.fullmatch(provenance_hash)
        or provenance_hash.lower() != source_hash.lower()
    ):
        conflicts.append(_conflict("PROFILE_PROVENANCE_MISMATCH", profile_id=profile_id))


def _validate_override(
    profile: dict[str, Any],
    override: Any,
    layer_rank: int,
    request: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if not isinstance(override, dict):
        return None, [_conflict("INVALID_OVERRIDE", profile_id=profile.get("profile_id", ""))]
    dimension = override.get("dimension")
    source = override.get("from")
    target = override.get("to")
    justification = override.get("justification")
    scope = override.get("scope")
    if (
        not isinstance(dimension, str)
        or not dimension
        or source not in CATEGORIES
        or target not in CATEGORIES
        or not isinstance(justification, str)
        or not justification.strip()
        or not isinstance(scope, dict)
    ):
        return None, [_conflict("INVALID_OVERRIDE", str(dimension or ""), layer=layer_rank)]
    if not _scope_matches(scope, request):
        return None, []
    conflicts: list[dict[str, Any]] = []
    if source == "required" and target == "not_applicable":
        if not scope or not set(scope).issubset(RESEARCH_SCOPE_KEYS):
            conflicts.append(
                _conflict("INVALID_NOT_APPLICABLE_SCOPE", dimension, scope=scope)
            )
    source_hash = override.get("source_hash")
    if (
        override.get("source_id") != profile.get("profile_id")
        or override.get("profile_version") != profile.get("version")
        or not isinstance(source_hash, str)
        or not SOURCE_HASH_RE.fullmatch(source_hash)
        or source_hash.lower() != str(profile.get("source_hash", "")).lower()
    ):
        conflicts.append(_conflict("OVERRIDE_SOURCE_MISMATCH", dimension))
    normalized = {
        **override,
        "justification": justification.strip(),
        "scope": {str(key): value for key, value in sorted(scope.items())},
        "source_hash": source_hash.lower() if isinstance(source_hash, str) else source_hash,
        "layer_rank": layer_rank,
        "scope_specificity": len(scope),
    }
    return normalized, conflicts


def resolve_profile(
    request: dict[str, Any], profiles: list[dict[str, Any]]
) -> dict[str, Any]:
    """Merge selected profile layers without mutating authoritative research state."""
    if not isinstance(request, dict) or not isinstance(profiles, list):
        canonical_input = {
            "request_type": type(request).__name__,
            "profiles_type": type(profiles).__name__,
        }
        result = {
            "operation": "resolve-publication-profile",
            "status": "PROFILE_CONFLICT",
            "applied_profile_ids": [],
            "required": [],
            "recommended": [],
            "not_applicable": [],
            "na_justifications": {},
            "resolution_events": [],
            "conflicts": [_conflict("INVALID_RESOLUTION_INPUT")],
            "canonical_input": canonical_input,
            "canonical_input_hash": canonical_hash(canonical_input),
        }
        result["canonical_output_hash"] = canonical_hash(result)
        return result
    normalized_request = {str(key): value for key, value in sorted(request.items())}
    normalized_profiles = [_normalize_profile(item) for item in profiles]
    ordered = sorted(normalized_profiles, key=_profile_sort_key)
    canonical_input = {"request": normalized_request, "profiles": ordered}
    assignments = {category: set() for category in CATEGORIES}
    conflicts: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    justifications: dict[str, str] = {}
    applied: list[str] = []

    applicable = []
    for profile in ordered:
        layer = str(profile.get("layer", ""))
        profile_id = str(profile.get("profile_id", ""))
        if layer not in LAYER_ORDER or not profile_id or not str(profile.get("version", "")):
            conflicts.append(
                _conflict("INVALID_PROFILE_IDENTITY", profile_id=profile_id, layer=layer)
            )
            continue
        _validate_profile_source(profile, conflicts)
        scope = profile.get("scope")
        if scope is not None and not _scope_matches(scope, normalized_request):
            continue
        applicable.append(profile)

    if not any(profile.get("layer") == "fallback" for profile in applicable):
        conflicts.append(_conflict("MISSING_FALLBACK"))

    for layer_rank, layer in enumerate(LAYER_ORDER):
        layer_profiles = [item for item in applicable if item.get("layer") == layer]
        for profile in layer_profiles:
            profile_id = str(profile["profile_id"])
            applied.append(profile_id)
            for category in CATEGORIES:
                values = _normalized_strings(profile.get(category, []))
                if values is None:
                    conflicts.append(
                        _conflict("INVALID_DIMENSION_LIST", category=category, profile_id=profile_id)
                    )
                    continue
                assignments[category].update(values)
            profile_justifications = profile.get("na_justifications", {})
            if not isinstance(profile_justifications, dict):
                conflicts.append(_conflict("INVALID_NA_JUSTIFICATIONS", profile_id=profile_id))
            else:
                for dimension, justification in sorted(profile_justifications.items()):
                    if not isinstance(justification, str) or not justification.strip():
                        conflicts.append(
                            _conflict("INVALID_NA_JUSTIFICATION", str(dimension), profile_id=profile_id)
                        )
                        continue
                    normalized = justification.strip()
                    if dimension in justifications and justifications[dimension] != normalized:
                        conflicts.append(
                            _conflict("CONFLICTING_NA_JUSTIFICATION", str(dimension), profile_id=profile_id)
                        )
                    else:
                        justifications[str(dimension)] = normalized

        overrides: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for profile in layer_profiles:
            raw_overrides = profile.get("overrides", [])
            if not isinstance(raw_overrides, list):
                conflicts.append(_conflict("INVALID_OVERRIDE_LIST", profile_id=profile["profile_id"]))
                continue
            for raw in raw_overrides:
                override, errors = _validate_override(profile, raw, layer_rank, normalized_request)
                conflicts.extend(errors)
                if override is not None:
                    overrides.append((profile, override))

        ambiguity: dict[tuple[int, str, str], set[str]] = {}
        for _, override in overrides:
            key = (
                override["scope_specificity"], override["dimension"], override["from"]
            )
            ambiguity.setdefault(key, set()).add(override["to"])
        ambiguous_keys = {key for key, targets in ambiguity.items() if len(targets) > 1}
        for specificity, dimension, source in sorted(ambiguous_keys):
            conflicts.append(
                _conflict(
                    "AMBIGUOUS_OVERRIDE",
                    dimension,
                    layer=layer_rank,
                    scope_specificity=specificity,
                    source=source,
                    targets=sorted(ambiguity[(specificity, dimension, source)]),
                )
            )

        overrides.sort(
            key=lambda item: (
                item[1]["scope_specificity"],
                item[1]["dimension"],
                str(item[0]["profile_id"]),
                _override_sort_key(item[1]),
            )
        )
        for owner, override in overrides:
            ambiguity_key = (
                override["scope_specificity"], override["dimension"], override["from"]
            )
            if ambiguity_key in ambiguous_keys:
                continue
            dimension = override["dimension"]
            source = override["from"]
            target = override["to"]
            if dimension not in assignments[source]:
                conflicts.append(_conflict("OVERRIDE_SOURCE_MISMATCH", dimension, expected=source))
                continue
            assignments[source].discard(dimension)
            assignments[target].add(dimension)
            if target == "not_applicable":
                justifications[dimension] = override["justification"]
            elif source == "not_applicable":
                justifications.pop(dimension, None)
            events.append(
                {
                    "dimension": dimension,
                    "from": source,
                    "to": target,
                    "justification": override["justification"],
                    "layer": layer,
                    "specificity": layer_rank,
                    "scope_specificity": override["scope_specificity"],
                    "source_id": override["source_id"],
                    "profile_version": override["profile_version"],
                }
            )

    for dimension in sorted(set().union(*assignments.values())):
        categories = [category for category in CATEGORIES if dimension in assignments[category]]
        if len(categories) > 1:
            conflicts.append(_conflict("CROSS_CATEGORY_ASSIGNMENT", dimension, categories=categories))
    for dimension in sorted(assignments["not_applicable"]):
        if not justifications.get(dimension):
            conflicts.append(_conflict("UNJUSTIFIED_NOT_APPLICABLE", dimension))

    result: dict[str, Any] = {
        "operation": "resolve-publication-profile",
        "status": "PROFILE_CONFLICT" if conflicts else "PROFILE_RESOLVED",
        "applied_profile_ids": applied,
        "required": sorted(assignments["required"]),
        "recommended": sorted(assignments["recommended"]),
        "not_applicable": sorted(assignments["not_applicable"]),
        "na_justifications": {
            key: justifications[key]
            for key in sorted(assignments["not_applicable"])
            if key in justifications
        },
        "resolution_events": sorted(
            events,
            key=lambda item: (
                item["specificity"], item["scope_specificity"], item["dimension"], item["source_id"]
            ),
        ),
        "conflicts": sorted(
            conflicts,
            key=lambda item: (
                item["code"], item.get("dimension", ""), json.dumps(item, sort_keys=True)
            ),
        ),
        "canonical_input": canonical_input,
        "canonical_input_hash": canonical_hash(canonical_input),
    }
    for field in RESEARCH_SCOPE_KEYS:
        if field in normalized_request:
            result[field] = normalized_request[field]
    result["canonical_output_hash"] = canonical_hash(result)
    return result
