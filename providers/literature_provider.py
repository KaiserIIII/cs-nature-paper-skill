"""Local-first and public-network literature discovery with evidence boundaries."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import provider_support as support


PROVIDER_ID = "literature-provider"


def _network_allowed(project: Path) -> bool:
    policy = support.read_json(support.state_dir(project) / "autonomy_policy.json", {})
    return policy.get("permissions", {}).get("network") is True


def _crossref(question: str) -> list[dict[str, Any]]:
    url = "https://api.crossref.org/works?rows=5&query=" + urllib.parse.quote(question)
    request = urllib.request.Request(url, headers={"User-Agent": "cs-nature-paper-provider/3.2.0 (mailto:noreply@example.invalid)"})
    with urllib.request.urlopen(request, timeout=15) as response:  # nosec B310: explicit Crossref endpoint
        payload = json.loads(response.read().decode("utf-8"))
    output = []
    for item in payload.get("message", {}).get("items", []):
        title = (item.get("title") or [""])[0]
        doi = item.get("DOI")
        if title and doi:
            output.append({"title": title, "doi": doi, "url": item.get("URL"), "identity": "VERIFIED_METADATA", "retrieved": False})
    return output


def _local_sources(project: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted((project / "inputs").glob("*")) if (project / "inputs").is_dir() else []:
        if not path.is_file() or path.name in {"research_brief.json", "literature_candidates.json"}:
            continue
        if path.suffix.casefold() not in {".txt", ".md", ".bib", ".pdf"}:
            continue
        exact_region = "binary document; exact region unresolved"
        retrieved = path.suffix.casefold() != ".pdf" and bool(path.read_text(encoding="utf-8", errors="replace").strip())
        if retrieved:
            exact_region = "line 1"
        records.append({
            "title": path.stem, "stable_identifier": support.digest(path), "identity": "VERIFIED_LOCAL",
            "path": path.relative_to(project).as_posix(), "retrieved": retrieved, "exact_region": exact_region,
        })
    return records


def execute(project: Path) -> dict[str, Any]:
    brief = support.read_json(project / "inputs" / "research_brief.json", {})
    question = str(brief.get("question", "")).strip()
    if not question:
        return {"status": "BLOCKED", "findings": ["research question is required"]}
    local = _local_sources(project)
    candidates = support.read_json(project / "inputs" / "literature_candidates.json", [])
    source_mode = "LOCAL"
    if not local:
        if not _network_allowed(project):
            return {"status": "BLOCKED", "findings": ["no local source and public network is not authorized"]}
        source_mode = "WEB"
        if not isinstance(candidates, list) or not candidates:
            try:
                candidates = _crossref(question)
            except (OSError, ValueError, TimeoutError):
                candidates = []
        if not candidates:
            return {"status": "UNAVAILABLE", "findings": ["authorized public literature provider returned no candidates"]}
    sources = local or [
        {
            "title": item.get("title"), "stable_identifier": item.get("doi") or item.get("url"),
            "identity": item.get("identity", "VERIFIED_METADATA"), "retrieved": bool(item.get("retrieved")),
            "exact_region": item.get("exact_region", "UNRESOLVED"),
        }
        for item in candidates if isinstance(item, dict) and item.get("title") and (item.get("doi") or item.get("url"))
    ]
    retrievals = [
        {
            "id": f"RR{index}", "source": item.get("path") or item.get("stable_identifier"),
            "identity": item.get("identity"), "retrieved": item.get("retrieved"),
            "exact_region": item.get("exact_region"), "load_bearing_eligible": bool(item.get("retrieved") and item.get("exact_region") not in {None, "UNRESOLVED"}),
        }
        for index, item in enumerate(sources, 1)
    ]
    relations = [
        {"source_id": f"S{index}", "claim_id": "BACKGROUND", "relation": "CONTEXT", "exact_region": item.get("exact_region")}
        for index, item in enumerate(retrievals, 1)
    ]
    value = {
        "queries": [question, f"{question} closest work", f"{question} recent review"],
        "candidate_sources": candidates or local,
        "sources": [{"id": f"S{index}", **item} for index, item in enumerate(sources, 1)],
        "verified_identities": [item for item in sources if str(item.get("identity", "")).startswith("VERIFIED")],
        "retrieval_records": retrievals,
        "closest_work": [item.get("title") for item in sources[:2]],
        "seminal_work": [], "recent_work": [item.get("title") for item in sources[:3]],
        "claim_relations": relations,
        "remaining_uncertainty": ["metadata or snippets are not load-bearing evidence"] if not any(item["load_bearing_eligible"] for item in retrievals) else [],
        "source_mode": source_mode,
    }
    artifact = support.write(project / "artifacts" / "literature.json", value)
    registry = support.read_json(support.state_dir(project) / "literature_registry.json", {})
    registry.update({"sources": value["sources"], "retrieval_records": retrievals, "claim_relations": relations})
    support.write(support.state_dir(project) / "literature_registry.json", registry)
    return support.handoff(
        project, PROVIDER_ID, "literature", [artifact],
        uncertainties=value["remaining_uncertainty"],
        extra={"sources": value["sources"], "retrieval_records": retrievals, "verified_relations": relations, "network_used": source_mode == "WEB"},
    )
