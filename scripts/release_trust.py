#!/usr/bin/env python3
"""Verify the fixed V4.1 release trust record and its constrained files."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRUST_RECORD_RELATIVE_PATH = "assets/trust/v41_release_trust.json"
TRUST_RECORD_PATH = ROOT / TRUST_RECORD_RELATIVE_PATH
RELEASE_MANIFEST_PATH = ROOT / "release_manifest.json"
TRUST_RECORD_SHA256 = "sha256:d61f6d55c8dc60db73e7af74521b950ddb2a81b4616353a55468fa428aa1853d"
HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
EXPECTED_TRUSTED_PATHS = {
    "assets/registry/publication_profiles.json",
    "assets/registry/v41_provider_qualification.json",
    "assets/registry/v41_provider_registry.json",
}


def _canonical_file_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _safe_path(relative_path: str) -> Path | None:
    if not isinstance(relative_path, str) or not relative_path:
        return None
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    resolved = (ROOT / candidate).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return resolved


def _verified_state() -> tuple[dict[str, Any] | None, dict[str, bytes], list[str]]:
    findings: list[str] = []
    payloads: dict[str, bytes] = {}
    if TRUST_RECORD_PATH.is_symlink() or not TRUST_RECORD_PATH.is_file():
        return None, payloads, ["TRUST_RECORD_UNAVAILABLE"]
    try:
        trust_bytes = _canonical_file_bytes(TRUST_RECORD_PATH)
    except OSError:
        return None, payloads, ["TRUST_RECORD_UNAVAILABLE"]
    if _digest(trust_bytes) != TRUST_RECORD_SHA256:
        return None, payloads, ["TRUST_RECORD_ANCHOR_MISMATCH"]
    try:
        trust = json.loads(trust_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, payloads, ["TRUST_RECORD_INVALID_JSON"]
    if not isinstance(trust, dict):
        return None, payloads, ["TRUST_RECORD_INVALID_TYPE"]
    if (
        trust.get("schema_version") != 1
        or trust.get("trust_root_id") != "v4.1-release-root-2026-09-19"
        or trust.get("release_line") != "4.1"
    ):
        findings.append("TRUST_RECORD_IDENTITY_MISMATCH")
    rotation = trust.get("rotation_policy")
    if rotation != {
        "runtime_override_allowed": False,
        "caller_supplied_root_allowed": False,
        "anchor_change_requires_code_review": True,
    }:
        findings.append("TRUST_RECORD_ROTATION_POLICY_MISMATCH")
    trusted_files = trust.get("trusted_files")
    if not isinstance(trusted_files, dict):
        findings.append("TRUST_RECORD_FILE_MAP_INVALID")
        trusted_files = {}
    if set(trusted_files) != EXPECTED_TRUSTED_PATHS:
        findings.append("TRUST_RECORD_SCOPE_MISMATCH")
    for relative_path in sorted(EXPECTED_TRUSTED_PATHS):
        expected = trusted_files.get(relative_path)
        path = _safe_path(relative_path)
        if HASH_RE.fullmatch(str(expected)) is None:
            findings.append(f"TRUSTED_FILE_DIGEST_INVALID: {relative_path}")
            continue
        if path is None or path.is_symlink() or not path.is_file():
            findings.append(f"TRUSTED_FILE_UNAVAILABLE: {relative_path}")
            continue
        try:
            payload = _canonical_file_bytes(path)
        except OSError:
            findings.append(f"TRUSTED_FILE_UNAVAILABLE: {relative_path}")
            continue
        if _digest(payload) != expected:
            findings.append(f"TRUSTED_FILE_DIGEST_MISMATCH: {relative_path}")
            continue
        payloads[relative_path] = payload
    constraints = trust.get("release_constraints")
    if not isinstance(constraints, dict):
        findings.append("RELEASE_CONSTRAINTS_INVALID")
    else:
        try:
            release = json.loads(RELEASE_MANIFEST_PATH.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            release = None
        if not isinstance(release, dict):
            findings.append("RELEASE_MANIFEST_UNAVAILABLE")
        else:
            benchmark = release.get("benchmark_suite")
            observed = {
                "release_status": release.get("release_status"),
                "recommended_merge": release.get("recommended_merge"),
                "model_behavior_eval": release.get("model_behavior_eval"),
                "benchmark_status": benchmark.get("status")
                if isinstance(benchmark, dict)
                else None,
            }
            for field, value in observed.items():
                allowed = constraints.get(field)
                if not isinstance(allowed, list) or value not in allowed:
                    findings.append(f"RELEASE_CONSTRAINT_VIOLATION: {field}")
    return trust, payloads, findings


def validate_release_trust() -> dict[str, Any]:
    trust, payloads, findings = _verified_state()
    return {
        "operation": "validate-v41-release-trust",
        "status": "PASS" if trust is not None and not findings else "FAIL",
        "trust_root_id": trust.get("trust_root_id") if isinstance(trust, dict) else None,
        "anchor": TRUST_RECORD_SHA256,
        "verified_files": sorted(payloads),
        "findings": findings,
    }


def load_trusted_json(relative_path: str) -> dict[str, Any] | None:
    if relative_path not in EXPECTED_TRUSTED_PATHS:
        return None
    trust, payloads, findings = _verified_state()
    if trust is None or findings or relative_path not in payloads:
        return None
    try:
        value = json.loads(payloads[relative_path].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None
