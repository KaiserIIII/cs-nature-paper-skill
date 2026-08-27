#!/usr/bin/env python3
"""Run dependency-free schema, registry, privacy, and release checks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SKILL_VERSION = "3.2.0"
LEGACY_SKILL_VERSION = "3.1.1"
V32_TEMPLATE_NAMES = {"autonomy_policy.json", "completion_contract.json", "director_session.json"}
ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))


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
        candidate = ROOT / "release_manifest.json" if stem == "release_manifest" else template_dir / f"{stem}.json"
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


def validate_release_manifest() -> list[str]:
    value = _read(ROOT / "release_manifest.json"); findings: list[str] = []
    fields = ("source_version", "source_commit", "source_commit_mode", "generated_at", "deterministic_tests", "hosted_ci", "model_behavior_eval", "e2e_status", "known_limitations")
    findings.extend(f"release_manifest.{field} is required" for field in fields if field not in value)
    if value.get("source_version") not in {LEGACY_SKILL_VERSION, SKILL_VERSION}: findings.append(f"release_manifest.source_version must be {SKILL_VERSION} or {LEGACY_SKILL_VERSION}")
    source_commit = str(value.get("source_commit", ""))
    if not source_commit or "pending" in source_commit.lower() or "local_equivalent" in source_commit.lower(): findings.append("release_manifest.source_commit must be explicit or release-process-injected")
    if value.get("hosted_ci") not in {"PASS", "PENDING", "NOT_RUN", "FAIL"}: findings.append("release_manifest.hosted_ci has invalid status")
    if value.get("e2e_status") not in {"PASS", "CONDITIONAL", "NOT_RUN", "FAIL"}: findings.append("release_manifest.e2e_status has invalid status")
    if value.get("source_commit_mode") not in {"publisher-injected", "resolved"}: findings.append("release_manifest.source_commit_mode has invalid status")
    if value.get("source_commit_mode") == "publisher-injected" and source_commit != "release-process-injected": findings.append("publisher-injected manifest must use release-process-injected source_commit")
    if value.get("source_commit_mode") == "resolved" and not re.fullmatch(r"[0-9a-f]{40}", source_commit): findings.append("resolved release manifest must contain a commit SHA")
    return findings


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


def validate(v32_e2e: Path | None = None) -> dict[str, Any]:
    findings = validate_json_assets() + validate_behavior_cases() + validate_release_manifest() + validate_runtime_results() + validate_docs()
    if v32_e2e is not None:
        findings.extend(validate_v32_e2e(v32_e2e))
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
    args = parser.parse_args()
    result = validate(args.v32_e2e); print(json.dumps(result, indent=2, ensure_ascii=False)); sys.exit(0 if result["status"] == "PASS" else 1)
