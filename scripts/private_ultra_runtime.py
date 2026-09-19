#!/usr/bin/env python3
"""Validate and resolve V4's optional behavior-qualified private provider overlay."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SKILL_VERSION = "4.0.0"
ROOT = Path(__file__).resolve().parents[1]
CANDIDATES_PATH = ROOT / "assets" / "registry" / "private_ultra_candidates.json"
TEAM_PATH = ROOT / "references" / "private-ultra" / "team.json"
MODES = {"PUBLIC_CORE", "PRIVATE_ULTRA"}
CRITICALITIES = {"low", "medium", "high", "critical"}
COMPARISONS = {"EXTERNAL_BETTER", "TIE", "INTERNAL_BETTER"}
SELECTION_OUTCOMES = {
    "SINGLE_PRIMARY",
    "ENSEMBLE_COMPLEMENTARY",
    "EXTERNAL_BETTER",
    "INTERNAL_BETTER",
    "NO_QUALIFIED_PROVIDER",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ARTIFACT_SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ROLE_IDS = {
    "research-director",
    "literature-evidence",
    "innovation-prior-art",
    "theory-mechanism",
    "data-dataset",
    "experimental-design",
    "research-engineering-compute",
    "implementation",
    "statistics",
    "scientific-visualization",
    "scientific-writing",
    "reproducibility-integrity",
    "adversarial-review-board",
    "publication-editor",
}


class PrivateUltraError(RuntimeError):
    pass


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PrivateUltraError(f"cannot read registry: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PrivateUltraError(f"registry root must be an object: {path}")
    return value


def load_candidates(path: Path | None = None) -> dict[str, Any]:
    return _read(path or CANDIDATES_PATH)


def load_team(path: Path | None = None) -> dict[str, Any]:
    return _read(path or TEAM_PATH)


def validate_candidates(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["candidate registry must be an object"]
    findings: list[str] = []
    if value.get("skill_version") != SKILL_VERSION:
        findings.append(f"skill_version must be {SKILL_VERSION}")
    policy = value.get("quality_policy")
    if not isinstance(policy, dict) or policy.get("missing_behavior_evidence") != "NOT_QUALIFIED":
        findings.append("quality policy must fail closed on missing behavior evidence")
    candidates = value.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return findings + ["candidates must be a non-empty list"]
    ids: list[str] = []
    required = {
        "id",
        "kind",
        "repository",
        "exact_commit",
        "license",
        "entrypoints",
        "last_meaningful_update",
        "functional_scope",
        "required_host_capabilities",
        "real_execution_support",
        "research_rigor_mechanisms",
        "provenance_mechanisms",
        "known_limitations",
        "behavior_evidence",
        "overlaps",
        "unique_capability",
        "qualification_state",
        "redistribution_decision",
    }
    for index, item in enumerate(candidates):
        prefix = f"candidates[{index}]"
        if not isinstance(item, dict):
            findings.append(f"{prefix} must be an object")
            continue
        ids.append(str(item.get("id", "")))
        for field in sorted(required):
            if field not in item or item[field] in (None, "", []):
                findings.append(f"{prefix}.{field} is required")
        if not SHA_RE.fullmatch(str(item.get("exact_commit", ""))):
            findings.append(f"{prefix}.exact_commit must be a full lowercase SHA")
        evidence = item.get("behavior_evidence")
        if not isinstance(evidence, dict) or evidence.get("status") not in {"NOT_RUN", "PASS", "FAIL"}:
            findings.append(f"{prefix}.behavior_evidence has an invalid status")
    if len(ids) != len(set(ids)):
        findings.append("candidate ids must be unique")
    return findings


def validate_team(value: Any, candidates: dict[str, Any] | None = None) -> list[str]:
    if not isinstance(value, dict):
        return ["team registry must be an object"]
    findings: list[str] = []
    if value.get("skill_version") != SKILL_VERSION:
        findings.append(f"team skill_version must be {SKILL_VERSION}")
    if value.get("layers") != ["PUBLIC_CORE", "PRIVATE_ULTRA"]:
        findings.append("team layers must preserve PUBLIC_CORE then PRIVATE_ULTRA")
    roles = value.get("roles")
    if not isinstance(roles, list):
        return findings + ["team roles must be a list"]
    role_ids = {item.get("id") for item in roles if isinstance(item, dict)}
    if role_ids != ROLE_IDS:
        findings.append(f"fourteen-role set mismatch: {sorted(str(item) for item in role_ids)}")
    candidate_ids = {
        item.get("id")
        for item in (candidates or load_candidates()).get("candidates", [])
        if isinstance(item, dict)
    }
    for index, role in enumerate(roles):
        prefix = f"roles[{index}]"
        if not isinstance(role, dict):
            findings.append(f"{prefix} must be an object")
            continue
        for field in (
            "id",
            "name",
            "authority",
            "public_core_provider",
            "primary_candidates",
            "checker_candidates",
            "task_capabilities",
        ):
            if not role.get(field):
                findings.append(f"{prefix}.{field} is required")
        referenced = set(role.get("primary_candidates", [])) | set(role.get("complementary_candidates", [])) | set(role.get("adversarial_candidates", []))
        missing = sorted(referenced - candidate_ids)
        if missing:
            findings.append(f"{prefix} references unknown candidates: {missing}")
        for checker in role.get("checker_candidates", []):
            if not str(checker).startswith("internal-checker:") and checker not in candidate_ids:
                findings.append(f"{prefix} references unknown checker: {checker}")
    return findings


def _public_provider(role: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_id": role["public_core_provider"],
        "layer": "PUBLIC_CORE",
        "formal_eligible": True,
        "source_kind": "V4_PUBLIC_CORE",
    }


def _public_checker(role: dict[str, Any]) -> dict[str, Any]:
    internal = next(
        (item for item in role["checker_candidates"] if str(item).startswith("internal-checker:")),
        None,
    )
    if not internal:
        internal = f"internal-checker:{role['id']}-checker"
    return {"provider_id": internal, "layer": "PUBLIC_CORE", "independent_invocation_required": True}


def _qualify(
    record: Any,
    candidate: dict[str, Any] | None,
    capability: str,
    *,
    formal: bool,
) -> list[str]:
    if not isinstance(record, dict):
        return ["local provider record must be an object"]
    provider_id = str(record.get("provider_id") or record.get("candidate_id") or "<unknown>")
    findings: list[str] = []
    if candidate is None:
        return [f"{provider_id}: candidate is not in the audited registry"]
    if record.get("exact_commit") != candidate.get("exact_commit"):
        findings.append(f"{provider_id}: exact commit does not match the audit")
    if record.get("installed") is not True or not str(record.get("entrypoint", "")).strip():
        findings.append(f"{provider_id}: local entrypoint is not installed")
    if capability not in record.get("capabilities", []):
        findings.append(f"{provider_id}: requested capability is absent")
    if formal and record.get("formal_eligible") is not True:
        findings.append(f"{provider_id}: provider is not formal-eligible")
    static = record.get("static_audit")
    if not isinstance(static, dict) or static.get("status") != "PASS" or static.get("exact_commit") != candidate.get("exact_commit"):
        findings.append(f"{provider_id}: static audit is incomplete")
    evidence = record.get("behavior_evidence")
    if not isinstance(evidence, dict) or evidence.get("status") != "PASS":
        findings.append(f"{provider_id}: behavior evidence is not PASS")
        return findings
    if capability not in evidence.get("capabilities", []):
        findings.append(f"{provider_id}: behavior trial did not exercise the requested capability")
    if not evidence.get("task_id") or not ARTIFACT_SHA_RE.fullmatch(str(evidence.get("output_sha256", ""))):
        findings.append(f"{provider_id}: behavior output is not task- and hash-bound")
    if not evidence.get("producer_id") or not evidence.get("checker_id") or evidence.get("producer_id") == evidence.get("checker_id"):
        findings.append(f"{provider_id}: behavior producer and checker are not separate")
    if evidence.get("comparison_to_public_core") not in COMPARISONS:
        findings.append(f"{provider_id}: behavior comparison to PUBLIC_CORE is missing")
    if candidate.get("kind") == "SYSTEM_BENCHMARK" and record.get("adapter_qualified") is not True:
        findings.append(f"{provider_id}: system benchmark needs a qualified adapter")
    return findings


def _load_local(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    value = _read(path)
    providers = value.get("providers")
    if value.get("schema_version") != "1.0.0" or not isinstance(providers, list):
        raise PrivateUltraError("local registry must declare schema_version 1.0.0 and providers")
    return providers


def resolve(
    role_id: str,
    capability: str,
    *,
    mode: str = "PUBLIC_CORE",
    criticality: str = "medium",
    local_registry: Path | None = None,
    formal: bool = True,
    require_private: bool = False,
    candidates_path: Path | None = None,
    team_path: Path | None = None,
) -> dict[str, Any]:
    if mode not in MODES:
        raise PrivateUltraError(f"unknown mode: {mode}")
    if criticality not in CRITICALITIES:
        raise PrivateUltraError(f"unknown criticality: {criticality}")
    candidates_value = load_candidates(candidates_path)
    team_value = load_team(team_path)
    registry_findings = validate_candidates(candidates_value) + validate_team(team_value, candidates_value)
    if registry_findings:
        return {"operation": "private-ultra-resolve", "status": "FAIL", "selection_outcome": "NO_QUALIFIED_PROVIDER", "findings": registry_findings}
    role = next((item for item in team_value["roles"] if item["id"] == role_id), None)
    if role is None:
        raise PrivateUltraError(f"unknown role: {role_id}")
    fallback = _public_provider(role)
    checker = _public_checker(role)
    base = {
        "operation": "private-ultra-resolve",
        "role_id": role_id,
        "capability": capability,
        "mode": mode,
        "criticality": criticality,
        "truth_authority": team_value["truth_authority"],
        "fallback": fallback,
        "checker": checker,
    }
    if mode == "PUBLIC_CORE":
        return base | {
            "status": "PASS",
            "layer": "PUBLIC_CORE",
            "selection_outcome": "INTERNAL_BETTER",
            "primary": fallback,
            "complementary": [],
            "findings": [],
        }

    candidates = {item["id"]: item for item in candidates_value["candidates"]}
    records = _load_local(local_registry)
    qualified: dict[str, dict[str, Any]] = {}
    findings: list[str] = []
    relevant = set(role["primary_candidates"]) | set(role.get("complementary_candidates", []))
    for record in records:
        candidate_id = str(record.get("candidate_id", ""))
        if candidate_id not in relevant:
            continue
        reasons = _qualify(record, candidates.get(candidate_id), capability, formal=formal)
        if reasons:
            findings.extend(reasons)
        else:
            qualified[candidate_id] = record

    primary = fallback
    external_primary = None
    for candidate_id in role["primary_candidates"]:
        record = qualified.get(candidate_id)
        evidence = record.get("behavior_evidence", {}) if record else {}
        if record and evidence.get("comparison_to_public_core") == "EXTERNAL_BETTER":
            external_primary = record
            primary = record | {"layer": "PRIVATE_ULTRA"}
            break

    if require_private and external_primary is None:
        return base | {
            "status": "FAIL",
            "layer": "PRIVATE_ULTRA",
            "selection_outcome": "NO_QUALIFIED_PROVIDER",
            "primary": None,
            "complementary": [],
            "findings": findings + ["no behavior-qualified private primary outperformed PUBLIC_CORE"],
        }

    complementary: list[dict[str, Any]] = []
    covered = set(primary.get("capabilities", [capability]))
    if criticality in {"high", "critical"}:
        for candidate_id in role.get("complementary_candidates", []):
            record = qualified.get(candidate_id)
            if not record or record is external_primary:
                continue
            evidence = record["behavior_evidence"]
            additions = [
                item for item in evidence.get("non_redundant_capabilities", [])
                if item in role["task_capabilities"] and item not in covered
            ]
            if not additions or evidence.get("comparison_to_public_core") == "INTERNAL_BETTER":
                continue
            complementary.append(record | {"layer": "PRIVATE_ULTRA", "ensemble_value": additions})
            covered.update(additions)

    if complementary:
        outcome = "ENSEMBLE_COMPLEMENTARY"
    elif external_primary is not None:
        outcome = "EXTERNAL_BETTER"
    else:
        outcome = "INTERNAL_BETTER"
    assert outcome in SELECTION_OUTCOMES
    return base | {
        "status": "PASS",
        "layer": "PRIVATE_ULTRA" if external_primary or complementary else "PUBLIC_CORE",
        "selection_outcome": outcome,
        "comparison_outcome": "EXTERNAL_BETTER" if external_primary else "INTERNAL_BETTER",
        "primary": primary,
        "complementary": complementary,
        "findings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    route = sub.add_parser("resolve")
    route.add_argument("--role", required=True)
    route.add_argument("--capability", required=True)
    route.add_argument("--mode", choices=sorted(MODES), default="PUBLIC_CORE")
    route.add_argument("--criticality", choices=sorted(CRITICALITIES), default="medium")
    route.add_argument("--local-registry", type=Path)
    route.add_argument("--exploratory", action="store_true")
    route.add_argument("--require-private", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            findings = validate_candidates(load_candidates()) + validate_team(load_team(), load_candidates())
            result = {"operation": "private-ultra-validate", "status": "PASS" if not findings else "FAIL", "findings": findings}
        else:
            result = resolve(
                args.role,
                args.capability,
                mode=args.mode,
                criticality=args.criticality,
                local_registry=args.local_registry,
                formal=not args.exploratory,
                require_private=args.require_private,
            )
    except PrivateUltraError as exc:
        result = {"operation": args.command, "status": "ERROR", "error": str(exc)}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
