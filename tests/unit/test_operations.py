import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('naslab', Path(__file__).resolve().parents[2] / 'scripts/naslab.py')
naslab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(naslab)


class OperationsTests(unittest.TestCase):
    def test_manifest_detects_content_change(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'fixture.txt'
            path.write_text('before')
            expected = naslab.manifest(t)
            path.write_text('after!')
            self.assertTrue(naslab.compare(expected, naslab.manifest(t)))

    def test_missing_and_unexpected_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'original.txt'
            path.write_text('data')
            expected = naslab.manifest(t)
            path.unlink()
            (Path(t) / 'unexpected.txt').write_text('data')
            errors = naslab.compare(expected, naslab.manifest(t))
            self.assertEqual(len(errors), 2)

    def test_permission_change_is_detected(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'file.txt'
            path.write_text('data')
            path.chmod(0o640)
            expected = naslab.manifest(t)
            path.chmod(0o644)
            self.assertTrue(naslab.compare(expected, naslab.manifest(t)))

    def test_failed_run_preserves_last_success(self):
        with tempfile.TemporaryDirectory() as t:
            with patch.object(naslab, 'STATE', Path(t)), patch.object(naslab, 'METRICS', Path(t) / 'metrics'):
                naslab.record('backup', True, 1, {'snapshot_id': 'abcdef'})
                before = json.loads((Path(t) / 'backup.json').read_text())
                naslab.record('backup', False, 1, {'error': 'repository unavailable'})
                after = json.loads((Path(t) / 'backup.json').read_text())
                self.assertEqual(before['last_success'], after['last_success'])
                self.assertEqual(after['success'], 0)
                self.assertIn('last_run_success{job="backup"} 0', (Path(t) / 'metrics/naslab_backup.prom').read_text())

    def test_preflight_rejects_unmounted_source_directory(self):
        result = type('Result', (), {'stdout': '/ ROOTFS\n'})()
        with patch.object(naslab, 'run', return_value=result):
            with self.assertRaises(RuntimeError):
                naslab.assert_mount('/srv/nas-data', 'NASLAB_DATA')


if __name__ == '__main__': unittest.main()
