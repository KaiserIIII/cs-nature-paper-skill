#!/usr/bin/env python3
"""Run dependency-free schema, registry, privacy, and release checks."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_VERSION = "3.2.0"
LEGACY_SKILL_VERSION = "3.1.1"
V32_TEMPLATE_NAMES = {"autonomy_policy.json", "completion_contract.json", "director_session.json"}
ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CI_MATRIX = (
    "ubuntu-latest / Python 3.10",
    "ubuntu-latest / Python 3.11",
    "ubuntu-latest / Python 3.12",
    "windows-latest / Python 3.10",
    "windows-latest / Python 3.11",
    "windows-latest / Python 3.12",
)
EXPECTED_WORKFLOW = "cs-nature-paper-v3.2"
SCHEMA_INSTANCES = {
    "competition_clock": "assets/templates/competition/competition_clock.json",
    "competition_method_router": "assets/registry/competition_method_router.json",
    "competition_profile": "assets/competition/cumcm_profile.json",
    "competition_review": "assets/templates/competition/competition_review.json",
    "competition_risks": "assets/templates/competition/competition_risks.json",
    "competition_rules": "assets/templates/competition/competition_rules.json",
    "competition_state": "assets/templates/competition/competition_state.json",
}


def _read(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))


def schema_instance_path(stem: str, root: Path = ROOT) -> Path:
    if stem == "release_manifest":
        return root / "release_manifest.json"
    if stem in SCHEMA_INSTANCES:
        return root / SCHEMA_INSTANCES[stem]
    return root / "assets" / "templates" / "v3" / f"{stem}.json"


def _type_ok(value: Any, kind: str) -> bool:
    return {"object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str), "integer": isinstance(value, int) and not isinstance(value, bool), "number": isinstance(value, (int, float)) and not isinstance(value, bool), "boolean": isinstance(value, bool), "null": value is None}.get(kind, True)


def validate_instance(value: Any, schema: dict[str, Any], path: str = "$", *, findings: list[str] | None = None) -> list[str]:
    findings = findings if findings is not None else []
    declared = schema.get("type")
    if declared:
        kinds = declared if isinstance(declared, list) else [declared]
        if not any(_type_ok(value, kind) for kind in kinds): findings.append(f"{path}: expected type {kinds}"); return findings
    if "enum" in schema and value not in schema["enum"]: findings.append(f"{path}: value is not in enum")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]: findings.append(f"{path}: string is shorter than minLength")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value): findings.append(f"{path}: pattern mismatch")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value: findings.append(f"{path}.{key}: required")
        props = schema.get("properties", {})
        for key, item in value.items():
            if key in props: validate_instance(item, props[key], f"{path}.{key}", findings=findings)
            elif schema.get("additionalProperties") is False: findings.append(f"{path}.{key}: additional property is not allowed")
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value): validate_instance(item, schema["items"], f"{path}[{index}]", findings=findings)
    return findings


def validate_json_assets() -> list[str]:
    findings: list[str] = []; schema_dir = ROOT / "assets" / "schemas"; template_dir = ROOT / "assets" / "templates" / "v3"
    for schema_path in sorted(schema_dir.glob("*.schema.json")):
        try: schema = _read(schema_path)
        except (OSError, json.JSONDecodeError) as exc: findings.append(f"{schema_path}: {exc}"); continue
        if not isinstance(schema, dict) or schema.get("type") != "object": findings.append(f"{schema_path}: schema must describe an object"); continue
        stem = schema_path.name.removesuffix(".schema.json")
        # These two documents describe array items, not a standalone template.
        if stem in {"evidence_anchor", "review_finding"}:
            continue
        candidate = schema_instance_path(stem, ROOT)
        if candidate.exists():
            try: validate_instance(_read(candidate), schema, str(candidate), findings=findings)
            except (OSError, json.JSONDecodeError) as exc: findings.append(f"{candidate}: {exc}")
    for template_path in sorted(template_dir.glob("*.json")):
        try: value = _read(template_path)
        except (OSError, json.JSONDecodeError) as exc: findings.append(f"{template_path}: {exc}"); continue
        if not isinstance(value, dict): findings.append(f"{template_path}: root must be an object")
        elif value.get("skill_version") != LEGACY_SKILL_VERSION and not (template_path.name in V32_TEMPLATE_NAMES and value.get("skill_version") == SKILL_VERSION):
            findings.append(f"{template_path}: skill_version must be {LEGACY_SKILL_VERSION}")
    return findings


def validate_behavior_cases() -> list[str]:
    findings: list[str] = []; value = _read(ROOT / "assets" / "evals" / "behavior_cases.json")
    if value.get("skill_version") not in {LEGACY_SKILL_VERSION, SKILL_VERSION}: findings.append(f"behavior cases must declare skill_version {SKILL_VERSION} or {LEGACY_SKILL_VERSION}")
    for index, case in enumerate(value.get("cases", [])):
        for field in ("id", "prompt", "required_behaviors", "forbidden_behaviors", "required_artifacts"):
            if not case.get(field): findings.append(f"cases[{index}].{field} is required")
    return findings


def _parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _commit_time(commit: str, root: Path = ROOT) -> datetime | None:
    try:
        value = subprocess.run(["git", "-C", str(root), "show", "-s", "--format=%cI", commit], check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return _parse_utc(value)


def validate_release_manifest_value(
    value: Any,
    *,
    expected_commit: str | None = None,
    expected_branch: str | None = None,
    expected_workflow: str = EXPECTED_WORKFLOW,
    require_hosted_ci: bool = True,
    root: Path = ROOT,
) -> list[str]:
    """Fail closed when release identity and Hosted CI identity are not identical."""
    if not isinstance(value, dict):
        return ["RELEASE_MANIFEST_INVALID: root must be an object"]
    findings: list[str] = []
    required = ("source_version", "source_commit", "source_commit_mode", "source_branch", "generated_at", "deterministic_tests", "hosted_ci", "model_behavior_eval", "e2e_status", "known_limitations", "release_disposition")
    findings.extend(f"RELEASE_MANIFEST_INVALID: missing {field}" for field in required if field not in value)
    if value.get("source_version") != SKILL_VERSION:
        findings.append(f"HOSTED_CI_WRONG_VERSION: expected {SKILL_VERSION}, got {value.get('source_version')}")
    source_commit = str(value.get("source_commit", ""))
    mode = value.get("source_commit_mode")
    generated = _parse_utc(value.get("generated_at"))
    if generated is None:
        findings.append("STALE_RELEASE_MANIFEST: generated_at is missing or invalid")
    if mode == "publisher-injected":
        if source_commit != "release-process-injected":
            findings.append("SOURCE_COMMIT_INCONSISTENT: publisher-injected manifest must use release-process-injected")
        hosted = value.get("hosted_ci")
        if not isinstance(hosted, dict) or any(hosted.get(field) is not None for field in ("run_id", "workflow", "branch", "head_sha", "conclusion")) or hosted.get("matrix") != {}:
            findings.append("STALE_RELEASE_MANIFEST: unresolved repository manifest must not contain Hosted CI success evidence")
        if "V3.2.0 RELEASE BLOCKED" not in str(value.get("release_disposition", "")):
            findings.append("RELEASE_DISPOSITION_INVALID: unresolved manifest must be blocked")
        return findings
    if mode != "resolved" or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        findings.append("SOURCE_COMMIT_INCONSISTENT: resolved manifest must contain a lowercase 40-character SHA")
        return findings
    if expected_commit and source_commit != expected_commit:
        findings.append(f"SOURCE_COMMIT_INCONSISTENT: expected {expected_commit}, got {source_commit}")
    if value.get("e2e_commit") != source_commit:
        findings.append("E2E_COMMIT_STALE: orchestration E2E commit does not match source_commit")
    commit_time = _commit_time(source_commit, root)
    if generated is not None and commit_time is not None and generated < commit_time:
        findings.append("STALE_RELEASE_MANIFEST: generated_at predates source commit")
    tag = value.get("tag")
    if tag not in {None, "v3.2.0"}:
        findings.append("TAG_INCONSISTENT: release tag must be absent or v3.2.0")
    hosted = value.get("hosted_ci")
    if not isinstance(hosted, dict):
        findings.append("HOSTED_CI_NOT_RUN: hosted_ci must be an object")
        return findings
    if hosted.get("head_sha") != source_commit:
        findings.append(f"HOSTED_CI_WRONG_SHA: expected {source_commit}, got {hosted.get('head_sha')}")
    branch = hosted.get("branch")
    allowed_branch = expected_branch or value.get("source_branch")
    if branch != allowed_branch or branch not in {"v3.2", "main", "feat/cumcm-v32-final"}:
        findings.append(f"HOSTED_CI_WRONG_BRANCH: expected {allowed_branch}, got {branch}")
    if hosted.get("workflow") != expected_workflow:
        findings.append(f"HOSTED_CI_WRONG_WORKFLOW: expected {expected_workflow}, got {hosted.get('workflow')}")
    if hosted.get("conclusion") != "success":
        findings.append(f"HOSTED_CI_NOT_SUCCESS: got {hosted.get('conclusion')}")
    if not isinstance(hosted.get("run_id"), int) or hosted.get("run_id", 0) <= 0:
        findings.append("HOSTED_CI_NOT_RUN: run_id is missing")
    matrix = hosted.get("matrix")
    missing = [name for name in REQUIRED_CI_MATRIX if not isinstance(matrix, dict) or matrix.get(name) != "PASS"]
    if missing or (isinstance(matrix, dict) and set(matrix) != set(REQUIRED_CI_MATRIX)):
        findings.append("HOSTED_CI_MATRIX_INCOMPLETE: " + ", ".join(missing or sorted(set(matrix) ^ set(REQUIRED_CI_MATRIX))))
    if require_hosted_ci and findings:
        if str(value.get("release_disposition")) == "V3.2.0 RELEASE READY":
            findings.append("RELEASE_DISPOSITION_INVALID: manifest claims READY despite release-integrity findings")
    elif require_hosted_ci and value.get("release_disposition") != "V3.2.0 RELEASE READY":
        findings.append("RELEASE_DISPOSITION_INVALID: exact-SHA successful manifest must be RELEASE READY")
    return findings


def validate_release_manifest(
    path: Path | None = None,
    *,
    expected_commit: str | None = None,
    expected_branch: str | None = None,
    expected_workflow: str = EXPECTED_WORKFLOW,
    require_hosted_ci: bool = False,
) -> list[str]:
    manifest_path = path or ROOT / "release_manifest.json"
    return validate_release_manifest_value(
        _read(manifest_path),
        expected_commit=expected_commit,
        expected_branch=expected_branch,
        expected_workflow=expected_workflow,
        require_hosted_ci=require_hosted_ci,
    )


def validate_runtime_results(root: Path = ROOT) -> list[str]:
    """Reject generated runtime results if they are present in source."""
    findings: list[str] = []
    for relative in ("benchmarks/smoke-run-result.json",):
        if (root / relative).exists():
            findings.append(f"{relative} is a generated runtime artifact and must not be committed")
    return findings


def validate_v32_e2e(path: Path, root: Path = ROOT) -> list[str]:
    """Validate a CI-only v3.2 harness result without treating it as source."""
    findings: list[str] = []
    try:
        value = _read(path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"v3.2 e2e result is unreadable: {exc}"]
    if value.get("status") != "PASS": findings.append("v3.2 e2e result status is not PASS")
    if value.get("evaluation_class") != "HARNESS_SELF_TEST": findings.append("v3.2 e2e result must be HARNESS_SELF_TEST")
    if value.get("model_behavior") != "NOT_RUN": findings.append("v3.2 e2e model_behavior must be NOT_RUN")
    try:
        commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "UNKNOWN"
    if value.get("skill_commit") != commit: findings.append("v3.2 e2e result has stale skill_commit")
    completion = value.get("completion")
    if not isinstance(completion, dict) or completion.get("status") != "PASS": findings.append("v3.2 e2e completion contract is not PASS")
    director = value.get("director_orchestration")
    if not isinstance(director, dict) or director.get("evaluation_class") != "DIRECTOR_ORCHESTRATION_E2E" or director.get("status") != "PASS":
        findings.append("v3.2 Director orchestration E2E is not PASS")
    return findings


def validate_competition_e2e(path: Path) -> list[str]:
    """Validate the normal-runtime competition orchestration record."""
    try:
        value = _read(path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"competition orchestration e2e is unreadable: {exc}"]
    findings: list[str] = []
    if value.get("status") != "PASS": findings.append("competition orchestration e2e status is not PASS")
    if value.get("evaluation_class") != "COMPETITION_ORCHESTRATION_E2E": findings.append("competition e2e class is invalid")
    if value.get("model_behavior") != "NOT_RUN": findings.append("competition e2e must not claim model behavior")
    if value.get("submission_readiness") != "COMPETITION_SUBMISSION_READY": findings.append("competition e2e did not reach submission ready")
    if value.get("executed_nodes") != 16: findings.append("competition e2e did not execute all 16 graph nodes")
    if value.get("ordinary_author_prompts") != 0: findings.append("competition e2e used ordinary author prompts")
    if value.get("automatic_repair") != "PASS": findings.append("competition automatic repair did not pass")
    if value.get("completion_contract") != "PASS": findings.append("competition completion contract did not pass")
    if value.get("failure_case_count") != 10: findings.append("competition e2e failure-case count is incomplete")
    cases = value.get("failure_cases")
    if not isinstance(cases, dict) or len(cases) != 10 or any(status != "PASS" for status in cases.values()):
        findings.append("competition e2e fail-closed cases are incomplete")
    unresolved = value.get("unresolved")
    if not isinstance(unresolved, dict) or unresolved.get("CRITICAL") != 0 or unresolved.get("MAJOR") != 0:
        findings.append("competition e2e has unresolved CRITICAL or MAJOR findings")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts or any(not str(digest).startswith("sha256:") for digest in artifacts.values()):
        findings.append("competition e2e artifact hashes are incomplete")
    return findings


def validate_docs() -> list[str]:
    findings: list[str] = []
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts: continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for target in re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", text):
            if target.startswith(("http://", "https://", "mailto:")): continue
            if not (path.parent / target).resolve().exists(): findings.append(f"{path}: missing link target {target}")
    return findings


def validate(
    v32_e2e: Path | None = None,
    *,
    competition_e2e: Path | None = None,
    manifest_path: Path | None = None,
    expected_commit: str | None = None,
    expected_branch: str | None = None,
    expected_workflow: str = EXPECTED_WORKFLOW,
    require_hosted_ci: bool = False,
) -> dict[str, Any]:
    findings = validate_json_assets() + validate_behavior_cases() + validate_release_manifest(manifest_path, expected_commit=expected_commit, expected_branch=expected_branch, expected_workflow=expected_workflow, require_hosted_ci=require_hosted_ci) + validate_runtime_results() + validate_docs()
    if v32_e2e is not None:
        findings.extend(validate_v32_e2e(v32_e2e))
    if competition_e2e is not None:
        findings.extend(validate_competition_e2e(competition_e2e))
    try:
        from validate_registry import validate as registry_validate
        registry = registry_validate()
        if registry["status"] != "PASS": findings.extend("registry: " + item for item in registry["findings"])
    except Exception as exc: findings.append(f"registry validation error: {exc}")
    try:
        from privacy_lint import lint
        privacy = lint([ROOT / "benchmarks", ROOT / "release_manifest.json"])
        if privacy["status"] != "PASS": findings.extend("privacy: " + item["kind"] + " in " + item["path"] for item in privacy["findings"])
    except Exception as exc: findings.append(f"privacy validation error: {exc}")
    return {"operation": "validate-release", "status": "PASS" if not findings else "FAIL", "skill_version": SKILL_VERSION, "findings": findings}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v32-e2e", type=Path)
    parser.add_argument("--competition-e2e", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--expected-commit")
    parser.add_argument("--expected-branch")
    parser.add_argument("--expected-workflow", default=EXPECTED_WORKFLOW)
    parser.add_argument("--require-hosted-ci", action="store_true")
    args = parser.parse_args()
    result = validate(args.v32_e2e, competition_e2e=args.competition_e2e, manifest_path=args.manifest, expected_commit=args.expected_commit, expected_branch=args.expected_branch, expected_workflow=args.expected_workflow, require_hosted_ci=args.require_hosted_ci); print(json.dumps(result, indent=2, ensure_ascii=False)); sys.exit(0 if result["status"] == "PASS" else 1)
