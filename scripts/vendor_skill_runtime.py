#!/usr/bin/env python3
"""Validate and load V4 vendored research Skills without network access."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VENDOR_ROOT = ROOT / "vendor" / "research-skills"
MANIFEST = VENDOR_ROOT / "THIRD_PARTY_MANIFEST.json"
PERMISSIVE_LICENSES = {"MIT", "BSD-2-CLAUSE", "BSD-3-CLAUSE", "APACHE-2.0", "ISC", "CC0-1.0"}
BLOCKED_LICENSE_TERMS = {"UNKNOWN", "NOASSERTION", "NON_COMMERCIAL", "NON-COMMERCIAL", "CC-BY-NC-4.0", "CC-BY-ND-4.0"}


class VendorSkillError(RuntimeError):
    pass


def _read_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise VendorSkillError(f"cannot read third-party manifest: {path}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("skills"), list):
        raise VendorSkillError("third-party manifest must contain a skills list")
    return value


def license_decision(license_id: str | None) -> dict[str, Any]:
    normalized = str(license_id or "").strip().upper()
    allowed = normalized in PERMISSIVE_LICENSES and not any(term in normalized for term in BLOCKED_LICENSE_TERMS)
    return {
        "status": "PASS" if allowed else "DO_NOT_VENDOR",
        "license": license_id or "UNKNOWN",
        "redistribution_allowed": allowed,
        "policy": "FAIL_CLOSED",
    }


def _safe_local(relative: str) -> Path:
    path = (VENDOR_ROOT / relative).resolve()
    try:
        path.relative_to(VENDOR_ROOT.resolve())
    except ValueError as exc:
        raise VendorSkillError(f"vendored path escapes root: {relative}") from exc
    return path


def validate_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    findings: list[str] = []
    value = _read_manifest(path)
    required = {
        "name", "repository", "source_path", "local_path", "exact_commit", "license",
        "license_file", "redistribution_allowed", "vendored_files", "modified",
        "local_modifications", "security_audit", "behavior_trial", "capabilities",
        "assigned_specialists",
    }
    names: set[str] = set()
    repositories: set[str] = set()
    for item in value["skills"]:
        name = str(item.get("name", "<unnamed>"))
        missing = required - set(item) if isinstance(item, dict) else required
        if missing:
            findings.append(f"{name}: missing fields {sorted(missing)}")
            continue
        if name in names:
            findings.append(f"{name}: duplicate name")
        names.add(name)
        repositories.add(str(item["repository"]))
        if not re.fullmatch(r"[0-9a-f]{40}", str(item["exact_commit"])):
            findings.append(f"{name}: exact_commit is not a 40-character SHA")
        decision = license_decision(item["license"])
        if decision["status"] != "PASS" or item["redistribution_allowed"] is not True:
            findings.append(f"{name}: license is not approved for redistribution")
        license_path = _safe_local(str(item["license_file"]))
        if not license_path.is_file():
            findings.append(f"{name}: license file is missing")
        if item["security_audit"].get("status") != "PASS":
            findings.append(f"{name}: security audit did not pass")
        if item["behavior_trial"].get("status") != "PASS":
            findings.append(f"{name}: behavior trial did not pass")
        skill_path = _safe_local(str(item["local_path"])) / "SKILL.md"
        if not skill_path.is_file():
            findings.append(f"{name}: SKILL.md is missing")
        listed = item.get("vendored_files", [])
        if not listed:
            findings.append(f"{name}: vendored_files is empty")
        for record in listed:
            file_path = _safe_local(str(record.get("path", "")))
            if not file_path.is_file():
                findings.append(f"{name}: vendored file missing: {record.get('path')}")
                continue
            digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if digest != record.get("sha256"):
                findings.append(f"{name}: vendored file hash mismatch: {record.get('path')}")
    notices = VENDOR_ROOT / "THIRD_PARTY_NOTICES.md"
    if not notices.is_file() or notices.stat().st_size < 200:
        findings.append("THIRD_PARTY_NOTICES.md is missing or incomplete")
    return {
        "operation": "validate-vendored-research-skills",
        "status": "PASS" if not findings else "FAIL",
        "skill_version": value.get("skill_version"),
        "vendored_skill_count": len(value["skills"]),
        "repository_count": len(repositories),
        "all_exact_shas_pinned": not any("exact_commit" in item for item in findings),
        "all_vendored_files_present": not any("vendored file" in item or "SKILL.md" in item for item in findings),
        "all_licenses_redistributable": not any("license" in item.lower() for item in findings),
        "findings": findings,
    }


def load_for_capability(capability: str, *, preferred_name: str | None = None) -> dict[str, Any]:
    value = _read_manifest()
    candidates = [item for item in value["skills"] if capability in item.get("capabilities", [])]
    if preferred_name:
        candidates.sort(key=lambda item: (item.get("name") != preferred_name, item.get("name", "")))
    if not candidates:
        return {"operation": "load-vendored-skill", "status": "UNAVAILABLE", "capability": capability}
    item = candidates[0]
    if license_decision(item.get("license"))["status"] != "PASS":
        return {"operation": "load-vendored-skill", "status": "BLOCKED", "capability": capability, "reason": "license rejected"}
    skill_path = _safe_local(str(item["local_path"])) / "SKILL.md"
    if not skill_path.is_file():
        return {"operation": "load-vendored-skill", "status": "UNAVAILABLE", "capability": capability, "reason": "SKILL.md missing"}
    actual = hashlib.sha256(skill_path.read_bytes()).hexdigest()
    listed = next((record for record in item["vendored_files"] if _safe_local(record["path"]) == skill_path), None)
    if listed is None or listed.get("sha256") != actual:
        return {"operation": "load-vendored-skill", "status": "BLOCKED", "capability": capability, "reason": "integrity mismatch"}
    return {
        "operation": "load-vendored-skill",
        "status": "PASS",
        "source_kind": "VENDORED_THIRD_PARTY_SKILL",
        "name": item["name"],
        "repository": item["repository"],
        "source_path": item["source_path"],
        "exact_commit": item["exact_commit"],
        "license": item["license"],
        "capabilities": item["capabilities"],
        "assigned_specialists": item["assigned_specialists"],
        "skill_path": str(skill_path),
        "skill_sha256": actual,
        "skill_text": skill_path.read_text(encoding="utf-8"),
        "network_used": False,
        "runtime_download": False,
        "truth_authority": "CONTROL_PLANE_CHECKER",
    }

