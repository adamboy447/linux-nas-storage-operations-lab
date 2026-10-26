"""Provision and configure both guests from versioned source files."""
import concurrent.futures
import json
from pathlib import Path
import sys
import time

from host import ROOT, RUN, NODES, connect, remote, secrets_config, upload_tree


def packages(node):
    upload_tree(node)
    result = remote(node, f'sudo bash /home/labadmin/naslab/infrastructure/provision.sh {node}', 3600)
    (RUN / node / 'provision-result.json').write_text(json.dumps(result, indent=2))
    print(node, 'packages exit', result['code'], result['stdout'][-2500:], result['stderr'][-1500:], flush=True)
    if result['code']: raise RuntimeError(node + ' packages failed')


def configure():
    creds, _ = secrets_config()
    result = remote('nas01', "sudo install -d -m 0700 /root/.ssh; sudo test -f /root/.ssh/naslab-backup || sudo ssh-keygen -q -t ed25519 -N '' -f /root/.ssh/naslab-backup; sudo cat /root/.ssh/naslab-backup.pub")
    if result['code']: raise RuntimeError(result)
    creds['backup_public_key'] = result['stdout'].strip()
    creds['backup_host_key'] = remote('backup01', 'cat /etc/ssh/ssh_host_ed25519_key.pub')['stdout'].strip()
    for node in ('backup01', 'nas01'):
        upload_tree(node)
        c = connect(node)
        try:
            stdin, out, err = c.exec_command(f'sudo python3 /home/labadmin/naslab/infrastructure/configure.py {node}', timeout=240)
            stdin.write(json.dumps(creds))
            stdin.channel.shutdown_write()
            stdout = out.read().decode(errors='replace')
            stderr = err.read().decode(errors='replace')
            status = out.channel.recv_exit_status()
            print(node, status, stdout[-3000:], stderr[-1500:], flush=True)
            if status: raise RuntimeError('Configuration failed: ' + node)
        finally: c.close()


def monitoring():
    creds, _ = secrets_config()
    upload_tree('backup01')
    c = connect('backup01')
    try:
        stdin, out, err = c.exec_command('sudo install -m 0600 /dev/stdin /etc/naslab/monitoring.env')
        stdin.write('GRAFANA_PASSWORD=' + creds['grafana_password'] + '\n')
        stdin.channel.shutdown_write()
        if out.channel.recv_exit_status(): raise RuntimeError(err.read().decode())
    finally: c.close()
    result = remote('backup01', '''sudo mkdir -p /mnt/naslab-nfs
mountpoint -q /mnt/naslab-nfs || sudo mount -t nfs4 -o ro,soft,timeo=20,retrans=1 172.28.90.10:/srv/nas-data/materials /mnt/naslab-nfs
sudo sh -c 'grep -q "172.28.90.10:/srv/nas-data/materials" /etc/fstab || printf "172.28.90.10:/srv/nas-data/materials /mnt/naslab-nfs nfs4 ro,soft,timeo=20,retrans=1,nofail,_netdev 0 0\\n" >> /etc/fstab'
sudo docker compose --env-file /etc/naslab/monitoring.env -f /home/labadmin/naslab/monitoring/compose.yml up -d
''', 1800)
    print(json.dumps(result), flush=True)
    if result['code']: raise RuntimeError('Monitoring deployment failed')


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'packages':
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(packages, NODES))
    elif action == 'configure': configure()
    elif action == 'monitoring': monitoring()
    elif action == 'update':
        for node in NODES:
            upload_tree(node)
            result = remote(node, 'sudo install -m 0644 /home/labadmin/naslab/scripts/naslab.py /opt/naslab/naslab.py; sudo install -m 0644 /home/labadmin/naslab/infrastructure/node-exporter.default /etc/default/prometheus-node-exporter; sudo systemctl restart prometheus-node-exporter')
            print(node, result['code'], result['stderr'])
            if result['code']: raise RuntimeError('Update failed: ' + node)
    elif action == 'upload':
        for node in NODES: upload_tree(node)
    else: raise ValueError(action)
