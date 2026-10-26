"""Prove the real repository cannot be opened with an unrelated password."""
import json
import os
from pathlib import Path
import subprocess

if __name__ == '__main__':
    config = json.loads(Path('/etc/naslab/config.json').read_text())
    env = os.environ.copy()
    env.pop('RESTIC_PASSWORD_FILE', None)
    env['RESTIC_PASSWORD'] = 'naslab-intentionally-wrong-non-secret-test-value'
    result = subprocess.run(['restic', '-r', config['repository'], 'snapshots', '--json'],
                            env=env, capture_output=True, text=True, timeout=30)
    passed = result.returncode != 0 and ('wrong password' in result.stderr or 'no key found' in result.stderr)
    output = {'pass': passed, 'wrong_password_exit_code': result.returncode,
              'stderr': result.stderr.strip(), 'test': 'Actual remote repository rejects incorrect decryption password'}
    Path('/var/lib/naslab/encryption-test.json').write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))
    if not passed: raise SystemExit(1)
