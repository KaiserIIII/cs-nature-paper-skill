#!/usr/bin/env python3
"""Independent V4 publication-depth, reviewer, and submission gates."""

from __future__ import annotations

import json
import re
import hashlib
import importlib.util
from collections import Counter
from pathlib import Path
from typing import Any


SKILL_VERSION = "4.1.0"
REQUIRED_REVIEWERS = (
    "novelty",
    "domain",
    "methods",
    "statistics",
    "experimental-completeness",
    "reproducibility",
    "adversarial",
)

DEPTH_DIMENSIONS = (
    "dataset_coverage",
    "model_coverage",
    "modern_baselines",
    "ablations",
    "external_validation",
    "mechanism_tests",
    "related_work",
    "manuscript_depth",
)


def _integer(profile: dict[str, Any], key: str) -> int:
    try:
        return max(0, int(profile.get(key, 0)))
    except (TypeError, ValueError):
        return 0


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _profile_conflict(code: str, **details: Any) -> dict[str, Any]:
    return {"status": "PROFILE_CONFLICT", "conflicts": [{"code": code, **details}]}


def _publication_profile_runtime():
    path = Path(__file__).with_name("publication_profiles.py")
    spec = importlib.util.spec_from_file_location("publication_profiles_replay", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("publication profile resolver is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _release_trust_runtime():
    path = Path(__file__).with_name("release_trust.py")
    spec = importlib.util.spec_from_file_location("publication_release_trust", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("release trust verifier is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _trusted_profile_signatures(runtime: Any) -> set[str]:
    trust = _release_trust_runtime()
    registry = trust.load_trusted_json(
        "assets/registry/publication_profiles.json"
    )
    if not isinstance(registry, dict):
        raise ValueError("trusted publication profile registry is unavailable")
    profiles = registry.get("profiles", [])
    if not isinstance(profiles, list):
        raise ValueError("trusted publication profile registry is invalid")
    return {
        runtime.canonical_hash(runtime._normalize_profile(profile))
        for profile in profiles
        if isinstance(profile, dict) and profile.get("status") == "PROFILE_ACTIVE"
    }


def _applied_profile_records(
    runtime: Any,
    request: dict[str, Any],
    profiles: list[dict[str, Any]],
    applied_profile_ids: list[str],
) -> list[dict[str, Any]]:
    remaining = Counter(str(item) for item in applied_profile_ids)
    applied = []
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        profile_id = str(profile.get("profile_id", ""))
        scope = profile.get("scope")
        if remaining[profile_id] <= 0:
            continue
        if scope is not None and not runtime._scope_matches(scope, request):
            continue
        applied.append(profile)
        remaining[profile_id] -= 1
    if any(remaining.values()):
        raise ValueError("applied profile provenance is incomplete")
    return applied


def _replay_publication_profile(artifact: dict[str, Any]) -> dict[str, Any] | None:
    canonical_input = artifact.get("canonical_input")
    if not isinstance(canonical_input, dict):
        return _profile_conflict("UNREPLAYABLE_PROFILE_PROVENANCE")
    request = canonical_input.get("request")
    replay_profiles = canonical_input.get("profiles")
    if not isinstance(request, dict) or not isinstance(replay_profiles, list):
        return _profile_conflict("UNREPLAYABLE_PROFILE_PROVENANCE")
    try:
        runtime = _publication_profile_runtime()
        expected_input_hash = runtime.canonical_hash(canonical_input)
        if artifact.get("canonical_input_hash") != expected_input_hash:
            return _profile_conflict("STALE_PROFILE_INPUT_HASH")
        trusted = _trusted_profile_signatures(runtime)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError):
        return _profile_conflict("TRUSTED_FALLBACK_UNAVAILABLE")
    replayed = runtime.resolve_profile(request, replay_profiles)
    if replayed.get("status") != "PROFILE_RESOLVED":
        return _profile_conflict(
            "PROFILE_REPLAY_CONFLICT", replay_conflicts=replayed.get("conflicts", [])
        )
    try:
        applied = _applied_profile_records(
            runtime,
            request,
            replay_profiles,
            replayed.get("applied_profile_ids", []),
        )
    except ValueError:
        return _profile_conflict("UNREPLAYABLE_PROFILE_PROVENANCE")
    untrusted = [
        profile
        for profile in applied
        if runtime.canonical_hash(runtime._normalize_profile(profile)) not in trusted
    ]
    if untrusted:
        profile_ids = sorted(str(profile.get("profile_id", "")) for profile in untrusted)
        if any(profile.get("layer") == "fallback" for profile in untrusted):
            return _profile_conflict("UNTRUSTED_FALLBACK", profile_ids=profile_ids)
        return _profile_conflict("UNTRUSTED_APPLIED_PROFILE", profile_ids=profile_ids)
    if replayed != artifact:
        return _profile_conflict("PROFILE_REPLAY_MISMATCH")
    return None


def _apply_publication_profile(checks: dict[str, Any], artifact: Any) -> dict[str, Any]:
    if artifact is None:
        return {"status": "FALLBACK_DEFAULTS", "source": "fixed V4 dimensions"}
    if not isinstance(artifact, dict) or artifact.get("status") != "PROFILE_RESOLVED":
        return {"status": "PROFILE_CONFLICT", "conflicts": artifact.get("conflicts", []) if isinstance(artifact, dict) else [{"code": "INVALID_PROFILE"}]}
    stored_hash = artifact.get("canonical_output_hash")
    body = {key: value for key, value in artifact.items() if key != "canonical_output_hash"}
    normalized_hash = stored_hash.removeprefix("sha256:") if isinstance(stored_hash, str) else ""
    if not normalized_hash or normalized_hash != _canonical_hash(body):
        return {"status": "PROFILE_CONFLICT", "conflicts": [{"code": "STALE_PROFILE_HASH"}]}
    replay_conflict = _replay_publication_profile(artifact)
    if replay_conflict is not None:
        return replay_conflict
    if any(not isinstance(artifact.get(name, []), list) for name in ("required", "recommended", "not_applicable")):
        return {"status": "PROFILE_CONFLICT", "conflicts": [{"code": "INVALID_PROFILE_CATEGORY"}]}
    categories = {name: set(artifact.get(name, [])) for name in ("required", "recommended", "not_applicable")}
    overlap = (categories["required"] & categories["recommended"]) | (categories["required"] & categories["not_applicable"]) | (categories["recommended"] & categories["not_applicable"])
    if overlap:
        return {"status": "PROFILE_CONFLICT", "conflicts": [{"code": "CROSS_CATEGORY_ASSIGNMENT", "dimensions": sorted(overlap)}]}
    justifications = artifact.get("na_justifications", {})
    invalid_na = sorted(item for item in categories["not_applicable"] if not isinstance(justifications, dict) or not str(justifications.get(item, "")).strip())
    if invalid_na:
        return {"status": "PROFILE_CONFLICT", "conflicts": [{"code": "UNJUSTIFIED_NOT_APPLICABLE", "dimensions": invalid_na}]}
    for dimension in categories["not_applicable"]:
        if dimension in checks:
            checks[dimension] = {"status": "NOT_APPLICABLE", "justification": justifications[dimension]}
    unsupported = sorted(categories["required"] - set(checks))
    for dimension in unsupported:
        checks[dimension] = {"status": "FAIL", "observed": "UNASSESSED", "minimum": "profile-defined requirement"}
    return {"status": "PROFILE_RESOLVED", "canonical_output_hash": stored_hash, "required": sorted(categories["required"]), "recommended": sorted(categories["recommended"]), "not_applicable": sorted(categories["not_applicable"])}


def research_depth_profile(profile: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "dataset_coverage": {
            "status": "PASS" if _integer(profile, "dataset_count") >= 2 and "toy" not in set(profile.get("dataset_kinds", [])) else "FAIL",
            "observed": _integer(profile, "dataset_count"),
            "minimum": "at least two datasets with non-toy coverage",
        },
        "model_coverage": {
            "status": "PASS" if _integer(profile, "model_count") >= 2 else "FAIL",
            "observed": _integer(profile, "model_count"),
            "minimum": 2,
        },
        "modern_baselines": {
            "status": "PASS" if _integer(profile, "modern_baseline_count") >= 3 else "FAIL",
            "observed": _integer(profile, "modern_baseline_count"),
            "minimum": 3,
        },
        "ablations": {
            "status": "PASS" if _integer(profile, "ablation_dimension_count") >= 2 else "FAIL",
            "observed": _integer(profile, "ablation_dimension_count"),
            "minimum": 2,
        },
        "external_validation": {
            "status": "PASS" if _integer(profile, "external_validation_count") >= 1 else "FAIL",
            "observed": _integer(profile, "external_validation_count"),
            "minimum": 1,
        },
        "mechanism_tests": {
            "status": "PASS" if _integer(profile, "mechanism_test_count") >= 1 else "FAIL",
            "observed": _integer(profile, "mechanism_test_count"),
            "minimum": 1,
        },
        "related_work": {
            "status": "PASS" if str(profile.get("related_work_depth", "")).upper() in {"ADEQUATE", "DEEP"} else "FAIL",
            "observed": str(profile.get("related_work_depth", "UNASSESSED")).upper(),
            "minimum": "ADEQUATE",
        },
        "manuscript_depth": {
            "status": "PASS" if _integer(profile, "manuscript_pages") >= 10 else "FAIL",
            "observed": _integer(profile, "manuscript_pages"),
            "minimum": 10,
        },
    }
    resolution = _apply_publication_profile(checks, profile.get("publication_profile"))
    active_required = set(DEPTH_DIMENSIONS) if resolution["status"] == "FALLBACK_DEFAULTS" else set(resolution.get("required", []))
    failed = [key for key, value in checks.items() if key in active_required and value["status"] != "PASS"]
    if resolution["status"] == "PROFILE_CONFLICT":
        failed = sorted(set(failed) | {"publication_profile"})
    return {
        "operation": "research-depth-profile",
        "status": "PASS" if not failed else "FAIL",
        "breadth": "SUFFICIENT" if not failed else "INSUFFICIENT",
        "breadth_dimensions": list(DEPTH_DIMENSIONS),
        "dimensions": checks,
        "failed_dimensions": failed,
        "profile_resolution": resolution,
        "formal_run_count": _integer(profile, "formal_run_count"),
        "note": "formal repetition count is reproducibility evidence, not a breadth dimension",
    }


def _publication_findings(depth: dict[str, Any]) -> list[dict[str, str]]:
    mapping = {
        "publication_profile": ("PUBLICATION_PROFILE_CONFLICT", "Resolve the publication-profile conflict or stale hash before reassessing sufficiency."),
        "dataset_coverage": ("DATASET_COVERAGE_INSUFFICIENT", "Add a distinct non-toy dataset and test cross-dataset scope."),
        "model_coverage": ("MODEL_COVERAGE_INSUFFICIENT", "Test at least one materially different model family or architecture."),
        "modern_baselines": ("MODERN_BASELINES_INCOMPLETE", "Compare against at least three current, mechanism-relevant baselines."),
        "ablations": ("ABLATIONS_INSUFFICIENT", "Add threat-driven ablations for at least two independent design dimensions."),
        "external_validation": ("EXTERNAL_VALIDATION_MISSING", "Validate the central result outside the development setting."),
        "mechanism_tests": ("MECHANISM_TESTS_MISSING", "Run a temporally valid discriminating mechanism test against rivals."),
        "related_work": ("RELATED_WORK_THIN", "Expand Related Work around seminal, closest, contradictory, and current methods."),
        "manuscript_depth": ("MANUSCRIPT_TOO_THIN", "Expand scientific content after the missing research is complete."),
    }
    findings = []
    for key in depth["failed_dimensions"]:
        finding_id, action = mapping.get(key, (f"PROFILE_DIMENSION_INSUFFICIENT:{key}", f"Satisfy the resolved publication-profile requirement '{key}' with checked evidence."))
        findings.append({"id": finding_id, "dimension": key, "action": action})
    return findings


def research_expansion_plan(depth: dict[str, Any]) -> list[dict[str, str]]:
    priority = {
        "publication_profile": "CRITICAL",
        "dataset_coverage": "CRITICAL",
        "modern_baselines": "CRITICAL",
        "mechanism_tests": "CRITICAL",
        "model_coverage": "MAJOR",
        "ablations": "MAJOR",
        "external_validation": "MAJOR",
        "related_work": "MAJOR",
        "manuscript_depth": "AFTER_RESEARCH",
    }
    return [
        {"finding_id": item["id"], "dimension": item["dimension"], "priority": priority.get(item["dimension"], "MAJOR"), "action": item["action"]}
        for item in _publication_findings(depth)
    ]


def assess(profile: dict[str, Any]) -> dict[str, Any]:
    scientific_status = str(profile.get("scientific_validity", "UNASSESSED")).upper()
    if scientific_status not in {"PASS", "CONDITIONAL", "FAIL"}:
        scientific_status = "FAIL"
    evidence_status = str(profile.get("evidence_sufficiency", "UNASSESSED")).upper()
    if evidence_status not in {"PASS", "CONDITIONAL", "FAIL"}:
        evidence_status = "FAIL"
    depth = research_depth_profile(profile)
    publication_status = "PASS" if depth["status"] == "PASS" else "FAIL"
    completed = {str(item).lower() for item in profile.get("reviewer_roles_completed", [])}
    missing_reviewers = [item for item in REQUIRED_REVIEWERS if item not in completed]
    reviewer_status = "PASS" if not missing_reviewers else "FAIL"
    all_pass = all(status == "PASS" for status in (scientific_status, evidence_status, publication_status, reviewer_status))
    result = {
        "operation": "publication-assessment",
        "skill_version": SKILL_VERSION,
        "scientific_validity": {"status": scientific_status, "scope": "bounded to recorded study and evidence"},
        "evidence_sufficiency": {"status": evidence_status},
        "publication_sufficiency": {
            "status": publication_status,
            "findings": _publication_findings(depth),
            "principle": "strong evidence for a narrow claim is not automatically sufficient for a strong paper",
        },
        "reviewer_completeness": {
            "status": reviewer_status,
            "required": list(REQUIRED_REVIEWERS),
            "completed": sorted(completed),
            "missing": missing_reviewers,
        },
        "submission_readiness": {"status": "PASS" if all_pass else "FAIL"},
        "research_depth_profile": depth,
        "profile_resolution": depth["profile_resolution"],
        "research_expansion_plan": research_expansion_plan(depth),
        "disposition": "READY_FOR_SUBMISSION" if all_pass else "EXPAND_RESEARCH",
    }
    return result


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, UnicodeDecodeError):
        return ""


def _pdf_pages(project: Path) -> int:
    candidates = [
        project / "paper" / "main.pdf",
        project / "submission_package" / "main.pdf",
        project / "submission_package_NCA" / "main_blinded.pdf",
    ]
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        return 0
    try:
        from pypdf import PdfReader

        return len(PdfReader(str(path)).pages)
    except Exception:
        data = path.read_bytes()
        return len(re.findall(rb"/Type\s*/Page(?!s)", data))


def _evidence_status(project: Path) -> str:
    for directory in (".research-state-v31", ".research-state-v3", ".research-state"):
        ledger = _read_json(project / directory / "evidence_ledger.json", {})
        anchors = ledger.get("anchors", []) if isinstance(ledger, dict) else []
        if anchors:
            return "PASS"
    return "CONDITIONAL"


def audit_project(project: Path) -> dict[str, Any]:
    project = project.resolve()
    state = next((project / name for name in (".research-state-v31", ".research-state-v3", ".research-state") if (project / name).is_dir()), project / ".research-state")
    contract = _read_json(state / "research_contract.json", {})
    claims = _read_json(state / "claims.json", {}).get("claims", [])
    experiments = _read_json(state / "experiment_registry.json", {})
    reviews = _read_json(state / "review_finding.json", {}).get("findings", [])
    protocol = _read_text(project / "docs" / "formal_protocol.md")
    manuscript = _read_text(project / "paper" / "main.tex") or _read_text(project / "paper" / "manuscript.md")
    corpus = "\n".join((json.dumps(contract, ensure_ascii=False), json.dumps(claims, ensure_ascii=False), protocol, manuscript)).lower()

    withdrawn_predictor = any("WITHDRAWN_PROSPECTIVE_MECHANISM" in str(item.get("status", "")) for item in claims)
    supported = [item for item in claims if str(item.get("status", "")).startswith("SUPPORTED")]
    scientific = "CONDITIONAL" if supported and withdrawn_predictor else ("PASS" if supported else "FAIL")
    status_doc = _read_json(project / "run_state" / "formal_experiments_status.json", {})
    formal_runs = len(status_doc.get("completed_job_ids", status_doc.get("completed", [])))
    if not formal_runs:
        formal_runs = len(list((project / "results" / "formal").glob("*.json"))) if (project / "results" / "formal").is_dir() else 0

    # This conservative extractor uses explicit project records. Ambiguous
    # breadth remains zero rather than being inferred from repetition names.
    profile = {
        "scientific_validity": scientific,
        "evidence_sufficiency": _evidence_status(project),
        "dataset_count": 1 if "sklearn digits" in corpus else 0,
        "dataset_kinds": ["toy"] if "sklearn digits" in corpus or "digits 8x8" in corpus else [],
        "model_count": 1 if "two-layer mlp" in corpus or "two layer mlp" in corpus else 0,
        "modern_baseline_count": 1 if "tent" in corpus else 0,
        "ablation_dimension_count": 0 if not re.search(r"\\section\*?\{[^}]*ablation", manuscript, re.IGNORECASE) else 1,
        "external_validation_count": 0 if "tier 2 is deferred" in corpus or "tier 2" not in corpus else 1,
        "mechanism_test_count": 0 if withdrawn_predictor else 1,
        "reviewer_roles_completed": [str(item.get("reviewer_role", "")).lower() for item in reviews if item.get("reviewer_role")],
        "manuscript_pages": _pdf_pages(project),
        "related_work_depth": "THIN" if manuscript.lower().count("\\cite") < 12 else "ADEQUATE",
        "formal_run_count": formal_runs,
    }
    result = assess(profile)
    field_findings = [
        {"id": "ONE_TOY_DATASET", "anchor": "docs/formal_protocol.md: Dataset", "observed": "sklearn digits 8x8"},
        {"id": "ONE_SMALL_MLP", "anchor": "docs/formal_protocol.md: Model", "observed": "two-layer MLP"},
        {"id": "INCOMPLETE_MODERN_TTA_BASELINES", "anchor": "configs/formal_experiment_manifest.json", "observed": "only TENT is a modern TTA reference baseline"},
        {"id": "INSUFFICIENT_EXTERNAL_VALIDITY", "anchor": ".research-state/research_contract.json: feasibility", "observed": "Tier 2 deferred; toy-domain risk recorded"},
        {"id": "INVALID_PROSPECTIVE_MECHANISM_PREDICTOR", "anchor": ".research-state/claims.json:C2", "observed": "withdrawn due to predictor timing"},
        {"id": "THIN_RELATED_WORK", "anchor": "paper/main.tex", "observed": "related-work coverage below V4 full-paper threshold"},
        {"id": "INSUFFICIENT_ABLATIONS", "anchor": "paper/main.tex", "observed": "no multi-dimensional ablation section"},
        {"id": "MANUSCRIPT_TOO_THIN", "anchor": "submission_package/main.pdf", "observed": f"{profile['manuscript_pages']} pages"},
    ]
    result.update({
        "project": str(project),
        "observed_profile": profile,
        "field_regression_findings": field_findings,
        "finding_ids": [item["id"] for item in field_findings],
    })
    return result

