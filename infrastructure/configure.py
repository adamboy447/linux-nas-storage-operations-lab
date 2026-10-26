#!/usr/bin/env python3
"""Configure disposable Lab guests. Secrets arrive over stdin, never command arguments."""
import grp
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys

ROLE = sys.argv[1]
assert ROLE in ('nas01', 'backup01')
C = json.load(sys.stdin)
SRC = Path('/home/labadmin/naslab')


def cmd(args, data=None, check=True):
    return subprocess.run(args, input=data, text=True, check=check, capture_output=True)


def write(path, content, mode=0o644):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    p.chmod(mode)


def account(name, uid):
    try: pwd.getpwnam(name)
    except KeyError: cmd(['useradd', '-m', '-u', str(uid), '-s', '/bin/bash', name])


for script in ('naslab.py', 'webhook.py'):
    shutil.copy2(SRC / 'scripts' / script, '/opt/naslab/' + script)
write('/etc/default/prometheus-node-exporter', (SRC / 'infrastructure/node-exporter.default').read_text())
cmd(['systemctl', 'restart', 'prometheus-node-exporter'])

base_config = {'role': ROLE, 'source': '/srv/nas-data',
               'repository': 'sftp:naslab-backup:/srv/restic-repo/repository',
               'password_file': '/etc/naslab/restic-password'}
write('/etc/naslab/config.json', json.dumps(base_config, indent=2), 0o600)
write('/etc/naslab/restic-password', C['restic_password'] + '\n', 0o600)

if ROLE == 'backup01':
    account('backupuser', 2100)
    info = pwd.getpwnam('backupuser')
    os.chown('/srv/restic-repo', info.pw_uid, info.pw_gid)
    Path('/srv/restic-repo/repository').mkdir(exist_ok=True)
    os.chown('/srv/restic-repo/repository', info.pw_uid, info.pw_gid)
    write('/home/backupuser/.ssh/authorized_keys', 'restrict ' + C['backup_public_key'] + '\n', 0o600)
    os.chmod('/home/backupuser/.ssh', 0o700)
    os.chown('/home/backupuser/.ssh', info.pw_uid, info.pw_gid)
    os.chown('/home/backupuser/.ssh/authorized_keys', info.pw_uid, info.pw_gid)
    write('/etc/naslab/smb-probe.conf', 'username = student01\npassword = ' + C['student_password'] + '\n', 0o600)
    Path('/mnt/naslab-nfs').mkdir(exist_ok=True)
    write('/etc/systemd/system/naslab-webhook.service', '''[Unit]
Description=NAS Lab notification evidence inbox
After=network-online.target
[Service]
ExecStart=/usr/bin/python3 /opt/naslab/webhook.py
Restart=on-failure
ProtectSystem=strict
ReadWritePaths=/var/lib/naslab
NoNewPrivileges=yes
[Install]
WantedBy=multi-user.target
''')
    cmd(['systemctl', 'daemon-reload'])
    cmd(['systemctl', 'enable', '--now', 'naslab-webhook'])
    # Mount NFS after NAS configuration is complete (deploy monitoring step).
else:
    try: grp.getgrnam('naslab')
    except KeyError: cmd(['groupadd', '-g', '2200', 'naslab'])
    for name, uid, secret in [('student01', 2001, 'student_password'), ('ta01', 2002, 'ta_password')]:
        account(name, uid)
        cmd(['usermod', '-aG', 'naslab', name])
        cmd(['smbpasswd', '-s', '-a', name], C[secret] + '\n' + C[secret] + '\n')
    for directory in ('materials', 'team-share', 'ops-config'):
        p = Path('/srv/nas-data') / directory
        p.mkdir(exist_ok=True)
        os.chown(p, pwd.getpwnam('ta01').pw_uid, grp.getgrnam('naslab').gr_gid)
        p.chmod(0o2770 if directory != 'materials' else 0o2775)
    Path('/srv/nas-data/ops-config').chmod(0o700)
    write('/srv/nas-data/.naslab-marker', 'Linux NAS Lab dedicated source\n')
    write('/srv/nas-data/materials/.probe', 'naslab-probe-ok\n')
    write('/srv/nas-data/materials/course-guide.txt', 'NAS Lab course materials: SMB + NFS read-only validation.\n')
    fixtures = Path('/srv/nas-data/team-share/fixtures')
    fixtures.mkdir(exist_ok=True)
    for name, text in [('report.txt', 'Lab report version 1\n'), ('network.conf', 'lab_network=172.28.90.0/24\n')]:
        if not (fixtures / name).exists(): write(fixtures / name, text)
    if not (fixtures / 'sample.bin').exists():
        (fixtures / 'sample.bin').write_bytes(os.urandom(4 * 1024 * 1024))
    cmd(['chown', '-R', 'ta01:naslab', str(fixtures)])
    cmd(['chmod', '-R', 'g+rwX', str(fixtures)])
    smb = '''[global]
    workgroup = WORKGROUP
    server role = standalone server
    security = user
    map to guest = Never
    server min protocol = SMB2
    interfaces = lo wan0 lab0
    bind interfaces only = yes
    log file = /var/log/samba/log.%m
    max log size = 1000
[materials]
    path = /srv/nas-data/materials
    valid users = student01 ta01
    read only = yes
    write list = ta01
    guest ok = no
[team-share]
    path = /srv/nas-data/team-share
    valid users = student01 ta01
    read only = no
    force group = naslab
    create mask = 0660
    directory mask = 2770
'''
    write('/etc/samba/smb.conf', smb)
    write('/etc/exports', '/srv/nas-data/materials 172.28.90.20(ro,sync,no_subtree_check,root_squash)\n')
    cmd(['testparm', '-s'])
    cmd(['exportfs', '-ra'])
    cmd(['systemctl', 'enable', '--now', 'smbd', 'nfs-server'])
    cmd(['systemctl', 'restart', 'smbd', 'nfs-server'])
    host_key = C['backup_host_key'].split()
    write('/root/.ssh/naslab_known_hosts', '172.28.90.20 ' + host_key[0] + ' ' + host_key[1] + '\n', 0o600)
    write('/root/.ssh/config', '''Host naslab-backup
    HostName 172.28.90.20
    User backupuser
    IdentityFile /root/.ssh/naslab-backup
    IdentitiesOnly yes
    BatchMode yes
    StrictHostKeyChecking yes
    UserKnownHostsFile /root/.ssh/naslab_known_hosts
    ConnectTimeout 8
    ServerAliveInterval 15
    ServerAliveCountMax 2
''', 0o600)
    env = os.environ.copy()
    env.update(RESTIC_REPOSITORY=base_config['repository'], RESTIC_PASSWORD_FILE=base_config['password_file'])
    check = subprocess.run(['restic', 'snapshots', '--json'], env=env, capture_output=True)
    if check.returncode:
        init = subprocess.run(['restic', 'init'], env=env, capture_output=True, text=True)
        if init.returncode: raise RuntimeError(init.stderr)

# Explicit calendar jobs use Persistent=true. One shared repository lock serialises jobs.
jobs = {'healthcheck': ('healthcheck', None), 'backup': ('backup', '*-*-* 21:00:00'),
        'maintenance': ('retention --apply', 'Sun *-*-* 22:00:00'),
        'verify': ('repository_check', 'Sun *-*-* 23:00:00'),
        'restore-test': ('restore_test', 'Mon *-*-* 00:00:00')}
for name, (arguments, calendar) in jobs.items():
    if ROLE != 'nas01' and name != 'healthcheck': continue
    write(f'/etc/systemd/system/naslab-{name}.service', f'''[Unit]
Description=NAS Lab {name}
Wants=network-online.target
After=network-online.target
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/naslab/naslab.py {arguments}
TimeoutStartSec=30min
UMask=0022
''')
    schedule = f'OnCalendar={calendar}\nPersistent=true\n' if calendar else 'OnBootSec=30s\nOnUnitInactiveSec=15s\n'
    write(f'/etc/systemd/system/naslab-{name}.timer', f'''[Unit]
Description=Schedule NAS Lab {name}
[Timer]
{schedule}AccuracySec=1s
[Install]
WantedBy=timers.target
''')
cmd(['systemctl', 'daemon-reload'])
for name in jobs:
    if ROLE == 'nas01' or name == 'healthcheck':
        cmd(['systemctl', 'enable', '--now', f'naslab-{name}.timer'])
print('Configured role:', ROLE)
