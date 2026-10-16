"""Real disposable Git roots and tracked state; no network or provider calls."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/check_smoke.py'


def load(name):
    spec = importlib.util.spec_from_file_location('provenance_' + name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = load('check_smoke')


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


def repository(root):
    root.mkdir(parents=True, exist_ok=True)
    git(root, 'init', '-q')
    git(root, 'config', 'core.autocrlf', 'false')
    git(root, 'config', 'core.eol', 'lf')
    (root / 'logic.py').write_text('RESULT = 1\n', encoding='utf-8')
    (root / '.gitignore').write_text('__pycache__/\n*.log\n', encoding='utf-8')
    git(root, 'add', '--', 'logic.py', '.gitignore')
    git(root, '-c', 'user.name=Local provenance fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '-qm', 'Synthetic source state')
    return git(root, 'rev-parse', 'HEAD')


def receipt(path, head, status='PASS'):
    path.write_text(json.dumps({'skill_commit': head, 'status': status}), encoding='utf-8')


class SmokeProvenanceTests(unittest.TestCase):
    def test_clean_repository_keeps_its_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo'
            expected = repository(root)
            self.assertEqual(check.current_commit(root), expected)

    def test_nested_archive_cannot_borrow_parent_commit(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / 'parent'
            repository(parent)
            archive = parent / 'archive'
            archive.mkdir()
            with self.assertRaises(ValueError):
                check.current_commit(archive)

    def test_receipt_for_parent_cannot_verify_a_nested_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / 'parent'
            head = repository(parent)
            archive = parent / 'archive'
            archive.mkdir()
            artifact = archive / 'smoke.json'
            receipt(artifact, head)
            with self.assertRaises(ValueError):
                check.check(artifact, archive)

    def test_archive_cli_returns_structured_unverified(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / 'parent'
            head = repository(parent)
            archive = parent / 'archive'
            archive.mkdir()
            artifact = archive / 'smoke.json'
            receipt(artifact, head)
            result = subprocess.run([sys.executable, str(SCRIPT), str(artifact), '--root', str(archive)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['status'], 'UNVERIFIED')

    def test_linked_worktree_is_an_own_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo'
            head = repository(root)
            linked = Path(temporary) / 'linked'
            git(root, 'worktree', 'add', '--detach', str(linked), 'HEAD')
            self.assertEqual(check.current_commit(linked), head)

    def test_missing_repository_has_no_verifiable_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                check.current_commit(Path(temporary))

    def test_unborn_repository_has_no_verifiable_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            git(root, 'init', '-q')
            with self.assertRaises(ValueError):
                check.current_commit(root)

    def test_stale_and_failed_receipts_keep_existing_semantics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo'
            head = repository(root)
            artifact = root / 'smoke.json'
            for commit, status, expected in [(head, 'PASS', 'PASS'), ('0' * 40, 'PASS', 'STALE'), (head, 'FAIL', 'FAIL')]:
                receipt(artifact, commit, status)
                self.assertEqual(check.check(artifact, root)['status'], expected)

    def test_producer_refuses_a_parent_repository_identity(self):
        smoke = load('smoke_run')
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary) / 'parent'
            repository(parent)
            archive = parent / 'archive'
            archive.mkdir()
            smoke.ROOT = archive
            with self.assertRaises(ValueError):
                smoke._commit()

    def test_receipt_refuses_unstaged_tracked_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo'
            head = repository(root)
            artifact = root / 'smoke.json'
            receipt(artifact, head)
            (root / 'logic.py').write_text('RESULT = 0\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                check.check(artifact, root)

    def test_receipt_refuses_staged_tracked_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo'
            head = repository(root)
            artifact = root / 'smoke.json'
            receipt(artifact, head)
            (root / 'logic.py').write_text('RESULT = 0\n', encoding='utf-8')
            git(root, 'add', '--', 'logic.py')
            with self.assertRaises(ValueError):
                check.check(artifact, root)

    def test_receipt_refuses_deleted_tracked_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo'
            head = repository(root)
            artifact = root / 'smoke.json'
            receipt(artifact, head)
            (root / 'logic.py').unlink()
            with self.assertRaises(ValueError):
                check.check(artifact, root)

    def test_index_change_cannot_hide_behind_a_head_matching_working_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo'
            head = repository(root)
            artifact = root / 'smoke.json'
            receipt(artifact, head)
            source = root / 'logic.py'
            source.write_text('RESULT = 0\n', encoding='utf-8')
            git(root, 'add', '--', 'logic.py')
            source.write_text('RESULT = 1\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                check.check(artifact, root)

    def test_dirty_cli_returns_unverified_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo'
            head = repository(root)
            artifact = root / 'smoke.json'
            receipt(artifact, head)
            (root / 'logic.py').write_text('RESULT = 0\n', encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPT), str(artifact), '--root', str(root)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['status'], 'UNVERIFIED')
            self.assertNotIn('Traceback', result.stderr)

    def test_producer_refuses_dirty_source_before_creating_an_output(self):
        smoke = load('smoke_run')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo'
            repository(root)
            (root / 'logic.py').write_text('RESULT = 0\n', encoding='utf-8')
            smoke.ROOT = root
            output = Path(temporary) / 'result.json'
            with self.assertRaises(ValueError):
                smoke.run(output)
            self.assertFalse(output.exists())

    def test_generated_untracked_and_ignored_artifacts_do_not_dirty_tracked_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo'
            head = repository(root)
            artifact = root / 'smoke.json'
            receipt(artifact, head)
            (root / 'generated.log').write_text('fixture output\n', encoding='utf-8')
            cache = root / '__pycache__'
            cache.mkdir()
            (cache / 'fixture.pyc').write_bytes(b'fixture cache')
            self.assertEqual(check.current_commit(root), head)
            self.assertEqual(check.check(artifact, root)['status'], 'PASS')

    def test_unicode_root_remains_valid_when_python_utf8_mode_is_disabled(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo-\u4e2d\u6587'
            head = repository(root)
            code = '''import importlib.util,json,locale,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("checked",sys.argv[1])
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
commit=module.current_commit(Path(sys.argv[2]))
print(json.dumps({"commit":commit,"utf8_mode":sys.flags.utf8_mode,"encoding":locale.getpreferredencoding(False)}))
'''
            env = dict(os.environ, PYTHONUTF8='0', PYTHONIOENCODING='utf-8')
            result = subprocess.run([sys.executable, '-X', 'utf8=0', '-c', code, str(SCRIPT), str(root)],
                                    env=env, capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertEqual(value['commit'], head)
            self.assertEqual(value['utf8_mode'], 0)
            self.assertEqual(result.stderr, '')

    def test_dirty_unicode_root_cli_stays_structured_outside_utf8_mode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'repo-\u4e2d\u6587'
            head = repository(root)
            artifact = root / 'smoke.json'
            receipt(artifact, head)
            (root / 'logic.py').write_text('RESULT = 0\n', encoding='utf-8')
            env = dict(os.environ, PYTHONUTF8='0', PYTHONIOENCODING='utf-8')
            result = subprocess.run([sys.executable, '-X', 'utf8=0', str(SCRIPT), str(artifact), '--root', str(root)],
                                    env=env, capture_output=True, text=True, encoding='utf-8')
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)['status'], 'UNVERIFIED')
            self.assertEqual(result.stderr, '')


if __name__ == '__main__':
    unittest.main()
