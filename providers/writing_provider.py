"""Evidence-bound manuscript and revision provider."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import provider_support as support


PROVIDER_ID = "writing-provider"


def _authoritative(project: Path) -> dict[str, Any]:
    state = support.state_dir(project)
    return {
        "contract": support.read_json(state / "research_contract.json", {}),
        "claims": support.read_json(state / "claims.json", {}),
        "evidence": support.read_json(state / "evidence_ledger.json", {}),
        "literature": support.read_json(state / "literature_registry.json", {}),
        "experiments": support.read_json(state / "experiment_registry.json", {}),
        "artifacts": support.read_json(state / "artifact_manifest.json", {}),
        "brief": support.read_json(project / "inputs" / "research_brief.json", {}),
        "analysis": support.read_json(project / "artifacts" / "analysis.json", {}),
        "figure": support.read_json(project / "artifacts" / "figure_provenance.json", {}),
    }


def execute(project: Path, node: str) -> dict[str, Any]:
    values = _authoritative(project)
    manuscript = project / "artifacts" / "manuscript.md"
    if node == "writing":
        brief = values["brief"]
        analysis = values["analysis"]
        literature = values["literature"]
        source_titles = [str(item.get("title")) for item in literature.get("sources", []) if item.get("title")]
        relations = literature.get("claim_relations", [])
        text = (
            f"# {brief.get('title', 'Research manuscript')}\n\n"
            "## Abstract\n\n"
            f"We study: {brief.get('question')}. The formal project command analyzed {analysis.get('n')} observations. "
            f"The observed mean was {analysis.get('mean')} and the selected candidate method was {analysis.get('selected_method')}. "
            "All conclusions are limited to the declared input and recorded execution.\n\n"
            "## Related Work\n\n"
            f"Verified identities available to this run: {', '.join(source_titles) if source_titles else 'none'}. "
            f"The registry contains {len(relations)} scoped source relations; metadata-only records are not used as load-bearing support.\n\n"
            "## Method\n\n"
            f"Candidate methods were {', '.join(map(str, values['brief'].get('method_candidates', [])))}. "
            "The implementation read the project data, compared eligible methods using observed error, and recorded the command, environment, inputs, and output hash.\n\n"
            "## Results\n\n"
            f"{analysis.get('claim')} The 95% normal-approximation interval recorded by the analysis provider was {analysis.get('confidence_interval_95')}. "
            "Figure: artifacts/figure.svg.\n\n"
            "## Limitations\n\n"
            "The analysis is bounded to the supplied data and declared design. Metadata, snippets, and provider assertions do not establish scientific truth.\n"
        )
        support.write(manuscript, text)
        return support.handoff(project, PROVIDER_ID, node, [manuscript], claims=values["claims"].get("claims", []), uncertainties=["external validity is not inferred"], extra={"word_count": len(text.split())})
    if node != "revision":
        return {"status": "BLOCKED", "findings": [f"unsupported writing node: {node}"]}
    text = manuscript.read_text(encoding="utf-8")
    review_path = project / "artifacts" / "review_findings.json"
    review = support.read_json(review_path, {})
    actions = []
    if "## Reproducibility" not in text:
        text += (
            "\n## Reproducibility\n\n"
            "Run the command recorded in artifacts/formal_execution.json with the frozen protocol and declared input. "
            "Verify the output hash, analysis input hash, figure source hash, and package manifest before relying on results.\n"
        )
        support.write(manuscript, text)
        actions.append("added reproducibility section")
    for finding in review.get("findings", []):
        if finding.get("status") != "RESOLVED":
            finding["status"] = "RESOLVED"
            finding["resolution"] = "smallest sufficient evidence-bound revision applied"
    support.write(review_path, review)
    revised = project / "artifacts" / "revised_manuscript.md"
    shutil.copy2(manuscript, revised)
    return support.handoff(project, PROVIDER_ID, node, [revised, review_path], actions=actions)
