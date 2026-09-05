"""Local-first literature discovery with explicit evidence-sufficiency states."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import provider_support as support


PROVIDER_ID = "literature-provider"
METADATA_ONLY = "METADATA_ONLY"
FULLTEXT_RETRIEVED = "FULLTEXT_RETRIEVED"
EXACT_REGION_VERIFIED = "EXACT_REGION_VERIFIED"
UNAVAILABLE = "UNAVAILABLE"
_REGION = re.compile(r"^lines?\s+(\d+)(?:\s*[-:]\s*(\d+))?$", re.IGNORECASE)
_MAX_FULL_TEXT = 5 * 1024 * 1024


def _network_allowed(project: Path) -> bool:
    policy = support.read_json(support.state_dir(project) / "autonomy_policy.json", {})
    return policy.get("permissions", {}).get("network") is True


def _crossref(question: str) -> list[dict[str, Any]]:
    url = "https://api.crossref.org/works?rows=5&query=" + urllib.parse.quote(question)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "cs-nature-paper-provider/3.2.1 (mailto:noreply@example.invalid)"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:  # nosec B310: fixed Crossref endpoint
        payload = json.loads(response.read().decode("utf-8"))
    output = []
    for item in payload.get("message", {}).get("items", []):
        title = (item.get("title") or [""])[0]
        doi = item.get("DOI")
        if title and doi:
            output.append(
                {
                    "title": title,
                    "doi": doi,
                    "url": item.get("URL"),
                    "identity": "VERIFIED_METADATA",
                    "retrieved": False,
                }
            )
    return output


def _materialized_path(source: dict[str, Any], project: Path | None = None) -> Path | None:
    raw = source.get("full_text_path")
    if not raw:
        return None
    path = Path(str(raw))
    if not path.is_absolute() and project is not None:
        path = project / path
    return path


def classify_retrieval(source: dict[str, Any], project: Path | None = None) -> dict[str, Any]:
    """Classify a source without treating metadata, snippets, or landing pages as evidence."""
    record = dict(source)
    identifier = source.get("stable_identifier") or source.get("doi") or source.get("url")
    path = _materialized_path(source, project)
    if not identifier and path is None:
        record.update({"retrieval_status": UNAVAILABLE, "load_bearing_eligible": False})
        return record
    if path is None or not path.is_file() or path.stat().st_size == 0:
        record.update({"retrieval_status": METADATA_ONLY, "load_bearing_eligible": False})
        return record

    record["full_text_path"] = str(path)
    record["full_text_sha256"] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    record.update({"retrieval_status": FULLTEXT_RETRIEVED, "load_bearing_eligible": False})
    region = str(source.get("exact_region", "UNRESOLVED")).strip()
    match = _REGION.fullmatch(region)
    producer = str(source.get("inspection_actor", "")).strip()
    checker = str(source.get("checker", "")).strip()
    if not match or not producer or not checker or producer == checker:
        return record

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = int(match.group(1))
    end = int(match.group(2) or start)
    if start < 1 or end < start or end > len(lines):
        record["region_finding"] = "declared exact region is outside the materialized full text"
        return record
    region_text = "\n".join(lines[start - 1 : end])
    if not region_text.strip():
        record["region_finding"] = "declared exact region is empty"
        return record
    record.update(
        {
            "retrieval_status": EXACT_REGION_VERIFIED,
            "load_bearing_eligible": True,
            "region_sha256": "sha256:" + hashlib.sha256(region_text.encode("utf-8")).hexdigest(),
            "verified_region": {"start_line": start, "end_line": end},
        }
    )
    return record


def _retrieve_open_text(project: Path, source: dict[str, Any], index: int) -> dict[str, Any]:
    """Materialize only an explicitly supplied open-access full-text URL."""
    url = source.get("open_access_url") or source.get("full_text_url")
    if not url or urllib.parse.urlparse(str(url)).scheme != "https":
        return source
    destination = support.state_dir(project) / "literature_full_text" / f"source-{index}.txt"
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(str(url), headers={"User-Agent": "cs-nature-paper-provider/3.2.1"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # nosec B310: explicit HTTPS open-access URL
            body = response.read(_MAX_FULL_TEXT + 1)
        if len(body) > _MAX_FULL_TEXT:
            return source | {"retrieval_finding": "open full text exceeded the bounded retrieval size"}
        text = body.decode("utf-8", errors="replace")
        if not text.strip():
            return source
        destination.write_text(text, encoding="utf-8")
        return source | {"full_text_path": destination.relative_to(project).as_posix()}
    except (OSError, ValueError, TimeoutError):
        return source


def _local_sources(project: Path) -> list[dict[str, Any]]:
    records = []
    inputs = project / "inputs"
    for path in sorted(inputs.glob("*")) if inputs.is_dir() else []:
        if not path.is_file() or path.name in {"research_brief.json", "literature_candidates.json"}:
            continue
        if path.suffix.casefold() not in {".txt", ".md", ".bib", ".pdf"}:
            continue
        records.append(
            {
                "title": path.stem,
                "stable_identifier": support.digest(path),
                "identity": "VERIFIED_LOCAL",
                "path": path.relative_to(project).as_posix(),
                "full_text_path": path.relative_to(project).as_posix() if path.suffix.casefold() != ".pdf" else None,
                "exact_region": "UNRESOLVED",
            }
        )
    return records


def _claims(brief: dict[str, Any]) -> list[dict[str, Any]]:
    value = brief.get("load_bearing_literature_claims", brief.get("load_bearing_claims", []))
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict) and item.get("claim_id")]


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

    raw_sources = local or [
        {
            "title": item.get("title"),
            "stable_identifier": item.get("doi") or item.get("stable_identifier") or item.get("url"),
            "identity": item.get("identity", "VERIFIED_METADATA"),
            "exact_region": item.get("exact_region", "UNRESOLVED"),
            "inspection_actor": item.get("inspection_actor"),
            "checker": item.get("checker"),
            "claim_ids": item.get("claim_ids", []),
            "open_access_url": item.get("open_access_url"),
            "full_text_url": item.get("full_text_url"),
            "full_text_path": item.get("full_text_path"),
        }
        for item in candidates
        if isinstance(item, dict) and item.get("title") and (item.get("doi") or item.get("stable_identifier") or item.get("url"))
    ]
    if source_mode == "WEB":
        raw_sources = [_retrieve_open_text(project, item, index) for index, item in enumerate(raw_sources, 1)]

    sources: list[dict[str, Any]] = []
    retrievals: list[dict[str, Any]] = []
    for index, source in enumerate(raw_sources, 1):
        source_id = f"S{index}"
        record = classify_retrieval(source, project)
        sources.append({"id": source_id, **source})
        retrievals.append({"id": f"RR{index}", "source_id": source_id, **record})

    claims = _claims(brief)
    relations: list[dict[str, Any]] = []
    for claim in claims:
        claim_id = claim["claim_id"]
        matched = [item for item in retrievals if claim_id in item.get("claim_ids", [])]
        for item in matched:
            verified = item.get("retrieval_status") == EXACT_REGION_VERIFIED and item.get("load_bearing_eligible") is True
            relations.append(
                {
                    "claim_id": claim_id,
                    "source_id": item["source_id"],
                    "relation": "SUPPORTS" if verified else "BACKGROUND_ONLY",
                    "verification_status": EXACT_REGION_VERIFIED if verified else "NOT_VERIFIED",
                }
            )
        if not matched:
            relations.append(
                {
                    "claim_id": claim_id,
                    "source_id": None,
                    "relation": "BACKGROUND_ONLY",
                    "verification_status": "NOT_VERIFIED",
                }
            )
    verified_relations = [item for item in relations if item["verification_status"] == EXACT_REGION_VERIFIED]
    unresolved = [claim["claim_id"] for claim in claims if not any(item["claim_id"] == claim["claim_id"] for item in verified_relations)]
    novelty_claims = [item["claim_id"] for item in claims if str(item.get("kind", "")).casefold() == "novelty"]
    novelty_status = "SCOPED" if not novelty_claims else ("VERIFIED" if not any(item in unresolved for item in novelty_claims) else "CONDITIONAL")
    gate = "SCOPED_PASS" if not claims else ("PASS" if not unresolved else "CONDITIONAL")
    remaining_gap = [f"load-bearing literature claim lacks exact-region verification: {item}" for item in unresolved]
    if not claims:
        remaining_gap = ["no load-bearing literature claim was declared; literature is background-only"]
    value = {
        "queries": [question, f"{question} closest work", f"{question} recent review"],
        "candidate_sources": candidates or local,
        "sources": sources,
        "verified_identities": [item for item in sources if str(item.get("identity", "")).startswith("VERIFIED")],
        "retrieval_records": retrievals,
        "full_text_retrieval": [item for item in retrievals if item.get("retrieval_status") in {FULLTEXT_RETRIEVED, EXACT_REGION_VERIFIED}],
        "closest_work": [item.get("title") for item in sources[:2]],
        "seminal_work": [],
        "recent_work": [item.get("title") for item in sources[:3]],
        "load_bearing_claims": claims,
        "claim_relations": relations,
        "verified_relations": verified_relations,
        "literature_gate_status": gate,
        "novelty_status": novelty_status,
        "remaining_gap": remaining_gap,
        "remaining_uncertainty": remaining_gap,
        "source_mode": source_mode,
    }
    artifact = support.write(project / "artifacts" / "literature.json", value)
    registry = support.read_json(support.state_dir(project) / "literature_registry.json", {})
    registry.update(
        {
            "sources": sources,
            "retrieval_records": retrievals,
            "claim_relations": relations,
            "verified_relations": verified_relations,
        }
    )
    support.write(support.state_dir(project) / "literature_registry.json", registry)
    return support.handoff(
        project,
        PROVIDER_ID,
        "literature",
        [artifact],
        uncertainties=remaining_gap,
        extra={
            "sources": sources,
            "retrieval_records": retrievals,
            "verified_relations": verified_relations,
            "literature_gate_status": gate,
            "novelty_status": novelty_status,
            "network_used": source_mode == "WEB",
        },
    )
