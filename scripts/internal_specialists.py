#!/usr/bin/env python3
"""Load and invoke V4's built-in publication-grade specialist pack."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import vendor_skill_runtime  # noqa: E402


SKILL_VERSION = "4.0.0"
PACK_PATH = ROOT / "references" / "internal-specialists" / "team.json"
QUALITY_TIER = "PUBLICATION_GRADE"

SPECIALIZED_TERMS = {
    "publication-quality", "full paper", "journal writing", "closest work",
    "prior art", "novelty", "formal proof", "causal inference", "mixed effect",
    "mixed-effects", "bayesian", "survival", "hierarchical", "multiple testing",
    "distribution shift", "mechanism", "domain review", "statistics review",
}
ORDINARY_TERMS = {
    "ordinary paired bootstrap", "paired bootstrap mean", "basic python",
    "descriptive statistics", "file conversion", "format a file",
}
FORMAL_UPGRADE_CAPABILITIES = {
    "evidence-bound-writing", "evidence-bound-revision", "adversarial-review",
    "novelty-analysis", "prior-art-analysis", "mechanism-analysis",
    "submission-readiness", "publication-editing", "scientific-visualization",
}


class InternalSpecialistError(RuntimeError):
    pass


def load_pack(path: Path = PACK_PATH) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise InternalSpecialistError(f"cannot load internal specialist pack: {path}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("specialists"), list):
        raise InternalSpecialistError("internal specialist pack must contain specialists")
    return value


def validate_pack(path: Path = PACK_PATH) -> dict[str, Any]:
    findings: list[str] = []
    pack = load_pack(path)
    ids: list[str] = []
    for specialist in pack["specialists"]:
        specialist_id = str(specialist.get("id", "<missing>"))
        ids.append(specialist_id)
        for field in ("name", "mission", "capabilities", "vendor_capabilities", "decision_rules", "quality_criteria", "forbidden_actions", "output_contract", "checker", "contract_files"):
            if not specialist.get(field):
                findings.append(f"{specialist_id}: {field} is required")
        for field, minimum in (("decision_rules", 3), ("quality_criteria", 3), ("forbidden_actions", 2)):
            if len(specialist.get(field, [])) < minimum:
                findings.append(f"{specialist_id}: {field} needs at least {minimum} entries")
        for relative in specialist.get("contract_files", []):
            contract = ROOT / "references" / "internal-specialists" / relative
            if not contract.is_file():
                findings.append(f"{specialist_id}: contract missing: {relative}")
                continue
            text = contract.read_text(encoding="utf-8")
            if "Decision rules" not in text or "Output contract" not in text:
                findings.append(f"{specialist_id}: contract lacks operating sections")
        if not any(
            vendor_skill_runtime.load_for_capability(capability).get("status") == "PASS"
            for capability in specialist.get("vendor_capabilities", [])
        ):
            findings.append(f"{specialist_id}: no vendored Skill can supply its primary capability")
    if len(ids) != len(set(ids)):
        findings.append("specialist IDs must be unique")
    if len(ids) != 14:
        findings.append("the publication team must contain exactly fourteen specialists")
    return {
        "operation": "validate-internal-specialist-pack",
        "status": "PASS" if not findings else "FAIL",
        "architecture_version": pack.get("architecture_version"),
        "quality_tier": pack.get("quality_tier"),
        "specialist_ids": ids,
        "findings": findings,
    }


def specialist_for_capability(capability: str) -> dict[str, Any] | None:
    pack = load_pack()
    matches = [item for item in pack["specialists"] if capability in item.get("capabilities", [])]
    return matches[0] if matches else None


def provider_decision(
    capability: str,
    *,
    task: str = "",
    purpose: str = "advisory",
    load_bearing: bool = False,
    criticality: str = "low",
    internal_available: bool = True,
    discovery_status: str | None = None,
    discovery_attempted: bool = False,
    external_comparison: str | None = None,
) -> dict[str, Any]:
    text = task.lower()
    ordinary = any(term in text for term in ORDINARY_TERMS)
    specialized = not ordinary and (
        any(term in text for term in SPECIALIZED_TERMS)
        or capability in {"novelty-analysis", "prior-art-analysis", "submission-readiness"}
        or (purpose == "formal" and load_bearing and capability in FORMAL_UPGRADE_CAPABILITIES)
    )
    base = {
        "operation": "provider-decision",
        "skill_version": SKILL_VERSION,
        "capability": capability,
        "task": task,
        "purpose": purpose,
        "load_bearing": bool(load_bearing),
        "criticality": criticality.upper(),
        "internal_baseline": QUALITY_TIER if internal_available else "UNAVAILABLE",
        "fallback_available": bool(internal_available),
        "external_discovery": "ATTEMPTED" if discovery_attempted else "SKIPPED",
        "discovery_status": discovery_status or "NOT_RUN",
        "truth_authority": "CONTROL_PLANE_CHECKER",
    }
    if not internal_available:
        return base | {
            "decision": "CAPABILITY_VACANCY_DISCOVERY",
            "status": "TRIGGERED",
            "external_discovery": "REQUIRED",
            "selected_provider": None,
        }
    if discovery_attempted:
        if discovery_status == "PASS" and external_comparison in {"EXTERNAL_BETTER", "COMPLEMENTARY"}:
            return base | {
                "decision": external_comparison,
                "status": "SELECTED",
                "selected_provider": "QUALIFIED_EXTERNAL_SKILL",
            }
        return base | {
            "decision": "FALLBACK_BUILT_IN",
            "status": "FALLBACK",
            "external_discovery": "ATTEMPTED",
            "selected_provider": "BUILT_IN_SPECIALIST",
        }
    if specialized:
        return base | {
            "decision": "QUALITY_UPGRADE_DISCOVERY",
            "status": "TRIGGERED",
            "external_discovery": "REQUIRED",
            "selected_provider": "BUILT_IN_SPECIALIST_PENDING_COMPARISON",
        }
    return base | {
        "decision": "INTERNAL_BETTER",
        "status": "SKIPPED",
        "external_discovery": "SKIPPED",
        "selected_provider": "BUILT_IN_SPECIALIST",
    }


def _relative(project: Path, path: Path) -> str:
    return path.resolve().relative_to(project.resolve()).as_posix()


def invoke_specialist(
    specialist_id: str,
    *,
    task: dict[str, Any],
    project: Path,
    network_available: bool = False,
) -> dict[str, Any]:
    project = project.resolve()
    specialist = next((item for item in load_pack()["specialists"] if item["id"] == specialist_id), None)
    if specialist is None:
        return {"status": "FAIL", "findings": [f"unknown internal specialist: {specialist_id}"]}
    loaded = []
    for capability in specialist["vendor_capabilities"]:
        value = vendor_skill_runtime.load_for_capability(capability)
        if value.get("status") == "PASS" and value["name"] not in {item["name"] for item in loaded}:
            loaded.append(value)
    if not loaded:
        return {"status": "FAIL", "findings": [f"no vendored Skill loaded for {specialist_id}"]}
    node = str(task.get("node") or specialist_id).replace("/", "-").replace("\\", "-")
    artifact = project / "artifacts" / "internal-specialists" / f"{specialist_id}-{node}.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    invocation = {
        "schema_version": 1,
        "skill_version": SKILL_VERSION,
        "specialist_id": specialist_id,
        "specialist_name": specialist["name"],
        "mission": specialist["mission"],
        "task": task,
        "decision_rules": specialist["decision_rules"],
        "quality_criteria": specialist["quality_criteria"],
        "forbidden_actions": specialist["forbidden_actions"],
        "expected_outputs": specialist["output_contract"],
        "checker": specialist["checker"],
        "loaded_skills": [
            {
                "name": item["name"],
                "source_kind": item["source_kind"],
                "repository": item["repository"],
                "source_path": item["source_path"],
                "exact_commit": item["exact_commit"],
                "skill_path": item["skill_path"],
                "skill_sha256": item["skill_sha256"],
            }
            for item in loaded
        ],
        "network_available": bool(network_available),
        "network_used": False,
        "runtime_download": False,
        "truth_authority": "CONTROL_PLANE_CHECKER",
    }
    artifact.write_text(json.dumps(invocation, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    relative = _relative(project, artifact)
    return {
        "status": "PASS",
        "provider_id": f"internal-specialist:{specialist_id}",
        "provider_version": SKILL_VERSION,
        "provider_type": "INTERNAL_SPECIALIST",
        "artifacts": [relative],
        "claims": [],
        "uncertainties": ["specialist invocation is not a scientific graph PASS"],
        "actions_taken": ["loaded audited vendored Skill", "materialized typed internal specialist invocation"],
        "tool_calls": [{"operation": "vendor_skill_runtime.load_for_capability", "network": False}],
        "handoff": {"specialist_id": specialist_id, "checker": specialist["checker"], "artifact_sha256": digest},
        "loaded_skills": invocation["loaded_skills"],
        "network_used": False,
        "truth_authority": "CONTROL_PLANE_CHECKER",
    }
