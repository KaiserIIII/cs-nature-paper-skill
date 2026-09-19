"""Replay the recovered Reviewer payload through the formal V4 control plane."""

import copy
import importlib.util
import json
import tempfile
from pathlib import Path


ROOT = Path.cwd()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load(
    "falsification_obligation_formal_replay",
    ROOT / "scripts" / "falsification_obligation.py",
)
resolver = load(
    "publication_profiles_formal_replay",
    ROOT / "scripts" / "publication_profiles.py",
)
registry = json.loads(
    (ROOT / "assets" / "registry" / "publication_profiles.json").read_text(
        encoding="utf-8"
    )
)
producer_id = "provider:falsification"
checker_id = "checker:falsification"
original_claim = {
    "claim_id": "C-001",
    "text": "The method generalizes beyond the development benchmark.",
    "strength": "HIGH",
    "load_bearing": True,
}


def evidence_for(artifact):
    checks = {
        field: {
            "status": "OBSERVED",
            "evidence_hash": "sha256:"
            + field.encode("utf-8").hex().ljust(64, "0")[:64],
            "summary": f"Recorded evidence for {field}",
        }
        for field in runtime.FIELDS
    }
    return {
        "claim_hash": artifact["claim_hash"],
        "profile_hash": artifact["profile_hash"],
        "obligation_hash": artifact["obligation_hash"],
        "checks": checks,
    }


def rehash(artifact):
    artifact["obligation_hash"] = runtime.canonical_hash(
        {key: value for key, value in artifact.items() if key != "obligation_hash"}
    )


def record(label, artifact, evidence, result):
    return {
        "label": label,
        "artifact_hash": runtime.canonical_hash(artifact),
        "evidence_hash": runtime.canonical_hash(evidence),
        "result_hash": runtime.canonical_hash(result),
        "obligation_hash": artifact.get("obligation_hash"),
        "authority_snapshot_hash": artifact.get("authority_snapshot_hash"),
        "status": result.get("status"),
        "error_code": result.get("error_code"),
    }


with tempfile.TemporaryDirectory() as temporary:
    project = Path(temporary) / "project"
    state = project / ".research-state"
    state.mkdir(parents=True)
    (state / "project.json").write_text(
        json.dumps(
            {
                "schema_version": 3,
                "skill_version": "4.0.0",
                "project_dir": str(project.resolve()),
                "domain": "machine-learning",
                "study_type": "ml-benchmark",
            }
        ),
        encoding="utf-8",
    )
    (state / "research_contract.json").write_text(
        json.dumps(
            {
                "schema_version": 3,
                "skill_version": "4.0.0",
                "project": {
                    "domain": "machine-learning",
                    "study_type": "ml-benchmark",
                },
            }
        ),
        encoding="utf-8",
    )
    claims = {
        "schema_version": 1,
        "skill_version": "4.0.0",
        "claims": [
            {"id": "C-001", **{k: v for k, v in original_claim.items() if k != "claim_id"}},
            {
                "id": "C-002",
                "text": "A different real claim in the same project.",
                "strength": "HIGH",
                "load_bearing": True,
            },
        ],
    }
    claims_path = state / "claims.json"
    claims_path.write_text(json.dumps(claims), encoding="utf-8")

    original_profile = resolver.resolve_profile(
        {"domain": "machine-learning", "study_type": "ml-benchmark"},
        registry["profiles"],
    )
    legacy_artifact = runtime.derive_obligation(
        original_claim, original_profile, producer_id=producer_id
    )
    baseline = runtime.derive_project_obligation(
        project, "C-001", producer_id=producer_id
    )
    baseline_evidence = evidence_for(baseline)
    baseline_result = runtime.check_project_obligation(
        project,
        "C-001",
        baseline,
        baseline_evidence,
        producer_id=producer_id,
        checker_id=checker_id,
    )
    records = [record("baseline", baseline, baseline_evidence, baseline_result)]

    rebound_values = {
        "claim_id": "C-ATTACKER-NONEMPTY",
        "claim_hash": runtime.canonical_hash(
            {**original_claim, "claim_id": "C-ATTACKER-NONEMPTY"}
        ),
        "profile_hash": resolver.resolve_profile(
            {"domain": "software-engineering", "study_type": "empirical"},
            registry["profiles"],
        )["canonical_output_hash"],
    }
    for field, value in rebound_values.items():
        tampered = copy.deepcopy(baseline)
        tampered[field] = value
        rehash(tampered)
        evidence = evidence_for(tampered)
        result = runtime.check_project_obligation(
            project,
            "C-001",
            tampered,
            evidence,
            producer_id=producer_id,
            checker_id=checker_id,
        )
        records.append(record(f"rebind_{field}", tampered, evidence, result))

    other_claim = runtime.derive_project_obligation(
        project, "C-002", producer_id=producer_id
    )
    other_evidence = evidence_for(other_claim)
    other_result = runtime.check_project_obligation(
        project,
        "C-001",
        other_claim,
        other_evidence,
        producer_id=producer_id,
        checker_id=checker_id,
    )
    records.append(record("other_real_claim", other_claim, other_evidence, other_result))

    caller_named_context = runtime.check_obligation(
        baseline,
        baseline_evidence,
        producer_id=producer_id,
        checker_id=checker_id,
        trusted_claim=original_claim,
        trusted_profile=original_profile,
    )
    records.append(
        record(
            "caller_named_trusted_context",
            baseline,
            baseline_evidence,
            caller_named_context,
        )
    )

    claims["claims"][1]["text"] = "Changed after the original snapshot."
    claims_path.write_text(json.dumps(claims), encoding="utf-8")
    stale_result = runtime.check_project_obligation(
        project,
        "C-001",
        baseline,
        baseline_evidence,
        producer_id=producer_id,
        checker_id=checker_id,
    )
    records.append(record("stale_snapshot", baseline, baseline_evidence, stale_result))

    expected = {
        "baseline": ("OBLIGATION_VERIFIED", None),
        "rebind_claim_id": ("OBLIGATION_REJECTED", "OBLIGATION_BINDING_MISMATCH"),
        "rebind_claim_hash": ("OBLIGATION_REJECTED", "OBLIGATION_BINDING_MISMATCH"),
        "rebind_profile_hash": ("OBLIGATION_REJECTED", "OBLIGATION_BINDING_MISMATCH"),
        "other_real_claim": ("OBLIGATION_REJECTED", "OBLIGATION_BINDING_MISMATCH"),
        "caller_named_trusted_context": ("OBLIGATION_REJECTED", "UNTRUSTED_CHECK_CONTEXT"),
        "stale_snapshot": ("OBLIGATION_REJECTED", "OBLIGATION_BINDING_MISMATCH"),
    }
    observed = {
        item["label"]: (item["status"], item["error_code"]) for item in records
    }
    if observed != expected:
        raise SystemExit(
            "formal reviewer replay did not fail closed: "
            + json.dumps({"expected": expected, "observed": observed}, sort_keys=True)
        )

    print(
        json.dumps(
            {
                "entrypoints": {
                    "derive": "derive_project_obligation",
                    "check": "check_project_obligation",
                },
                "legacy_original_obligation_hash": legacy_artifact[
                    "obligation_hash"
                ],
                "records": records,
            },
            indent=2,
            sort_keys=True,
        )
    )
