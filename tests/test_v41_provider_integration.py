import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "paperspine:contribution",
    "paperspine:results-validation",
    "paperspine:target-exemplar",
    "paperspine:publication-production",
    "nature:figure",
    "nature:reviewer",
}


def load_runtime():
    spec = importlib.util.spec_from_file_location(
        "v41_provider_adapters", ROOT / "scripts" / "v41_provider_adapters.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def load_contract_runtime():
    spec = importlib.util.spec_from_file_location(
        "v41_provider_contracts_integration", ROOT / "scripts" / "v41_provider_contracts.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_contribution(root: Path) -> Path:
    output = root / "paper"
    output.mkdir()
    (output / "confirmed_contribution.md").write_text(
        """# Confirmed contribution

## Core Contribution
| Field | Decision |
|---|---|
| Main contribution statement | A deterministic audit binds every publication claim to inspected local evidence. |
| Contribution type | new method |
| Reviewer payoff | Reviewers can trace every reported result to a concrete validation artifact. |

## Why This Contribution Is Needed
| Field | Decision |
|---|---|
| Field problem | Existing workflows can report readiness without proving that specialist code executed. |
| Specific gap | Registry-only checks do not establish usable research capability. |
| Concrete challenge | The runtime must stay offline while preserving provenance and fail-closed gates. |
| Why prior work leaves it unresolved | Prior integration recorded candidates but shipped no adapter or executable route. |

## How This Paper Responds
| Field | Decision |
|---|---|
| Design response | Bind selected upstream resources to typed local adapter entrypoints. |
| Evidence required | Executable end-to-end receipts and source-bound hashes are required. |
| Evidence available | Local synthetic fixtures exercise each selected upstream implementation. |
| Evidence missing | Independent behavior qualification remains deliberately pending. |

## Claim Boundary
| Field | Decision |
|---|---|
| Strong claims allowed | The bounded adapter executed and produced the recorded advisory result. |
| Claims to soften or avoid | Do not claim formal scientific qualification or superiority. |
| Novelty risk | Similar orchestration patterns may exist and require separate literature review. |
| Significance risk | Synthetic execution alone does not prove publication-level scientific value. |
""",
        encoding="utf-8",
    )
    return output


def write_results(root: Path) -> Path:
    path = root / "results_validation.md"
    path.write_text(
        """# Results validation

| Results Unit | Contribution Claim Tested | Result/Evidence | Allowed Interpretation | Interpretation NOT Allowed |
|---|---|---|---|---|
| Adapter E2E | C1: real execution | Six entrypoints returned source-bound typed receipts | The local advisory adapters are callable | Formal evidence qualification or scientific superiority |
""",
        encoding="utf-8",
    )
    return path


def write_exemplars(root: Path) -> Path:
    path = root / "target_exemplars.json"
    path.write_text(
        json.dumps(
            {
                "target_venue": "Nature Machine Intelligence",
                "exemplars": [
                    {
                        "source_id": "doi:10.0000/example",
                        "title": "Verified target exemplar",
                        "verified": True,
                        "transferable_patterns": ["problem framing", "evidence architecture"],
                        "non_transferable_content": ["claims", "data", "wording"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def write_figure_source(root: Path) -> Path:
    path = root / "figure.py"
    path.write_text(
        """import matplotlib as mpl
import matplotlib.pyplot as plt
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica"],
    "font.size": 7,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
})
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
    return path


def write_manuscript(root: Path) -> Path:
    path = root / "manuscript.md"
    path.write_text(
        """# Evidence-bound specialist runtime

## Abstract
We report a bounded local runtime and do not claim scientific superiority.

## Methods
All six adapters are exercised offline on deterministic fixtures. Inputs, source hashes,
and outputs are recorded. No model-generated result is treated as ground truth.

## Results
The executed adapters returned typed advisory artifacts. Formal qualification remains pending.

## Limitations
Synthetic fixtures establish callability, not domain validity, novelty, or publication readiness.

## Data and code availability
The fixture and adapter source are included in the release tree.
""",
        encoding="utf-8",
    )
    return path


def write_publication_invocation(root: Path) -> Path:
    manuscript = write_manuscript(root)
    receipt = root / "manuscript_validation.json"
    receipt.write_text('{"status":"PASS","fixture":true}\n', encoding="utf-8")
    source = {"id": "official-guide", "authority": "official", "url": "https://example.org/guide", "checked_at": "2026-09-20"}
    coverage = []
    for area in (
        "title", "abstract", "body", "figures", "tables", "references",
        "attachments", "required_sections", "required_materials",
    ):
        coverage.append(
            {
                "area": area,
                "status": "known" if area == "required_materials" else "not_applicable",
                "source_ids": ["official-guide"],
                "source_locator": f"fixture:{area}",
                "note": "No additional bounded fixture rule." if area != "required_materials" else "",
            }
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
                "sources": [source],
                "format": {"manuscript_formats": ["Markdown"], "source_ids": ["official-guide"]},
                "five_part_preferences": {
                    key: preference
                    for key in (
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
                    "coverage": coverage,
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
    import hashlib

    profile_hash = hashlib.sha256(profile.read_bytes()).hexdigest()
    plan = root / "submission_package_plan.json"
    plan.write_text(
        json.dumps(
            {
                "schema_version": "1.0", "project_root": ".", "target_name": "Fixture Journal",
                "target_profile_sha256": profile_hash,
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
    return invocation


class V41ProviderIntegrationTests(unittest.TestCase):
    def test_selected_upstream_bytes_are_not_eol_normalized_on_windows(self):
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("vendor/selected/v41/** -text", attributes)

    def test_selected_resources_are_installed_and_hash_bound(self):
        runtime = load_runtime()
        audit = runtime.audit_installation()
        self.assertEqual(audit["status"], "PASS", audit)
        self.assertEqual(set(audit["providers"]), EXPECTED)
        for provider in audit["providers"].values():
            self.assertTrue(provider["source_hash"].startswith("sha256:"))
            self.assertTrue(provider["entrypoint"].startswith("v41_provider_adapters:"))
            self.assertTrue(provider["executed_resources"])
            self.assertEqual(provider["integrity"], "PASS")

    def test_registry_exposes_six_advisory_offline_entrypoints(self):
        registry = json.loads(
            (ROOT / "assets" / "registry" / "v41_provider_registry.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual({item["provider_id"] for item in registry["providers"]}, EXPECTED)
        for item in registry["providers"]:
            self.assertEqual(item["execution_class"], "ADVISORY_ONLY")
            self.assertFalse(item["network"])
            self.assertFalse(item["credentials_required"])
            self.assertIn("PUBLIC_CORE", item["modes"])
            self.assertIn("PRIVATE_ULTRA", item["modes"])
            self.assertTrue(item["input_contract"]["required"])
            self.assertTrue(item["output_contract"]["required"])

    def test_main_skill_discovers_and_invokes_selected_advisory_providers(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for provider_id in EXPECTED:
            self.assertIn(f"`{provider_id}`", text)
        self.assertIn("scripts/v41_provider_adapters.py invoke", text)
        self.assertIn("EXTERNAL_PROVIDER_ADVISORY", text)
        self.assertIn("FORMAL_EVIDENCE_INCOMPLETE", text)
        self.assertIn("PUBLIC_CORE", text)
        self.assertIn("PRIVATE_ULTRA", text)

    def test_capability_runtime_routes_then_invokes_real_advisory_provider(self):
        runtime = load_contract_runtime()
        with tempfile.TemporaryDirectory() as temporary:
            result = runtime.invoke_advisory_provider(
                "paperspine:contribution",
                {"output_dir": str(write_contribution(Path(temporary)))},
                {
                    "provider_id": "internal-specialist:publication-editor",
                    "capabilities": ["publication-argument"],
                },
                capability="publication-argument",
                mode="PUBLIC_CORE",
            )
        self.assertEqual(result["status"], "PASS", result)
        self.assertTrue(result["result"]["ok"])
        self.assertEqual(result["qualification_status"], "UNAUDITED")
        self.assertFalse(result["formal_eligible"])
        self.assertTrue(result["evidence"]["executed_resources"])

    def test_all_six_capabilities_execute_real_resources(self):
        runtime = load_runtime()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contribution = write_contribution(root)
            results = write_results(root)
            exemplars = write_exemplars(root)
            figure = write_figure_source(root)
            manuscript = write_manuscript(root)
            publication_request = write_publication_invocation(root)

            requests = {
                "paperspine:contribution": {"output_dir": str(contribution)},
                "paperspine:results-validation": {"artifact_path": str(results)},
                "paperspine:target-exemplar": {"artifact_path": str(exemplars)},
                "paperspine:publication-production": {"request_path": str(publication_request)},
                "nature:figure": {"source_path": str(figure), "backend": "python"},
                "nature:reviewer": {"manuscript_path": str(manuscript)},
            }
            outputs = {
                provider_id: runtime.invoke_provider(
                    provider_id, request, mode="PUBLIC_CORE", formal=False
                )
                for provider_id, request in requests.items()
            }

        self.assertEqual(set(outputs), EXPECTED)
        for provider_id, output in outputs.items():
            with self.subTest(provider_id=provider_id):
                self.assertEqual(output["status"], "PASS", output)
                self.assertEqual(output["provider_id"], provider_id)
                self.assertEqual(output["mode"], "PUBLIC_CORE")
                self.assertTrue(output["advisory_only"])
                self.assertFalse(output["formal_eligible"])
                self.assertTrue(output["evidence"]["executed_resources"])
                self.assertTrue(output["evidence"]["output_hash"].startswith("sha256:"))
                self.assertNotEqual(output["result"], {})

        self.assertTrue(outputs["paperspine:contribution"]["result"]["ok"])
        self.assertEqual(outputs["paperspine:results-validation"]["result"]["mapped_rows"], 1)
        self.assertEqual(outputs["paperspine:target-exemplar"]["result"]["exemplar_count"], 1)
        publication = outputs["paperspine:publication-production"]["result"]
        self.assertEqual(publication["operation"], "assemble")
        self.assertEqual(publication["outcome"], "BUNDLE_READY")
        self.assertTrue(publication["signals"]["submission_bundle_ready"])
        self.assertTrue(publication["artifacts"])
        self.assertIn("counts", outputs["nature:figure"]["result"])
        self.assertEqual(outputs["nature:reviewer"]["result"]["review_basis"], "LOCAL_MANUSCRIPT")

    def test_private_ultra_uses_same_bounded_adapter_without_qualification_escalation(self):
        runtime = load_runtime()
        with tempfile.TemporaryDirectory() as temporary:
            manuscript = write_manuscript(Path(temporary))
            result = runtime.invoke_provider(
                "nature:reviewer",
                {"manuscript_path": str(manuscript)},
                mode="PRIVATE_ULTRA",
                formal=False,
            )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["mode"], "PRIVATE_ULTRA")
        self.assertFalse(result["formal_eligible"])
        self.assertEqual(result["qualification_status"], "UNAUDITED")

    def test_formal_request_is_blocked_and_missing_resource_fails_closed(self):
        runtime = load_runtime()
        blocked = runtime.invoke_provider(
            "nature:reviewer", {"manuscript_path": "missing.md"}, formal=True
        )
        self.assertEqual(blocked["status"], "BLOCKED")
        self.assertEqual(blocked["reason"], "FORMAL_EVIDENCE_INCOMPLETE")
        self.assertFalse(blocked["formal_eligible"])

        with tempfile.TemporaryDirectory() as temporary:
            audit = runtime.audit_installation(root=Path(temporary))
        self.assertEqual(audit["status"], "FAIL")
        self.assertTrue(audit["findings"])

    def test_cli_e2e_executes_adapter_not_registry_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_path = root / "request.json"
            request_path.write_text(
                json.dumps({"output_dir": str(write_contribution(root))}), encoding="utf-8"
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "v41_provider_adapters.py"),
                    "invoke",
                    "paperspine:contribution",
                    "--request",
                    str(request_path),
                    "--mode",
                    "PUBLIC_CORE",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "PASS")
        self.assertTrue(payload["result"]["ok"])
        self.assertIn("contribution_check.py", " ".join(payload["evidence"]["executed_resources"]))

    def test_release_e2e_runner_records_all_six_real_executions(self):
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "specialist-e2e.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "v41_specialist_e2e.py"),
                    "--output",
                    str(report_path),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(set(report["providers"]), EXPECTED)
        self.assertEqual(report["executed_count"], 6)
        for result in report["providers"].values():
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["evidence"]["executed_resources"])
            self.assertEqual(result["qualification_status"], "UNAUDITED")
            self.assertFalse(result["formal_eligible"])


if __name__ == "__main__":
    unittest.main()
