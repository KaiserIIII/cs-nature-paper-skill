#!/usr/bin/env python3
"""Select relevant reviewer attacks and validate evidence-bound findings."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ATTACKS = {"novelty": "Novelty attack", "prior_art": "Prior-art attack", "construct": "Construct attack", "mechanism": "Mechanism attack", "causal": "Causal attack", "baseline": "Baseline attack", "leakage": "Leakage attack", "statistics": "Statistics attack", "generalization": "Generalization attack", "reproducibility": "Reproducibility attack", "artifact": "Artifact attack", "cost": "Cost/deployment attack", "editor": "Editor 90-second reject attack"}
ROLE_RULES = {"editor": {"editor", "writing", "venue"}, "domain expert": {"domain", "novelty"}, "closest competitor": {"novelty", "prior_art"}, "methodologist": {"method", "statistics", "causal", "construct"}, "statistician": {"statistics", "stochastic", "sampling"}, "artifact reviewer": {"artifact", "reproducibility", "code"}, "security reviewer": {"security", "leakage"}, "practitioner": {"cost", "deployment", "systems"}, "ethics": {"ethics", "human", "privacy"}, "human-study reviewer": {"human", "survey", "ethics"}, "theorist": {"theory", "formal", "proof"}, "adversarial alternative": {"alternative", "mechanism", "causal"}, "newcomer": {"clarity", "student", "editor"}}


def select(threats: list[str], claims: list[str] | None = None) -> dict[str, Any]:
    text = " ".join(threats + (claims or [])).lower()
    attacks = [label for key, label in ATTACKS.items() if key.replace("_", " ") in text or key in text]
    if not attacks:
        attacks = [ATTACKS["editor"], ATTACKS["reproducibility"]]
    roles = [role for role, keywords in ROLE_RULES.items() if any(keyword in text for keyword in keywords)]
    if not roles:
        roles = ["editor", "adversarial alternative", "newcomer"]
    return {"operation": "select", "status": "PASS", "attacks": attacks, "roles": roles, "reason": "roles are activated by named threats; no fixed reviewer count or acceptance vote is used"}


def validate_finding(value: Any) -> dict[str, Any]:
    required = ("id", "role", "severity", "anchor", "affected_claim", "problem", "evidence", "uncertainty", "smallest_sufficient_fix", "new_data_required", "verification", "residual_risk")
    findings = [] if isinstance(value, dict) else ["finding must be an object"]
    if isinstance(value, dict):
        findings.extend(f"{field} is required" for field in required if field not in value)
        if value.get("severity") not in {"CRITICAL", "MAJOR", "MINOR", "INFO"}: findings.append("severity is invalid")
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def audit(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8")); items = value.get("findings", value if isinstance(value, list) else [])
    findings: list[str] = []
    if isinstance(items, list):
        for index, item in enumerate(items): findings.extend(f"findings[{index}]: {message}" for message in validate_finding(item)["findings"])
    serialized = json.dumps(value, ensure_ascii=False).lower()
    for phrase in ("acceptance probability", "% nature", "reviewers accept"):
        if phrase in serialized: findings.append(f"acceptance theater phrase is forbidden: {phrase}")
    return {"operation": "audit", "status": "PASS" if not findings else "FAIL", "finding_count": len(items) if isinstance(items, list) else 0, "findings": findings}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("select"); p.add_argument("--threat", action="append", default=[]); p.add_argument("--claim", action="append", default=[])
    p = sub.add_parser("audit"); p.add_argument("path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv); result = select(args.threat, args.claim) if args.command == "select" else audit(args.path); print(json.dumps(result, indent=2, ensure_ascii=False)); return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__": sys.exit(main())
