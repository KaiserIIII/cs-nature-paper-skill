#!/usr/bin/env python3
"""Run dependency-light V3.1 schema, registry, graph, and documentation checks."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _required(value: dict[str, Any], fields: list[str], label: str) -> list[str]:
    return [f"{label}.{field} is required" for field in fields if field not in value]


def validate_json_assets() -> list[str]:
    findings: list[str] = []
    schema_dir = ROOT / "assets" / "schemas"
    for schema_path in sorted(schema_dir.glob("*.schema.json")):
        try: schema = _read(schema_path)
        except (OSError, json.JSONDecodeError) as exc: findings.append(f"{schema_path}: {exc}"); continue
        if not isinstance(schema, dict) or schema.get("type") != "object": findings.append(f"{schema_path}: schema must describe an object")
    template_dir = ROOT / "assets" / "templates" / "v3"
    for template_path in sorted(template_dir.glob("*.json")):
        try: value = _read(template_path)
        except (OSError, json.JSONDecodeError) as exc: findings.append(f"{template_path}: {exc}"); continue
        if not isinstance(value, dict): findings.append(f"{template_path}: root must be an object")
        else: findings.extend(_required(value, ["schema_version", "skill_version"], str(template_path)))
    return findings


def validate_schema_documents() -> list[str]:
    """Apply dependency-free top-level required-field checks to known assets."""
    findings: list[str] = []
    candidates: dict[str, Path] = {
        "project": ROOT / "assets" / "templates" / "v3" / "project.json",
        "research_contract": ROOT / "assets" / "templates" / "v3" / "research_contract.json",
        "research_graph": ROOT / "assets" / "templates" / "v3" / "research_graph.json",
        "claims": ROOT / "assets" / "templates" / "v3" / "claims.json",
        "evidence_ledger": ROOT / "assets" / "templates" / "v3" / "evidence_ledger.json",
        "literature_registry": ROOT / "assets" / "templates" / "v3" / "literature_registry.json",
        "experiment_registry": ROOT / "assets" / "templates" / "v3" / "experiment_registry.json",
        "artifact_manifest": ROOT / "assets" / "templates" / "v3" / "artifact_manifest.json",
        "amendments": ROOT / "assets" / "templates" / "v3" / "amendments.json",
        "risks": ROOT / "assets" / "templates" / "v3" / "risks.json",
        "venue_profile": ROOT / "assets" / "templates" / "v3" / "venue_profile.json",
        "employee_registry": ROOT / "assets" / "templates" / "v3" / "employee_registry.json",
        "delegation_plan": ROOT / "assets" / "templates" / "v3" / "delegation_plan.json",
        "handoff": ROOT / "assets" / "templates" / "v3" / "handoff.json",
        "query_log": ROOT / "assets" / "templates" / "v3" / "query_log.json",
        "release_manifest": ROOT / "release_manifest.json",
    }
    schema_dir = ROOT / "assets" / "schemas"
    for schema_path in sorted(schema_dir.glob("*.schema.json")):
        schema = _read(schema_path)
        required = schema.get("required")
        if not isinstance(required, list) or not required:
            findings.append(f"{schema_path}: required must be a non-empty list")
            continue
        stem = schema_path.name.removesuffix(".schema.json")
        candidate = candidates.get(stem)
        if candidate is None or not candidate.exists():
            continue
        value = _read(candidate)
        findings.extend(f"{candidate}: missing schema field {field}" for field in required if field not in value)
    return findings


def validate_profiles() -> list[str]:
    findings: list[str] = []
    required_domain = ("domain", "common_contributions", "common_study_types", "high-risk_claims", "typical_evidence", "baseline_families", "common_failure_modes", "specialist_triggers", "method_modules", "reviewer_threats", "artifact_expectations")
    required_study = ("study_type", "required_decisions", "mandatory_expertise", "required_evidence", "escalation_triggers", "forbidden_claims")
    for path, required, minimum in ((ROOT / "assets/registry/domain_profiles.json", required_domain, 13), (ROOT / "assets/registry/study_profiles.json", required_study, 15)):
        value = _read(path); profiles = value.get("profiles", [])
        if len(profiles) < minimum: findings.append(f"{path}: expected at least {minimum} profiles")
        for index, profile in enumerate(profiles): findings.extend(_required(profile, list(required), f"{path}[{index}]"))
    return findings


def validate_behavior_cases() -> list[str]:
    value = _read(ROOT / "assets/evals/behavior_cases.json"); findings: list[str] = []
    if value.get("skill_version") != "3.1.0": findings.append("behavior cases must declare skill_version 3.1.0")
    categories = {"routing","student UX","literature","novelty","method selection","feasibility","experiment design","implementation","statistics","figures","writing","validation","review","security","privacy","authorization","supply-chain","graph recovery","migration","completion honesty"}
    declared = set(value.get("categories", [])); missing = sorted(categories - declared)
    if missing: findings.append(f"behavior categories missing: {missing}")
    for index, case in enumerate(value.get("cases", [])):
        findings.extend(_required(case, ["id", "prompt", "required_behaviors", "forbidden_behaviors", "required_artifacts", "category"], f"cases[{index}]"))
    return findings


def validate_release_manifest() -> list[str]:
    path = ROOT / "release_manifest.json"
    if not path.exists():
        return ["release_manifest.json is required"]
    value = _read(path)
    findings = _required(value, ["version", "commit", "schemas", "scripts", "tests", "behavior_evals", "known_limitations", "external_skill_audit_date", "ci_status"], "release_manifest")
    if value.get("version") != "3.1.0":
        findings.append("release_manifest.version must be 3.1.0")
    for field in ("schemas", "scripts", "tests", "known_limitations"):
        if field in value and not isinstance(value[field], list):
            findings.append(f"release_manifest.{field} must be a list")
    if "behavior_evals" in value and not isinstance(value["behavior_evals"], dict):
        findings.append("release_manifest.behavior_evals must be an object")
    return findings


def validate_docs() -> list[str]:
    findings: list[str] = []
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts: continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for target in re.findall(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]+)?\)", text):
            if target.startswith(("http://", "https://", "mailto:")): continue
            candidate = (path.parent / target).resolve()
            if not candidate.exists(): findings.append(f"{path}: missing link target {target}")
    return findings


def validate() -> dict[str, Any]:
    findings = validate_json_assets() + validate_schema_documents() + validate_profiles() + validate_behavior_cases() + validate_release_manifest() + validate_docs()
    return {"operation":"validate-release","status":"PASS" if not findings else "FAIL","findings":findings}


if __name__ == "__main__":
    result = validate(); print(json.dumps(result, indent=2, ensure_ascii=False)); sys.exit(0 if result["status"] == "PASS" else 1)
