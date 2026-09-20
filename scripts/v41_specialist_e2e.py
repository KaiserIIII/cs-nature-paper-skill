#!/usr/bin/env python3
"""Execute all six selected V4.1 specialist adapters on local fixtures."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "assets" / "evals" / "v41" / "specialist_integration_cases.json"


def _runtime():
    path = ROOT / "scripts" / "v41_provider_adapters.py"
    spec = importlib.util.spec_from_file_location("v41_provider_adapters_e2e", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("V4.1 provider adapter runtime is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixtures(root: Path) -> dict[str, dict[str, Any]]:
    paper = root / "paper"
    paper.mkdir()
    (paper / "confirmed_contribution.md").write_text(
        """# Confirmed contribution

## Core Contribution
| Field | Decision |
|---|---|
| Main contribution statement | A source-bound adapter proves that selected specialist code really executed. |
| Contribution type | new method |
| Reviewer payoff | Reviewers receive typed receipts rather than registry-only assertions. |

## Why This Contribution Is Needed
| Field | Decision |
|---|---|
| Field problem | Candidate listings can be mistaken for installed and callable capabilities. |
| Specific gap | No prior adapter executed the pinned specialist resources. |
| Concrete challenge | Local execution must preserve licensing, provenance, and fail-closed qualification. |
| Why prior work leaves it unresolved | The prior release contained only provider metadata and fallback routing. |

## How This Paper Responds
| Field | Decision |
|---|---|
| Design response | Execute pinned upstream checks behind deterministic local adapters. |
| Evidence required | Each invocation records its input, output, source bundle, and executed files. |
| Evidence available | This suite runs all six providers on local deterministic fixtures. |
| Evidence missing | Independent formal behavior qualification has not been supplied. |

## Claim Boundary
| Field | Decision |
|---|---|
| Strong claims allowed | The bounded advisory implementation executes offline. |
| Claims to soften or avoid | It is not formally qualified or scientifically superior. |
| Novelty risk | Novelty needs a separate current-literature assessment. |
| Significance risk | Synthetic callability does not establish research significance. |
""",
        encoding="utf-8",
    )
    results = root / "results_validation.md"
    results.write_text(
        """# Results validation

| Results Unit | Contribution Claim Tested | Result/Evidence | Allowed Interpretation | Interpretation NOT Allowed |
|---|---|---|---|---|
| Six adapter run | C1: real local execution | All provider receipts name executed source resources | The integrations are callable | Formal scientific qualification |
""",
        encoding="utf-8",
    )
    exemplars = root / "target_exemplars.json"
    exemplars.write_text(
        json.dumps(
            {
                "target_venue": "Nature Machine Intelligence",
                "exemplars": [
                    {
                        "source_id": "doi:10.0000/pinned-example",
                        "title": "Pinned target exemplar",
                        "verified": True,
                        "transferable_patterns": ["problem framing", "evidence architecture"],
                        "non_transferable_content": ["claims", "data", "wording"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    figure = root / "figure.py"
    figure.write_text(
        """import matplotlib as mpl
import matplotlib.pyplot as plt
mpl.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica"], "font.size": 7, "svg.fonttype": "none", "pdf.fonttype": 42})
width_mm = 183
values = values[values > 0]
fig, ax = plt.subplots(figsize=(width_mm / 25.4, 120 / 25.4))
ax.set_yscale("log")
fig.savefig("figure.svg", bbox_inches="tight")
fig.savefig("figure.pdf", bbox_inches="tight")
fig.savefig("figure.tiff", dpi=600, bbox_inches="tight")
""",
        encoding="utf-8",
    )
    manuscript = root / "manuscript.md"
    manuscript.write_text(
        """# Evidence-bound specialist runtime

## Abstract
We report a bounded contribution: pinned advisory specialist resources can execute offline.

## Methods
The suite records deterministic source, input, output, and executed-resource hashes.

## Results
Six local adapters return typed advisory artifacts without claiming scientific truth.

## Limitations
Synthetic fixtures establish callability, not novelty, validity, or publication readiness.

## Data and code availability
All fixtures and adapter source are in the release tree.
""",
        encoding="utf-8",
    )
    receipt = root / "manuscript_validation.json"
    receipt.write_text('{"status":"PASS","fixture":true}\n', encoding="utf-8")
    areas = (
        "title", "abstract", "body", "figures", "tables", "references",
        "attachments", "required_sections", "required_materials",
    )
    preference = {
        "preferred_moves": ["evidence before interpretation"],
        "evidence_expectations": ["source-bound receipt"],
        "avoid": ["unsupported claims"],
        "source_ids": ["official-guide"],
    }
    profile = root / "publication_target_profile.json"
    profile.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "target": {"name": "Fixture Journal", "article_type": "Article", "researched_at": "2026-09-20"},
                "sources": [{"id": "official-guide", "authority": "official", "url": "https://example.org/guide", "checked_at": "2026-09-20"}],
                "format": {"manuscript_formats": ["Markdown"], "source_ids": ["official-guide"]},
                "five_part_preferences": {
                    key: preference for key in (
                        "front_matter", "introduction", "methods_or_approach",
                        "results_or_analysis", "discussion_and_conclusion",
                    )
                },
                "package_requirements": [
                    {
                        "id": "main-manuscript", "role": "main_manuscript",
                        "disposition": "required", "condition_status": "applies",
                        "accepted_extensions": [".md"], "reuse_policy": "revalidate",
                        "source_ids": ["official-guide"],
                    }
                ],
                "compliance": {
                    "coverage": [
                        {
                            "area": area,
                            "status": "known" if area == "required_materials" else "not_applicable",
                            "source_ids": ["official-guide"], "source_locator": f"fixture:{area}",
                            "note": "No additional bounded fixture rule." if area != "required_materials" else "",
                        }
                        for area in areas
                    ],
                    "rules": [
                        {
                            "id": "required-main", "area": "required_materials",
                            "verification": "machine_verifiable", "metric": "required_material",
                            "operator": "required", "unit": "files", "limit": ["main-manuscript"],
                            "source_ids": ["official-guide"], "source_locator": "fixture:required-materials",
                            "remediation": "Attach the validated manuscript.",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    plan = root / "submission_package_plan.json"
    plan.write_text(
        json.dumps(
            {
                "schema_version": "1.0", "project_root": ".", "target_name": "Fixture Journal",
                "target_profile_sha256": hashlib.sha256(profile.read_bytes()).hexdigest(),
                "compliance_inputs": {"manuscript_path": manuscript.name},
                "author_confirmations": [
                    {"id": item, "status": "confirmed"}
                    for item in (
                        "target_selected", "author_identity_and_order",
                        "declarations_approved", "exclusive_submission",
                    )
                ],
                "items": [
                    {
                        "requirement_id": "main-manuscript", "status": "ready",
                        "source_path": manuscript.name, "output_name": "manuscript.md",
                        "validation_receipts": [
                            {"path": receipt.name, "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest()}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    invocation = root / "publication_cycle_request.json"
    invocation.write_text(
        json.dumps(
            {
                "contract": "paperspine.publication-cycle.invoke-request",
                "interface_version": "1.0", "operation": "assemble", "project_root": ".",
                "inputs": {"profile": profile.name, "plan": plan.name},
                "outputs": {"directory": "publication_bundle"},
                "options": {"write_report": False},
            }
        ),
        encoding="utf-8",
    )
    return {
        "paperspine:contribution": {"output_dir": str(paper)},
        "paperspine:results-validation": {"artifact_path": str(results)},
        "paperspine:target-exemplar": {"artifact_path": str(exemplars)},
        "paperspine:publication-production": {"request_path": str(invocation)},
        "nature:figure": {"source_path": str(figure), "backend": "python"},
        "nature:reviewer": {"manuscript_path": str(manuscript)},
    }


def _lookup(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def run(mode: str = "PUBLIC_CORE") -> dict[str, Any]:
    runtime = _runtime()
    suite = json.loads(CASES.read_text(encoding="utf-8"))
    providers: dict[str, dict[str, Any]] = {}
    checks: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="v41-specialist-e2e-") as temporary:
        requests = _fixtures(Path(temporary))
        for case in suite["cases"]:
            provider_id = case["provider_id"]
            result = runtime.invoke_provider(
                provider_id, requests[provider_id], mode=mode, formal=False
            )
            providers[provider_id] = result
            assertion = case["assertion"]
            observed = _lookup(result, assertion["path"])
            checks.append(
                {
                    "case_id": case["id"],
                    "provider_id": provider_id,
                    "path": assertion["path"],
                    "expected": assertion["equals"],
                    "observed": observed,
                    "status": "PASS" if observed == assertion["equals"] else "FAIL",
                }
            )
    passed = (
        len(providers) == 6
        and all(item.get("status") == "PASS" for item in providers.values())
        and all(item["status"] == "PASS" for item in checks)
        and all(item.get("evidence", {}).get("executed_resources") for item in providers.values())
    )
    return {
        "operation": "v41-selected-specialist-e2e",
        "status": "PASS" if passed else "FAIL",
        "mode": mode,
        "suite_id": suite["suite_id"],
        "executed_count": len(providers),
        "providers": providers,
        "checks": checks,
        "formal_qualification_claimed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("PUBLIC_CORE", "PRIVATE_ULTRA"), default="PUBLIC_CORE")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = run(args.mode)
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(payload, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
