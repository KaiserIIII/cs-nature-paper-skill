import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path.cwd()
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


runtime = load(
    "falsification_obligation_attack",
    ROOT / "scripts" / "falsification_obligation.py",
)
resolver = load(
    "publication_profiles_attack", ROOT / "scripts" / "publication_profiles.py"
)
registry = json.loads(
    (ROOT / "assets" / "registry" / "publication_profiles.json").read_text(
        encoding="utf-8"
    )
)
profile = resolver.resolve_profile(
    {"domain": "machine-learning", "study_type": "ml-benchmark"},
    registry["profiles"],
)
claim = {
    "claim_id": "C-001",
    "text": "The method generalizes beyond the development benchmark.",
    "strength": "HIGH",
    "load_bearing": True,
}
producer_id = "provider:falsification"
checker_id = "checker:falsification"
baseline = runtime.derive_obligation(claim, profile, producer_id=producer_id)


def evidence_for(artifact):
    checks = {}
    for field in runtime.FIELDS:
        checks[field] = {
            "status": "OBSERVED",
            "evidence_hash": "sha256:"
            + field.encode("utf-8").hex().ljust(64, "0")[:64],
            "summary": f"Recorded evidence for {field}",
        }
    return {
        "claim_hash": artifact["claim_hash"],
        "profile_hash": artifact["profile_hash"],
        "obligation_hash": artifact["obligation_hash"],
        "checks": checks,
    }

def rehash(artifact):
    unsigned = {
        key: value
        for key, value in artifact.items()
        if key != "obligation_hash"
    }
    artifact["obligation_hash"] = runtime.canonical_hash(unsigned)


mutations = {
    "status=NOT_REQUIRED,required=False": lambda value: (
        value.__setitem__("status", "NOT_REQUIRED"),
        value.__setitem__("required", False),
    ),
    "operation=attacker-operation": lambda value: value.__setitem__(
        "operation", "attacker-operation"
    ),
    "confirmation_test.check_id=''": lambda value: value[
        "confirmation_test"
    ].__setitem__("check_id", ""),
    "confirmation_test.description=''": lambda value: value[
        "confirmation_test"
    ].__setitem__("description", ""),
    "claim_id=''": lambda value: value.__setitem__("claim_id", ""),
}

print("BASELINE_ARTIFACT")
print(json.dumps(baseline, indent=2, sort_keys=True))
print("BASELINE_RESULT")
print(
    json.dumps(
        runtime.check_obligation(
            baseline,
            evidence_for(baseline),
            producer_id=producer_id,
            checker_id=checker_id,
        ),
        sort_keys=True,
    )
)
print("ATTACK_RESULTS")
for label, mutate in mutations.items():
    tampered = copy.deepcopy(baseline)
    mutate(tampered)
    rehash(tampered)
    result = runtime.check_obligation(
        tampered,
        evidence_for(tampered),
        producer_id=producer_id,
        checker_id=checker_id,
    )
    verdict = (
        "ATTACK_REPRODUCED"
        if result["status"] == "OBLIGATION_VERIFIED"
        else "ATTACK_REJECTED"
    )
    print(
        json.dumps(
            {
                "mutation": label,
                "recomputed_obligation_hash": tampered["obligation_hash"],
                "call": "check_obligation(tampered, evidence_for(tampered), producer_id='provider:falsification', checker_id='checker:falsification')",
                "actual_result": result,
                "verdict": verdict,
            },
            sort_keys=True,
        )
    )
