"""Collect measured, sanitised final evidence and generate the handoff report."""
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.parse
import urllib.request

from host import ROOT, RUN, NODES, remote, secrets_config

OUT = ROOT / 'reports/measured-results'


def http(path, grafana=False):
    req = urllib.request.Request(('http://127.0.0.1:3000' if grafana else 'http://127.0.0.1:9090') + path)
    if grafana:
        creds, _ = secrets_config()
        token = base64.b64encode(('admin:' + creds['grafana_password']).encode()).decode()
        req.add_header('Authorization', 'Basic ' + token)
    return json.load(urllib.request.urlopen(req, timeout=15))


def checked(node, command):
    result = remote(node, command, 600)
    if result['code']:
        raise RuntimeError(json.dumps(result))
    return result


def collect():
    OUT.mkdir(parents=True, exist_ok=True)
    acceptance = json.loads((OUT / 'acceptance.json').read_text())
    if not acceptance.get('all_passed'):
        raise RuntimeError('Integration acceptance is not complete')
    evidence = {'collected_at': datetime.now(timezone.utc).isoformat(), 'nodes': {}}
    for node in NODES:
        evidence['nodes'][node] = checked(node, "hostname; . /etc/os-release; echo $PRETTY_NAME; uname -r; restic version; dpkg-query -W prometheus-node-exporter; lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINTS; df -h /; systemctl list-timers 'naslab-*' --no-pager")
    evidence['quality_checks'] = checked('nas01', 'set -e; cd /home/labadmin/naslab; python3 -m unittest discover -s tests/unit -v; bash -n infrastructure/provision.sh; shellcheck infrastructure/provision.sh')
    evidence['monitoring_checks'] = checked('backup01', 'set -e; docker_cmd="sudo docker"; sudo docker exec naslab-prometheus-1 promtool check config /etc/prometheus/prometheus.yml; sudo docker exec naslab-alertmanager-1 amtool check-config /etc/alertmanager/alertmanager.yml; sudo docker run --rm --entrypoint promtool -v /home/labadmin/naslab:/repo:ro -w /repo/tests/alert-rules prom/prometheus:v3.15.1 test rules jobs.test.yml; sudo docker ps --format "{{.Names}} {{.Status}}"; sudo docker images --digests --format "{{.Repository}}:{{.Tag}} {{.Digest}}"')
    evidence['schedule_test'] = json.loads(checked('nas01', 'sudo cat /var/lib/naslab/schedule-test.json')['stdout'])
    evidence['encryption_test'] = json.loads(checked('nas01', 'sudo cat /var/lib/naslab/encryption-test.json')['stdout'])
    evidence['systemd_jobs'] = checked('nas01', 'systemctl show naslab-backup.service naslab-verify.service naslab-restore-test.service -p Id -p Result -p ExecMainStatus')
    evidence['targets'] = http('/api/v1/targets')['data']['activeTargets']
    assert all(t['health'] == 'up' for t in evidence['targets'])
    dashboard = http('/api/dashboards/uid/naslab-operations', grafana=True)
    evidence['dashboard'] = {'uid': dashboard['dashboard']['uid'], 'title': dashboard['dashboard']['title'], 'panels': []}
    for panel in dashboard['dashboard']['panels']:
        query = urllib.parse.urlencode({'query': panel['targets'][0]['expr']})
        response = http('/api/datasources/proxy/uid/prometheus/api/v1/query?' + query, grafana=True)
        if response['status'] != 'success': raise RuntimeError(response)
        evidence['dashboard']['panels'].append({'title': panel['title'], 'query_success': True,
            'series_count': len(response['data']['result'])})
    assert len(evidence['dashboard']['panels']) == 12
    evidence['browser_visual_check'] = {'completed': False, 'reason': 'The browser tool refused authority to open the local Grafana origin. No alternate browser or screenshot workaround was used. Dashboard provisioning and every panel query were validated via the authorised service APIs.'}
    evidence['backup_state'] = json.loads(checked('nas01', 'sudo cat /var/lib/naslab/backup.json')['stdout'])
    evidence['repository_check'] = json.loads(checked('nas01', 'sudo cat /var/lib/naslab/repository_check.json')['stdout'])
    evidence['restore_state'] = json.loads(checked('nas01', 'sudo cat /var/lib/naslab/restore_test.json')['stdout'])
    evidence['notifications'] = json.load(urllib.request.urlopen('http://127.0.0.1:8088/api/events'))
    (OUT / 'final-state.json').write_text(json.dumps(evidence, indent=2, ensure_ascii=False))
    dr = next(t['evidence'] for t in acceptance['tests'] if t['name'].startswith('T08'))
    rows = '\n'.join(f'| {t["name"]} | PASS | {t["duration_seconds"]:.2f} s |' for t in acceptance['tests'])
    text = f'''# Measured v1.0 acceptance results

Collected: {evidence['collected_at']}

These are actual local tests, not illustrative result values. The raw evidence is in [acceptance.json](acceptance.json) and [final-state.json](final-state.json).

| Test | Result | Elapsed |
|---|---|---:|
{rows}

## Additional checks

- Five meaningful Python unit tests passed.
- Shell syntax/ShellCheck, Compose deployment, Prometheus configuration/rules and Alertmanager configuration validated.
- Promtool alert-rule tests passed, including failed job and missing metric cases.
- Real stopped-calendar Persistent=true catch-up triggered the production backup service in {evidence['schedule_test']['catchup_delay_seconds']:.2f} seconds after timer reactivation.
- All scrape targets were up; Grafana loaded the 12-panel Dashboard and all 12 queries succeeded through its actual datasource proxy.
- Actual firing and resolved notifications were delivered to the local inbox for the backup, SMB and capacity drills.
- Both VMs were gracefully shut down and restarted; Windows permissions, dedicated mounts, NFS Client access, Docker containers and systemd backup/check/restore jobs were revalidated afterwards.
- The actual encrypted repository rejected an incorrect password; runtime credentials and private keys were excluded from versionable source files.

## DR result

- Scope: {dr['scope']}.
- Snapshot: `{dr['snapshot']['details']['snapshot_id']}`.
- Dataset: approximately {dr['snapshot']['details']['bytes_processed'] / 1048576:.2f} MiB, with 3 deterministic fixture files checked for SHA-256, size and basic UID/GID/mode.
- End-to-end recovery after isolation: **{dr['rto_seconds']:.2f} seconds**, target 1800 seconds.
- Recovery-point age at incident: **{dr['recovery_point_age_seconds']:.2f} seconds**. This is the fresh recovery point used in this exercise, not proof of a sustained 24-hour RPO under laptop downtime.
- Client SMB reading and NFS probes passed after share data/service recovery.

## Issues found and corrected

The initial capacity drill failed because the Ubuntu Node Exporter package excluded `/mnt` by default. The versioned exporter configuration now includes the dedicated test filesystem. The failed attempt remains in `acceptance.json` under `previous_failed_attempts`; the repeated real test passed.

The initial restricted forced-command SSH experiment was removed in favour of a dedicated non-sudo backup account with `restrict` key options. The active design is documented without claiming an SFTP-only sandbox.

## Verification limits

- Browser visual verification/screenshots remain unavailable because the browser tool rejected access to the local origin. No substitute screenshot is presented as real evidence. Backend provisioning and all panel queries were verified.
- Two VMs share one physical laptop. No offsite/HA claim is made.
- Retention over months has not been observed; current tests cover configured policy execution and repository readability.
- The DR exercise uses the existing NAS VM, not a clean new-host or backup-repository-loss rebuild.
'''
    (OUT / 'README.md').write_text(text)
    versions = '# Measured versions\n\n' + '\n'.join('## ' + n + '\n\n```text\n' + value['stdout'] + '\n```\n' for n, value in evidence['nodes'].items())
    versions += '\n## Monitoring images and validation\n\n```text\n' + evidence['monitoring_checks']['stdout'] + '\n```\n'
    (ROOT / 'docs/versions.md').write_text(versions)
    print(json.dumps({'all_acceptance_passed': True, 'dashboard_panels': 12,
        'dr_rto_seconds': dr['rto_seconds'], 'recovery_point_age_seconds': dr['recovery_point_age_seconds'],
        'browser_visual_check': False, 'report': str(OUT / 'README.md')}, indent=2))


if __name__ == '__main__': collect()
