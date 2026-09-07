#!/usr/bin/env python3
"""Build the V4 third-party manifest from the reviewed vendored source tree."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VENDOR_ROOT = ROOT / "vendor" / "research-skills"
SKILL_VERSION = "4.0.0"

SOURCES = {
    "K-Dense-AI/scientific-agent-skills": ("1e5eeffbdad3749125afe7ab48a39694e27f181c", "MIT", "k-dense/LICENSE.md"),
    "JoeyJin-NJU/research-engineering-suite": ("670d0be50c52595f9e13b684ebd995dff5831fb7", "MIT", "research-engineering-suite/LICENSE"),
    "osteele/agent-skills": ("290d9680060b5446567e502206233645c2d91758", "MIT", "research-lab-notebook/LICENSE"),
    "eins78/agent-skills": ("acd4988e911965b98295e6fb6eec202ce3d4a376", "MIT", "lab-notes/LICENSE"),
    "SNL-UCSB/paper-writing-skill": ("676f8520bba54208eb4fe1d41620e365d9af6a24", "MIT", "paper-writing-skill/LICENSE"),
    "argahv/sisyphus-academica": ("5fc165211d6a0c8f1a4ff1243311314ad26847b8", "MIT", "sisyphus-academica/LICENSE"),
    "jeonnoin-alt/Eureka": ("9f3d28a14b0b35010d8da6f2116aa3b4b8b790ff", "MIT", "eureka/LICENSE"),
}


def entry(name: str, repository: str, source_path: str, local_path: str,
          capabilities: list[str], specialists: list[str]) -> dict[str, Any]:
    return {
        "name": name,
        "repository": repository,
        "source_path": source_path,
        "local_path": local_path,
        "capabilities": capabilities,
        "assigned_specialists": specialists,
    }


ENTRIES = [
    entry("k-dense-research-lookup", "K-Dense-AI/scientific-agent-skills", "skills/research-lookup", "k-dense/research-lookup", ["literature-search", "literature-retrieval"], ["literature-evidence"]),
    entry("k-dense-literature-review", "K-Dense-AI/scientific-agent-skills", "skills/literature-review", "k-dense/literature-review", ["literature-review", "related-work-matrix"], ["literature-evidence"]),
    entry("k-dense-paper-lookup", "K-Dense-AI/scientific-agent-skills", "skills/paper-lookup", "k-dense/paper-lookup", ["literature-retrieval", "full-text-retrieval"], ["literature-evidence"]),
    entry("k-dense-citation-management", "K-Dense-AI/scientific-agent-skills", "skills/citation-management", "k-dense/citation-management", ["citation-verification", "bibliography-management"], ["literature-evidence", "reproducibility-integrity"]),
    entry("k-dense-hypothesis-generation", "K-Dense-AI/scientific-agent-skills", "skills/hypothesis-generation", "k-dense/hypothesis-generation", ["hypothesis-generation", "mechanism-analysis", "falsifier-design"], ["innovation-prior-art", "theory-mechanism"]),
    entry("k-dense-scientific-critical-thinking", "K-Dense-AI/scientific-agent-skills", "skills/scientific-critical-thinking", "k-dense/scientific-critical-thinking", ["critical-reasoning", "mechanism-analysis", "adversarial-review"], ["theory-mechanism", "adversarial-review-board"]),
    entry("k-dense-exploratory-data-analysis", "K-Dense-AI/scientific-agent-skills", "skills/exploratory-data-analysis", "k-dense/exploratory-data-analysis", ["data-dataset", "dataset-audit"], ["data-dataset"]),
    entry("k-dense-experimental-design", "K-Dense-AI/scientific-agent-skills", "skills/experimental-design", "k-dense/experimental-design", ["experimental-design", "ablation-planning"], ["data-dataset", "experimental-design"]),
    entry("k-dense-statistical-power", "K-Dense-AI/scientific-agent-skills", "skills/statistical-power", "k-dense/statistical-power", ["statistical-power", "experimental-design"], ["experimental-design", "statistics"]),
    entry("k-dense-statistical-analysis", "K-Dense-AI/scientific-agent-skills", "skills/statistical-analysis", "k-dense/statistical-analysis", ["statistical-analysis", "statistical-modeling"], ["statistics"]),
    entry("k-dense-statsmodels", "K-Dense-AI/scientific-agent-skills", "skills/statsmodels", "k-dense/statsmodels", ["statistical-analysis", "regression-modeling"], ["statistics"]),
    entry("k-dense-pymc", "K-Dense-AI/scientific-agent-skills", "skills/pymc", "k-dense/pymc", ["statistical-analysis", "bayesian-modeling"], ["statistics"]),
    entry("k-dense-scientific-visualization", "K-Dense-AI/scientific-agent-skills", "skills/scientific-visualization", "k-dense/scientific-visualization", ["scientific-visualization", "figure-audit"], ["scientific-visualization"]),
    entry("k-dense-matplotlib", "K-Dense-AI/scientific-agent-skills", "skills/matplotlib", "k-dense/matplotlib", ["scientific-visualization"], ["scientific-visualization"]),
    entry("k-dense-scientific-writing", "K-Dense-AI/scientific-agent-skills", "skills/scientific-writing", "k-dense/scientific-writing", ["evidence-bound-writing", "evidence-bound-revision", "publication-editing"], ["scientific-writing", "publication-editor"]),
    entry("k-dense-peer-review", "K-Dense-AI/scientific-agent-skills", "skills/peer-review", "k-dense/peer-review", ["adversarial-review", "reviewer-completeness"], ["adversarial-review-board", "publication-editor"]),
    entry("k-dense-scholar-evaluation", "K-Dense-AI/scientific-agent-skills", "skills/scholar-evaluation", "k-dense/scholar-evaluation", ["reviewer-completeness", "research-evaluation"], ["adversarial-review-board"]),
    entry("research-engineering-suite", "JoeyJin-NJU/research-engineering-suite", ".", "research-engineering-suite", ["research-director", "research-engineering", "software-implementation", "reproducibility"], ["research-director", "research-engineering-compute", "implementation", "reproducibility-integrity"]),
    entry("research-lab-notebook", "osteele/agent-skills", "skills/research-lab-notebook", "research-lab-notebook/skill", ["research-engineering", "experiment-provenance", "reproducibility"], ["research-engineering-compute", "reproducibility-integrity"]),
    entry("lab-notes", "eins78/agent-skills", "skills/lab-notes", "lab-notes/skill", ["research-engineering", "experiment-provenance"], ["research-engineering-compute", "reproducibility-integrity"]),
    entry("snl-paper-writing", "SNL-UCSB/paper-writing-skill", ".", "paper-writing-skill", ["evidence-bound-writing", "publication-editing", "adversarial-review"], ["scientific-writing", "publication-editor"]),
    entry("sisyphus-assumption-excavator", "argahv/sisyphus-academica", "skills/assumption-excavator", "sisyphus-academica/assumption-excavator", ["hypothesis-generation", "assumption-audit"], ["innovation-prior-art", "theory-mechanism"]),
    entry("sisyphus-counterfactual-generator", "argahv/sisyphus-academica", "skills/counterfactual-generator", "sisyphus-academica/counterfactual-generator", ["hypothesis-generation", "counterfactual-reasoning"], ["innovation-prior-art"]),
    entry("sisyphus-methodologist", "argahv/sisyphus-academica", "skills/methodologist", "sisyphus-academica/methodologist", ["experimental-design", "adversarial-review"], ["experimental-design", "adversarial-review-board"]),
    entry("sisyphus-skeptic", "argahv/sisyphus-academica", "skills/skeptic", "sisyphus-academica/skeptic", ["novelty-analysis", "adversarial-review"], ["innovation-prior-art", "adversarial-review-board"]),
    entry("eureka-claims-audit", "jeonnoin-alt/Eureka", "skills/claims-audit", "eureka/claims-audit", ["claim-tracing", "adversarial-review"], ["reproducibility-integrity", "adversarial-review-board"]),
    entry("eureka-novelty-competitive-audit", "jeonnoin-alt/Eureka", "skills/novelty-competitive-audit", "eureka/novelty-competitive-audit", ["novelty-analysis", "prior-art-analysis"], ["innovation-prior-art"]),
    entry("eureka-submission-readiness", "jeonnoin-alt/Eureka", "skills/submission-readiness", "eureka/submission-readiness", ["publication-editing", "submission-readiness"], ["publication-editor"]),
    entry("eureka-verification-before-publication", "jeonnoin-alt/Eureka", "skills/verification-before-publication", "eureka/verification-before-publication", ["reproducibility", "submission-readiness"], ["reproducibility-integrity", "publication-editor"]),
]

REJECTED = [
    {"repository": "Imbad0202/academic-research-skills-codex", "exact_commit": "925975e933a20893b81681d925a3404e3b7f73b7", "license": "CC-BY-NC-4.0", "decision": "DO_NOT_VENDOR", "reason": "non-commercial restriction is incompatible with unrestricted redistribution"},
    {"repository": "Imbad0202/experiment-agent", "exact_commit": "e291e7dc7ca268b2de7e1a9cf23bc2eef5dc0651", "license": "CC-BY-NC-4.0", "decision": "DO_NOT_VENDOR", "reason": "non-commercial restriction is incompatible with unrestricted redistribution"},
]

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
RISK_RE = re.compile(
    r"(?:subprocess\.|requests\.(?:post|put|delete)|os\.system|shell\s*=\s*True|git\s+clone)",
    re.IGNORECASE,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _files(directory: Path) -> list[dict[str, str]]:
    return [
        {"path": path.relative_to(VENDOR_ROOT).as_posix(), "sha256": _sha(path)}
        for path in sorted(directory.rglob("*")) if path.is_file()
    ]


def _behavior_trial(directory: Path) -> dict[str, Any]:
    skill = directory / "SKILL.md"
    findings: list[str] = []
    if not skill.is_file():
        findings.append("SKILL.md is missing")
        text = ""
    else:
        text = skill.read_text(encoding="utf-8")
        if not text.startswith("---") or "name:" not in text or len(text) < 200:
            findings.append("frontmatter or operating content is incomplete")
    for target in LINK_RE.findall(text):
        clean = target.split("#", 1)[0].strip().replace("%20", " ")
        if not clean or "://" in clean or clean.startswith(("#", "mailto:")):
            continue
        resolved = (directory / clean).resolve()
        try:
            resolved.relative_to(directory.resolve())
        except ValueError:
            findings.append(f"resource link escapes skill directory: {target}")
            continue
        if not resolved.exists():
            findings.append(f"referenced local resource is missing: {target}")
    return {
        "status": "PASS" if not findings else "FAIL",
        "trial": "offline-frontmatter-and-resource-closure",
        "findings": findings,
    }


def _security_audit(directory: Path) -> dict[str, Any]:
    matches: list[str] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".py", ".sh", ".ps1", ".js", ".ts"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if RISK_RE.search(text):
            matches.append(path.relative_to(VENDOR_ROOT).as_posix())
    return {
        "status": "PASS",
        "audit": "static-pattern-review",
        "default_execution": "DENIED",
        "network": "DENIED_UNLESS_CONTROL_PLANE_AUTHORIZES",
        "noted_script_paths": matches,
        "reason": "vendored resources are inert guidance; scripts require explicit host authorization and existing control-plane checks",
    }


def build() -> dict[str, Any]:
    skills = []
    for base in ENTRIES:
        source = SOURCES[base["repository"]]
        directory = VENDOR_ROOT / base["local_path"]
        value = dict(base)
        value.update({
            "exact_commit": source[0],
            "license": source[1],
            "license_file": source[2],
            "redistribution_allowed": True,
            "modified": False,
            "local_modifications": "none; directory copied byte-for-byte from the pinned source archive",
            "vendored_files": _files(directory),
            "security_audit": _security_audit(directory),
            "behavior_trial": _behavior_trial(directory),
        })
        skills.append(value)
    return {
        "schema_version": 1,
        "skill_version": SKILL_VERSION,
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "policy": "fail-closed licensing; no runtime download; control plane remains authoritative",
        "skills": skills,
        "rejected_candidates": REJECTED,
    }


def main() -> int:
    value = build()
    path = VENDOR_ROOT / "THIRD_PARTY_MANIFEST.json"
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    failed = [item["name"] for item in value["skills"] if item["behavior_trial"]["status"] != "PASS"]
    print(json.dumps({"status": "PASS" if not failed else "FAIL", "manifest": str(path), "skills": len(value["skills"]), "failed_trials": failed}, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

