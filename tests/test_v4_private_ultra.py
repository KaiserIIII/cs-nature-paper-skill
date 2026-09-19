import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_runtime():
    spec = importlib.util.spec_from_file_location(
        "private_ultra_runtime", ROOT / "scripts" / "private_ultra_runtime.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrivateUltraRegistryTests(unittest.TestCase):
    def test_candidate_audit_covers_requested_skills_and_systems(self):
        runtime = load_runtime()
        value = runtime.load_candidates()
        candidates = {item["id"]: item for item in value["candidates"]}
        required = {
            "ars",
            "ars_codex",
            "k_dense",
            "orchestra_skills",
            "eureka",
            "sisyphus_academica",
            "snl_paper_writing",
            "research_engineering_suite",
            "research_lab_notebook",
            "lab_notes",
            "neuromechanist_research_skills",
            "opencite",
            "experiment_agent",
            "hermes_research_writing",
            "paper_orchestra",
            "ai_scientist_v2",
            "agent_laboratory",
            "deer_flow",
        }
        self.assertEqual(set(candidates), required)
        for item in candidates.values():
            self.assertRegex(item["exact_commit"], r"^[0-9a-f]{40}$")
            for field in (
                "repository",
                "kind",
                "entrypoints",
                "last_meaningful_update",
                "functional_scope",
                "required_host_capabilities",
                "real_execution_support",
                "research_rigor_mechanisms",
                "provenance_mechanisms",
                "known_limitations",
                "behavior_evidence",
                "overlaps",
                "unique_capability",
                "qualification_state",
            ):
                self.assertIn(field, item, (item["id"], field))
        self.assertEqual(runtime.validate_candidates(value), [])

    def test_team_keeps_fourteen_roles_with_provider_layers(self):
        runtime = load_runtime()
        team = runtime.load_team()
        self.assertEqual(len(team["roles"]), 14)
        self.assertEqual(team["layers"], ["PUBLIC_CORE", "PRIVATE_ULTRA"])
        for role in team["roles"]:
            self.assertTrue(role["public_core_provider"])
            self.assertTrue(role["primary_candidates"])
            self.assertTrue(role["checker_candidates"])
            self.assertIn("authority", role)
        self.assertEqual(runtime.validate_team(team, runtime.load_candidates()), [])


class PrivateUltraRoutingTests(unittest.TestCase):
    def qualified_provider(
        self,
        candidate_id,
        capability,
        *,
        comparison="EXTERNAL_BETTER",
        non_redundant=None,
        checker_id="independent-checker",
    ):
        runtime = load_runtime()
        candidate = next(
            item for item in runtime.load_candidates()["candidates"] if item["id"] == candidate_id
        )
        return {
            "provider_id": f"local:{candidate_id}",
            "candidate_id": candidate_id,
            "exact_commit": candidate["exact_commit"],
            "installed": True,
            "entrypoint": f"local-provider://{candidate_id}",
            "capabilities": [capability] + list(non_redundant or []),
            "formal_eligible": True,
            "static_audit": {"status": "PASS", "exact_commit": candidate["exact_commit"]},
            "behavior_evidence": {
                "status": "PASS",
                "task_id": f"trial-{candidate_id}-{capability}",
                "capabilities": [capability] + list(non_redundant or []),
                "output_sha256": "sha256:" + "a" * 64,
                "producer_id": f"producer:{candidate_id}",
                "checker_id": checker_id,
                "comparison_to_public_core": comparison,
                "non_redundant_capabilities": list(non_redundant or []),
            },
        }

    def write_registry(self, providers):
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "private_registry.json"
        path.write_text(json.dumps({"schema_version": "1.0.0", "providers": providers}), encoding="utf-8")
        return temporary, path

    def test_public_core_is_independently_functional(self):
        runtime = load_runtime()
        result = runtime.resolve(
            "literature-evidence",
            "literature-synthesis",
            mode="PUBLIC_CORE",
            criticality="critical",
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["selection_outcome"], "INTERNAL_BETTER")
        self.assertEqual(result["primary"]["provider_id"], "internal-specialist:literature-evidence")
        self.assertEqual(result["layer"], "PUBLIC_CORE")

    def test_static_only_candidate_cannot_enter_formal_work(self):
        runtime = load_runtime()
        candidate = next(item for item in runtime.load_candidates()["candidates"] if item["id"] == "ars")
        unqualified = {
            "provider_id": "local:ars",
            "candidate_id": "ars",
            "exact_commit": candidate["exact_commit"],
            "installed": True,
            "entrypoint": "local-provider://ars",
            "capabilities": ["literature-synthesis"],
            "formal_eligible": True,
            "static_audit": {"status": "PASS", "exact_commit": candidate["exact_commit"]},
            "behavior_evidence": {"status": "NOT_RUN"},
        }
        temporary, path = self.write_registry([unqualified])
        with temporary:
            result = runtime.resolve(
                "literature-evidence",
                "literature-synthesis",
                mode="PRIVATE_ULTRA",
                criticality="critical",
                local_registry=path,
            )
        self.assertEqual(result["primary"]["provider_id"], "internal-specialist:literature-evidence")
        self.assertEqual(result["selection_outcome"], "INTERNAL_BETTER")
        self.assertTrue(any("behavior" in finding.lower() for finding in result["findings"]))

    def test_behavior_qualified_primary_can_outperform_public_core(self):
        runtime = load_runtime()
        provider = self.qualified_provider("ars", "literature-synthesis")
        temporary, path = self.write_registry([provider])
        with temporary:
            result = runtime.resolve(
                "literature-evidence",
                "literature-synthesis",
                mode="PRIVATE_ULTRA",
                criticality="high",
                local_registry=path,
            )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["selection_outcome"], "EXTERNAL_BETTER")
        self.assertEqual(result["primary"]["provider_id"], "local:ars")
        self.assertEqual(result["fallback"]["provider_id"], "internal-specialist:literature-evidence")
        self.assertNotEqual(result["primary"]["provider_id"], result["checker"]["provider_id"])

    def test_critical_node_uses_only_non_redundant_complement(self):
        runtime = load_runtime()
        primary = self.qualified_provider("ars", "literature-synthesis")
        complement = self.qualified_provider(
            "opencite",
            "literature-synthesis",
            comparison="TIE",
            non_redundant=["full-text-acquisition", "citation-identity-verification"],
        )
        redundant = self.qualified_provider(
            "k_dense",
            "literature-synthesis",
            comparison="TIE",
            non_redundant=[],
        )
        temporary, path = self.write_registry([primary, complement, redundant])
        with temporary:
            result = runtime.resolve(
                "literature-evidence",
                "literature-synthesis",
                mode="PRIVATE_ULTRA",
                criticality="critical",
                local_registry=path,
            )
        self.assertEqual(result["selection_outcome"], "ENSEMBLE_COMPLEMENTARY")
        self.assertEqual([item["provider_id"] for item in result["complementary"]], ["local:opencite"])
        self.assertEqual(result["checker"]["provider_id"], "internal-checker:literature-evidence-checker")

    def test_same_producer_and_checker_fails_qualification(self):
        runtime = load_runtime()
        provider = self.qualified_provider(
            "ars",
            "literature-synthesis",
            checker_id="producer:ars",
        )
        temporary, path = self.write_registry([provider])
        with temporary:
            result = runtime.resolve(
                "literature-evidence",
                "literature-synthesis",
                mode="PRIVATE_ULTRA",
                criticality="critical",
                local_registry=path,
            )
        self.assertEqual(result["primary"]["provider_id"], "internal-specialist:literature-evidence")
        self.assertTrue(any("checker" in finding.lower() for finding in result["findings"]))


if __name__ == "__main__":
    unittest.main()
