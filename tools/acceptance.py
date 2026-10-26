"""Run real local integration/drill tests and save measured evidence after each stage."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import urllib.parse
import urllib.request

from host import ROOT, RUN, remote, upload_tree

EVIDENCE = ROOT / 'reports/measured-results/acceptance.json'
REPORT = {'started_at': datetime.now(timezone.utc).isoformat(), 'environment': 'Two Ubuntu 24.04 QEMU/WHPX VMs on one Windows 11 Home laptop', 'tests': []}
if '--resume' in sys.argv and EVIDENCE.exists():
    REPORT = json.loads(EVIDENCE.read_text())


def save():
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(REPORT, indent=2, ensure_ascii=False))


def guest(node, command, expected=0):
    result = remote(node, command, 900)
    if expected is not None and result['code'] != expected:
        raise RuntimeError(json.dumps(result))
    return result


def job(name):
    guest('nas01', 'sudo python3 /opt/naslab/naslab.py ' + name)
    return json.loads(guest('nas01', 'sudo cat /var/lib/naslab/' + name.split()[0] + '.json')['stdout'])


def inject(action):
    return json.loads(guest('nas01', 'sudo python3 /home/labadmin/naslab/tests/guest_scenarios.py ' + action)['stdout'])


def http(url):
    return json.load(urllib.request.urlopen(url, timeout=10))


def notification(name, status, since, timeout=240):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for event in http('http://127.0.0.1:8088/api/events'):
            received = datetime.fromisoformat(event['received_at']).timestamp()
            if received < since: continue
            for alert in event['payload'].get('alerts', []):
                if alert['labels'].get('alertname') == name and alert.get('status') == status:
                    return {'received_at': event['received_at'], 'delay_seconds': received - since,
                            'status': status, 'labels': alert['labels'], 'annotations': alert.get('annotations')}
        time.sleep(5)
    raise RuntimeError(f'Notification timeout: {name} {status}')


def capture(name, operation):
    previous = next((t for t in REPORT['tests'] if t['name'] == name), None)
    if previous and previous['pass']:
        print('ALREADY PASSED', name, flush=True)
        return
    if previous:
        REPORT.setdefault('previous_failed_attempts', []).append(previous)
        REPORT['tests'].remove(previous)
    started = time.time()
    print('START', name, flush=True)
    item = {'name': name, 'started_at': datetime.now(timezone.utc).isoformat()}
    try:
        item['evidence'] = operation()
        item['pass'] = True
    except Exception as exc:
        item['pass'] = False
        item['error'] = str(exc)
        raise
    finally:
        item['duration_seconds'] = time.time() - started
        REPORT['tests'].append(item)
        save()
        print('RESULT', name, item['pass'], round(item['duration_seconds'], 2), flush=True)


def baseline():
    linux = guest('backup01', "sudo smbclient //172.28.90.10/materials -A /etc/naslab/smb-probe.conf -c 'get course-guide.txt /tmp/naslab-course.txt'; cat /mnt/naslab-nfs/course-guide.txt; findmnt -n -o OPTIONS /mnt/naslab-nfs")
    denied = guest('backup01', 'sudo touch /mnt/naslab-nfs/should-not-exist', expected=None)
    assert denied['code'] != 0 and 'Read-only file system' in denied['stderr']
    anonymous = guest('backup01', "smbclient //172.28.90.10/materials -N -c ls", expected=None)
    assert anonymous['code'] != 0
    windows = json.loads((RUN / 'windows-smb-result.json').read_text(encoding='utf-8-sig'))
    assert all(row['pass'] for row in windows)
    return {'linux_access': linux, 'nfs_write_denied': denied, 'anonymous_smb_denied': anonymous, 'windows': windows}


def versioning():
    first = job('backup')
    changed = inject('version2')
    second = job('backup')
    assert first['details']['snapshot_id'] != second['details']['snapshot_id']
    REPORT['recovery_snapshot'] = second['details']['snapshot_id']
    return {'version1': first, 'change': changed, 'version2': second,
            'integrity_check': job('repository_check'), 'retention': job('retention --apply')}


def deletion():
    start = time.time()
    missing = inject('delete-file')
    restored = job('restore_test --snapshot ' + REPORT['recovery_snapshot'])
    recovered = inject('recover-file')
    assert recovered['sha256'] == missing['deleted_sha256']
    client = guest('backup01', "sudo smbclient //172.28.90.10/team-share -A /etc/naslab/smb-probe.conf -c 'get fixtures/report.txt /tmp/naslab-recovered-report.txt'; cat /tmp/naslab-recovered-report.txt")
    return {'deletion': missing, 'restore': restored, 'recovered': recovered, 'client': client,
            'rto_seconds': time.time() - start}


def backup_failure():
    start = time.time()
    # Stop both socket and service; QEMU console/host boot remain available for recovery.
    guest('backup01', 'sudo systemctl stop ssh.socket ssh.service')
    try:
        failed = guest('nas01', 'sudo python3 /opt/naslab/naslab.py backup', expected=None)
        assert failed['code'] != 0
        firing = notification('NasLabJobFailed', 'firing', start)
    finally:
        # An already stopped SSH cannot be used for restart: recovery is a short NAS-side SSH
        # scheduled command arranged before stopping in main workflow.
        pass
    deadline = time.monotonic() + 150
    while True:
        try:
            guest('backup01', 'sudo systemctl start ssh.socket ssh.service')
            break
        except Exception:
            if time.monotonic() > deadline: raise
            time.sleep(5)
    recovered_at = time.time()
    successful = job('backup')
    resolved = notification('NasLabJobFailed', 'resolved', recovered_at)
    return {'failed_job': failed, 'firing': firing, 'successful_job': successful, 'resolved': resolved}


def service_failure():
    start = time.time()
    guest('nas01', 'sudo systemctl stop smbd')
    try:
        firing = notification('NasLabServiceUnavailable', 'firing', start)
    finally:
        guest('nas01', 'sudo systemctl start smbd')
    resolved = notification('NasLabServiceUnavailable', 'resolved', time.time() - 2)
    return {'firing': firing, 'resolved': resolved}


def capacity_failure():
    start = time.time()
    up = inject('capacity-up')
    try:
        firing = notification('NasLabStorageCritical', 'firing', start)
    finally:
        down = inject('capacity-down')
    resolved = notification('NasLabStorageCritical', 'resolved', time.time() - 2)
    return {'controlled_filesystem': up, 'firing': firing, 'after_cleanup': down, 'resolved': resolved}


def disaster_recovery():
    start = time.time()
    # Use a fresh validated recovery point immediately before the exercise.
    snapshot = job('backup')
    recovery_point = datetime.fromisoformat(snapshot['details']['snapshot_time'].replace('Z', '+00:00')).timestamp()
    isolated = inject('dr-isolate')
    incident = time.time()
    restored = job('restore_test --snapshot ' + snapshot['details']['snapshot_id'])
    recovered = inject('dr-recover')
    client = guest('backup01', "sudo umount /mnt/naslab-nfs; sudo mount /mnt/naslab-nfs; sudo python3 /opt/naslab/naslab.py healthcheck; sudo smbclient //172.28.90.10/team-share -A /etc/naslab/smb-probe.conf -c 'get fixtures/report.txt /tmp/naslab-dr-report.txt'; cat /tmp/naslab-dr-report.txt")
    return {'snapshot': snapshot, 'isolated': isolated, 'restore': restored, 'recovered': recovered,
        'client': client, 'rto_seconds': time.time() - incident,
        'recovery_point_age_seconds': incident - recovery_point,
        'rto_target_seconds': 1800, 'scope': 'Controlled static share data and SMB/NFS service recovery on existing NAS VM'}


if __name__ == '__main__':
    for node in ('nas01', 'backup01'): upload_tree(node)
    capture('Authenticated SMB and read-only NFS permissions', baseline)
    capture('Versioned backups, read-all-data integrity check and retention', versioning)
    capture('T01 Accidental deletion and exact-version restore', deletion)
    # Arrange guaranteed local automatic recovery before disrupting SSH/SFTP.
    if not any(t['name'].startswith('T02') and t['pass'] for t in REPORT['tests']):
        guest('backup01', "sudo systemd-run --unit=naslab-ssh-drill-recovery --on-active=100s /bin/systemctl start ssh.socket ssh.service")
    capture('T02 SFTP unavailable: failure and recovery notifications', backup_failure)
    capture('T04 SMB outage: failure and recovery notifications', service_failure)
    capture('T03 Capacity pressure: critical and recovery notifications', capacity_failure)
    capture('T08 Data and SMB/NFS service disaster recovery', disaster_recovery)
    REPORT['completed_at'] = datetime.now(timezone.utc).isoformat()
    REPORT['all_passed'] = all(row['pass'] for row in REPORT['tests'])
    save()
    print('Acceptance complete:', REPORT['all_passed'], flush=True)
