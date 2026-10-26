#!/usr/bin/env python3
"""NAS operations: complete backups, deterministic restore verification and probes."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

CONFIG = Path('/etc/naslab/config.json')
STATE = Path('/var/lib/naslab')
METRICS = Path('/var/lib/prometheus/node-exporter')


def atomic(path, content, mode=0o644):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temp.write_text(content)
    temp.chmod(mode)
    temp.replace(path)


def run(args, timeout=900, check=True, env=None):
    p = subprocess.run(args, text=True, capture_output=True, timeout=timeout, env=env)
    if check and p.returncode:
        raise RuntimeError(f'{args[0]} exited {p.returncode}: {p.stderr[-2000:]} {p.stdout[-1000:]}')
    return p


def config():
    return json.loads(CONFIG.read_text())


def restic(args, timeout=900):
    c = config()
    env = os.environ.copy()
    env.update(RESTIC_REPOSITORY=c['repository'], RESTIC_PASSWORD_FILE=c['password_file'],
               RESTIC_CACHE_DIR='/var/cache/naslab/restic')
    return run(['restic', *args], timeout=timeout, env=env)


def log(event):
    event['time'] = datetime.now(timezone.utc).isoformat()
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'events.jsonl').open('a') as f:
        f.write(json.dumps(event) + '\n')
    print(json.dumps(event), flush=True)


@contextmanager
def lock():
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'repository.lock').open('w') as f:
        deadline = time.monotonic() + 120
        while True:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Another repository operation remained active for 120 seconds; retry later')
                time.sleep(0.2)
        yield


def record(job, success, started, details):
    p = STATE / f'{job}.json'
    previous = json.loads(p.read_text()) if p.exists() else {}
    now = time.time()
    state = {'job': job, 'last_run': now, 'last_success': now if success else previous.get('last_success', 0),
             'success': int(success), 'duration': now - started, 'details': details}
    atomic(p, json.dumps(state, indent=2))
    values = {'last_run_timestamp_seconds': state['last_run'],
              'last_success_timestamp_seconds': state['last_success'],
              'last_run_success': state['success'], 'duration_seconds': state['duration']}
    atomic(METRICS / f'naslab_{job}.prom', ''.join(
        f'naslab_job_{metric}{{job="{job}"}} {value}\n' for metric, value in values.items()))
    log(state.copy())


def assert_mount(path, label):
    result = run(['findmnt', '-n', '-o', 'TARGET,LABEL', '--target', str(path)]).stdout.strip().split()
    if len(result) != 2 or result[0] != str(path) or result[1] != label:
        raise RuntimeError(f'Expected dedicated mount {path} with label {label}; got {result}')


def manifest(root):
    root = Path(root)
    result = {}
    for p in sorted(root.rglob('*')):
        if p.is_file() and not p.is_symlink():
            st = p.stat()
            with p.open('rb') as f:
                digest = hashlib.file_digest(f, 'sha256').hexdigest()
            result[p.relative_to(root).as_posix()] = {'sha256': digest, 'size': st.st_size,
                'mode': st.st_mode & 0o777, 'uid': st.st_uid, 'gid': st.st_gid}
    return result


def compare(expected, actual):
    errors = []
    for name in sorted(set(expected) | set(actual)):
        if name not in actual: errors.append(f'missing: {name}')
        elif name not in expected: errors.append(f'unexpected: {name}')
        elif actual[name] != expected[name]: errors.append(f'content/metadata mismatch: {name}')
    return errors


def preflight():
    c = config()
    assert_mount(c['source'], 'NASLAB_DATA')
    if not (Path(c['source']) / '.naslab-marker').exists():
        raise RuntimeError('Source identity marker missing')
    # Validate the remote mount, not only that a directory exists.
    check = run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', 'naslab-backup',
        'findmnt -n -o TARGET,LABEL --target /srv/restic-repo'], timeout=20).stdout.strip()
    if check.split() != ['/srv/restic-repo', 'NASLAB_BACKUP']:
        raise RuntimeError('Backup repository dedicated mount is missing: ' + check)
    return c


def export_config():
    destination = Path(config()['source']) / 'ops-config/server-config'
    destination.mkdir(parents=True, exist_ok=True)
    for original, filename in [('/etc/samba/smb.conf', 'smb.conf'), ('/etc/exports', 'exports'),
                               ('/etc/fstab', 'fstab.reference')]:
        if Path(original).exists(): shutil.copy2(original, destination / filename)
    accounts = run(['getent', 'passwd']).stdout
    atomic(destination / 'accounts.txt', ''.join(line + '\n' for line in accounts.splitlines()
        if line.split(':')[0] in ['student01', 'ta01', 'labadmin']))
    atomic(destination / 'versions.txt', run(['dpkg-query', '-W', 'restic', 'samba', 'nfs-kernel-server']).stdout)


def backup():
    c = preflight()
    export_config()
    source = Path(c['source'])
    fixtures = source / 'team-share/fixtures'
    expected = manifest(fixtures)
    if not expected:
        raise RuntimeError('Test fixtures unexpectedly empty')
    atomic(source / 'ops-config/fixture-manifest.json', json.dumps(expected, indent=2))
    output = restic(['backup', str(source), '--host', 'nas01', '--tag', 'naslab-v1', '--json']).stdout
    summary = next(json.loads(line) for line in output.splitlines() if json.loads(line).get('message_type') == 'summary')
    snapshot = summary['snapshot_id']
    snapshot_info = json.loads(restic(['snapshots', snapshot, '--json']).stdout)[0]
    return {'snapshot_id': snapshot, 'snapshot_time': snapshot_info['time'], 'files_processed': summary.get('total_files_processed'),
            'bytes_processed': summary.get('total_bytes_processed'), 'data_added': summary.get('data_added')}


def latest():
    snapshots = json.loads(restic(['snapshots', '--host', 'nas01', '--tag', 'naslab-v1', '--json']).stdout)
    if not snapshots: raise RuntimeError('No matching NAS Lab snapshots')
    return max(snapshots, key=lambda x: x['time'])['id']


def restore(snapshot=None):
    snapshot = snapshot or latest()
    if not snapshot or any(ch not in '0123456789abcdef' for ch in snapshot):
        raise RuntimeError('Expected an explicit hexadecimal snapshot ID')
    target = Path('/srv/nas-restore') / f'{int(time.time())}-{os.getpid()}'
    target.mkdir(parents=True)
    restic(['restore', snapshot, '--target', str(target)])
    restored = target / config()['source'].lstrip('/')
    expected = json.loads((restored / 'ops-config/fixture-manifest.json').read_text())
    actual = manifest(restored / 'team-share/fixtures')
    errors = compare(expected, actual)
    if errors: raise RuntimeError('Restore verification failed: ' + '; '.join(errors))
    result = {'snapshot_id': snapshot, 'target': str(target), 'restored_source': str(restored),
              'verified_files': len(expected), 'checksum_and_metadata': 'PASS'}
    atomic(STATE / 'last-restore.json', json.dumps(result, indent=2))
    return result


def retention(apply=False):
    backup_state = json.loads((STATE / 'backup.json').read_text())
    if not backup_state['success'] or time.time() - backup_state['last_success'] > 93600:
        raise RuntimeError('Retention requires a recent completely successful backup')
    args = ['forget', '--host', 'nas01', '--tag', 'naslab-v1', '--keep-daily', '7',
            '--keep-weekly', '4', '--keep-monthly', '3']
    preview = restic([*args, '--dry-run']).stdout
    result = {'dry_run': preview, 'applied': apply}
    if apply:
        result['output'] = restic(args).stdout
        result['prune'] = restic(['prune']).stdout
        result['post_prune_check'] = restic(['check']).stdout
    return result


def health():
    c = config()
    lines = [f'naslab_healthcheck_last_run_timestamp_seconds {time.time()}']
    target = c['source'] if c['role'] == 'nas01' else '/srv/restic-repo'
    expected_label = 'NASLAB_DATA' if c['role'] == 'nas01' else 'NASLAB_BACKUP'
    try:
        assert_mount(target, expected_label)
        mounted = 1
    except Exception:
        mounted = 0
    lines.append(f'naslab_storage_mount_ok {mounted}')
    if c['role'] == 'nas01':
        for service, unit in [('smb', 'smbd'), ('nfs', 'nfs-server')]:
            ok = run(['systemctl', 'is-active', '--quiet', unit], check=False).returncode == 0
            lines.append(f'naslab_service_active{{service="{service}"}} {int(ok)}')
    else:
        for service, args in [('smb', ['smbclient', '//172.28.90.10/materials', '-A', '/etc/naslab/smb-probe.conf', '-c', 'get .probe /dev/null']),
                              ('nfs', ['timeout', '5', 'cat', '/mnt/naslab-nfs/.probe'])]:
            try:
                p = run(args, timeout=8, check=False)
                ok = p.returncode == 0
            except (subprocess.TimeoutExpired, OSError):
                ok = False
            lines.append(f'naslab_service_probe_success{{service="{service}"}} {int(ok)}')
    atomic(METRICS / 'naslab_health.prom', '\n'.join(lines) + '\n')
    return {'role': c['role'], 'metrics': lines}


def execute(job, snapshot=None, apply=False):
    started = time.time()
    try:
        if job == 'healthcheck': return health()
        with lock():
            if job == 'backup': details = backup()
            elif job == 'repository_check': details = {'output': restic(['check', '--read-data']).stdout, 'read_all_data': True}
            elif job == 'restore_test': details = restore(snapshot)
            elif job == 'retention': details = retention(apply)
            else: raise ValueError(job)
        record(job, True, started, details)
        return details
    except Exception as exc:
        record(job, False, started, {'error': str(exc)})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('job', choices=['backup', 'repository_check', 'restore_test', 'retention', 'healthcheck'])
    parser.add_argument('--snapshot')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        result = execute(args.job, args.snapshot, args.apply)
        print(json.dumps(result, indent=2))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
