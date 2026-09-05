import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('quality_runtime', ROOT / 'scripts/provider_runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def specialist(capability='evidence-bound-writing'):
    record = runtime.provider('installed-specialist', 'EXTERNAL_SKILL', [capability],
                              formal_eligible=True, quality_level='FORMAL_QUALIFIED')
    record.update({
        'exact_ref': 'a' * 40,
        'static_audit': {'status': 'PASS', 'exact_commit': 'a' * 40},
        'capability_verification': {
            'status': 'CONFIRMED', 'requested_capability': capability, 'formal_eligible': True,
            'semantic_audit': {'status': 'CONFIRMED', 'actor': 'semantic-auditor', 'evidence': ['SKILL.md:10']},
            'behavior_trial': {'status': 'PASS', 'output_contract': 'PASS', 'checker': 'independent-trial-checker'},
        },
    })
    return record


class ProviderQualityTests(unittest.TestCase):
    def route(self, capability, providers, **task):
        return runtime.resolve_provider(capability, task, True, 'HIGH', {'auto_hire'}, providers)

    def test_formal_eligibility_does_not_inflate_quality(self):
        record = runtime.provider('native', 'NATIVE', ['file-read'], formal_eligible=True)
        self.assertEqual(record['quality_level'], 'GENERAL')

    def test_formal_writing_requires_discovery_before_general_host(self):
        native = runtime.provider('native', 'NATIVE', ['evidence-bound-writing'],
                                  formal_eligible=True, quality_level='BASELINE')
        host = runtime.provider('host', 'HOST_LLM', ['evidence-bound-writing'],
                                qualification='HOST_REQUEST_CAPABLE')
        result = self.route('evidence-bound-writing', [native, host])
        self.assertEqual(result['status'], 'SPECIALIST_DISCOVERY')
        self.assertTrue(result['specialist_required'])
        self.assertTrue(result['discovery_required'])

    def test_failed_discovery_uses_existing_host_request_lifecycle(self):
        host = runtime.provider('host', 'HOST_LLM', ['evidence-bound-writing'],
                                qualification='HOST_REQUEST_CAPABLE')
        result = self.route('evidence-bound-writing', [host], discovery_attempted=True)
        self.assertEqual(result['status'], 'HOST_EXECUTION_REQUIRED')
        self.assertFalse(result['discovery_required'])
        self.assertEqual(result['truth_authority'], 'DETERMINISTIC_CHECKER')

    def test_specialized_statistics_is_detected_without_manual_flag(self):
        native = runtime.provider('native', 'NATIVE', ['statistical-analysis'], formal_eligible=True)
        for description in ('conformal inference', 'risk-controlled acceptance', 'clustered observations',
                            'distribution shift', 'mixed-effects modeling', 'selective prediction'):
            with self.subTest(description=description):
                result = self.route('statistical-analysis', [native], description=description)
                self.assertEqual(result['status'], 'SPECIALIST_DISCOVERY')

    def test_descriptive_statistics_and_ordinary_code_keep_native_priority(self):
        for capability, description in [('statistical-analysis', 'basic descriptive mean and variance'),
                                         ('code-generation', 'implement conformal data loader'),
                                         ('provenance-checking', 'verify formal writing artifact hashes')]:
            with self.subTest(capability=capability):
                native = runtime.provider('native', 'NATIVE', [capability], formal_eligible=True)
                other = specialist(capability)
                result = self.route(capability, [other, native], description=description)
                self.assertEqual(result['provider']['provider_id'], 'native')
                self.assertFalse(result['specialist_required'])

    def test_fully_qualified_matching_installed_specialist_wins(self):
        result = self.route('evidence-bound-writing', [specialist()])
        self.assertEqual(result['status'], 'PASS')
        self.assertTrue(result['specialist_required'])
        self.assertFalse(result['discovery_required'])

    def test_quality_label_cannot_replace_exact_capability_qualification(self):
        changes = [
            ('exact_ref', 'main'), ('formal_eligible', False), ('installed', False),
            ('static_audit', {'status': 'FAIL', 'exact_commit': 'a' * 40}),
            ('static_audit', {'status': 'PASS', 'exact_commit': 'b' * 40}),
            ('capability_verification.requested_capability', 'unrelated'),
            ('capability_verification.status', 'UNVERIFIED'),
            ('capability_verification.semantic_audit.evidence', []),
            ('capability_verification.behavior_trial.checker', ''),
        ]
        for path, value in changes:
            with self.subTest(path=path, value=value):
                record = copy.deepcopy(specialist())
                target = record
                fields = path.split('.')
                for field in fields[:-1]:
                    target = target[field]
                target[fields[-1]] = value
                self.assertEqual(self.route('evidence-bound-writing', [record])['status'], 'SPECIALIST_DISCOVERY')

    def test_discovery_does_not_grant_installation_permission(self):
        record = specialist()
        record['permissions'] = ['admin']
        result = self.route('evidence-bound-writing', [record])
        self.assertEqual(result['status'], 'SPECIALIST_DISCOVERY')
        result = runtime.resolve_provider('evidence-bound-writing', {}, True, 'HIGH', set(), [record])
        self.assertEqual(result['status'], 'FALLBACK')


if __name__ == '__main__':
    unittest.main()
