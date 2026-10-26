"""Windows host controller. Runtime credentials and VM disks never enter Git."""
import argparse
import concurrent.futures
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import urllib.request

import paramiko
import pycdlib
import yaml

logging.getLogger('paramiko.transport').setLevel(logging.CRITICAL)

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / '.runtime'
QEMU = Path('C:/msys64/ucrt64/bin/qemu-system-x86_64.exe')
IMG = QEMU.with_name('qemu-img.exe')
NODES = {'nas01': {'ssh': 2221, 'ip': '172.28.90.10', 'ram': 3072, 'disk': '5G', 'mac': '10'},
         'backup01': {'ssh': 2222, 'ip': '172.28.90.20', 'ram': 4096, 'disk': '15G', 'mac': '20'}}


def secrets_config():
    RUN.mkdir(exist_ok=True)
    p = RUN / 'credentials.json'
    if not p.exists():
        p.write_text(json.dumps({k: secrets.token_urlsafe(24) for k in
            ('restic_password', 'ta_password', 'student_password', 'grafana_password')}, indent=2))
    key = RUN / 'admin.key'
    if not key.exists():
        paramiko.RSAKey.generate(3072).write_private_key_file(str(key))
    if os.name == 'nt':
        user = subprocess.check_output(['whoami'], text=True).strip()
        for target in (p, key):
            subprocess.run(['icacls', str(target), '/inheritance:r', '/grant:r', f'{user}:F', 'SYSTEM:F'],
                           check=True, capture_output=True)
    return json.loads(p.read_text()), paramiko.RSAKey.from_private_key_file(str(key))


def prepare():
    config, key = secrets_config()
    base = RUN / 'downloads/ubuntu-24.04-server-cloudimg-amd64.img'
    if not base.exists():
        raise RuntimeError('Download the official Ubuntu cloud image first')
    sums = urllib.request.urlopen('https://cloud-images.ubuntu.com/releases/noble/release/SHA256SUMS').read().decode()
    expected = next(line.split()[0] for line in sums.splitlines()
                    if line.split()[-1].lstrip('*') == base.name)
    actual = hashlib.file_digest(base.open('rb'), 'sha256').hexdigest()
    if expected != actual:
        raise RuntimeError('Ubuntu image SHA256 mismatch')
    (RUN / 'image-checksum.json').write_text(json.dumps({'url': 'https://cloud-images.ubuntu.com/releases/noble/release/' + base.name, 'sha256': actual}))
    for name, node in NODES.items():
        folder = RUN / name
        folder.mkdir(exist_ok=True)
        for filename, args in [('os.qcow2', ['-F', 'qcow2', '-b', str(base), '24G']),
                               ('data.qcow2', [node['disk']])]:
            path = folder / filename
            if not path.exists():
                subprocess.run([str(IMG), 'create', '-f', 'qcow2', *args[:-1], str(path), args[-1]], check=True)
        cloud = {'hostname': name, 'manage_etc_hosts': True, 'ssh_pwauth': False,
                 'timezone': 'Asia/Taipei', 'users': [{'name': 'labadmin', 'groups': ['sudo'],
                 'shell': '/bin/bash', 'sudo': 'ALL=(ALL) NOPASSWD:ALL',
                 'ssh_authorized_keys': [f'{key.get_name()} {key.get_base64()} naslab-host']}],
                 'growpart': {'mode': 'auto', 'devices': ['/']}, 'resize_rootfs': True}
        net = {'version': 2, 'ethernets': {
            'wan0': {'match': {'macaddress': f'52:54:00:11:00:{node["mac"]}'}, 'set-name': 'wan0', 'dhcp4': True},
            'lab0': {'match': {'macaddress': f'52:54:00:22:00:{node["mac"]}'}, 'set-name': 'lab0',
                     'addresses': [node['ip'] + '/24']}}}
        iso = pycdlib.PyCdlib()
        iso.new(interchange_level=3, joliet=3, vol_ident='cidata')
        files = {'user-data': '#cloud-config\n' + yaml.safe_dump(cloud),
                 'meta-data': f'instance-id: naslab-{name}-v1\nlocal-hostname: {name}\n',
                 'network-config': yaml.safe_dump(net)}
        for index, (filename, content) in enumerate(files.items()):
            raw = content.encode()
            iso.add_fp(io.BytesIO(raw), len(raw), iso_path=f'/FILE{index}.;1', joliet_path='/' + filename)
        iso.write(str(folder / 'seed.iso'))
        iso.close()
    print('Prepared two VM disks, cloud-init seeds and verified official image checksum.')


def start(accel='whpx'):
    for name, node in NODES.items():
        folder = RUN / name
        try:
            with socket.create_connection(('127.0.0.1', node['ssh']), timeout=1):
                print(name, 'already listening')
                continue
        except OSError:
            pass
        forwards = f'hostfwd=tcp:127.0.0.1:{node["ssh"]}-:22'
        if name == 'nas01':
            forwards += ',hostfwd=tcp:127.0.0.1:1445-:445'
        else:
            forwards += ',hostfwd=tcp:127.0.0.1:3000-:3000,hostfwd=tcp:127.0.0.1:9090-:9090,hostfwd=tcp:127.0.0.1:9093-:9093,hostfwd=tcp:127.0.0.1:8088-:8088'
        link = 'listen=127.0.0.1:13001' if name == 'nas01' else 'connect=127.0.0.1:13001'
        args = [str(QEMU), '-name', name, '-machine', 'q35', '-accel', accel,
                '-cpu', 'max' if accel == 'tcg' else 'qemu64', '-smp', '2', '-m', str(node['ram']),
                '-drive', f'file={folder / "os.qcow2"},format=qcow2,if=virtio',
                '-drive', f'file={folder / "data.qcow2"},format=qcow2,if=virtio',
                '-drive', f'file={folder / "seed.iso"},media=cdrom,readonly=on',
                '-netdev', f'user,id=wan,{forwards}', '-device', f'virtio-net-pci,netdev=wan,mac=52:54:00:11:00:{node["mac"]}',
                '-netdev', f'socket,id=lab,{link}', '-device', f'virtio-net-pci,netdev=lab,mac=52:54:00:22:00:{node["mac"]}',
                '-display', 'none', '-serial', f'file:{folder / "serial.log"}',
                '-qmp', f'tcp:127.0.0.1:{4441 if name == "nas01" else 4442},server=on,wait=off']
        env = os.environ.copy()
        env['PATH'] = str(QEMU.parent) + os.pathsep + env['PATH']
        with (folder / 'qemu-stderr.log').open('ab') as err:
            proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=err, env=env,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        (folder / 'process.json').write_text(json.dumps({'pid': proc.pid, 'accel': accel, 'args': args}))
        print(name, 'started PID', proc.pid)
        time.sleep(2)


def connect(name):
    c = paramiko.SSHClient()
    known = RUN / f'{name}/known_hosts'
    if known.exists():
        c.load_host_keys(str(known))
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect('127.0.0.1', port=NODES[name]['ssh'], username='labadmin',
              key_filename=str(RUN / 'admin.key'), timeout=8, banner_timeout=15, auth_timeout=15)
    c.save_host_keys(str(known))
    return c


def remote(name, command, timeout=120):
    c = connect(name)
    try:
        _, out, err = c.exec_command(command, timeout=timeout)
        stdout, stderr = out.read().decode(errors='replace'), err.read().decode(errors='replace')
        code = out.channel.recv_exit_status()
        return {'node': name, 'code': code, 'stdout': stdout, 'stderr': stderr}
    finally:
        c.close()


def wait_ready():
    deadline = time.monotonic() + 900
    pending = set(NODES)
    while pending and time.monotonic() < deadline:
        for name in list(pending):
            try:
                result = remote(name, 'cloud-init status; ip -br address; uname -r', 30)
                if result['code'] == 0:
                    print(json.dumps(result), flush=True)
                    pending.remove(name)
            except Exception:
                pass
        if pending:
            print('Waiting for:', ','.join(sorted(pending)), flush=True)
            time.sleep(15)
    if pending:
        raise RuntimeError('VM boot timeout: ' + ','.join(pending))


def upload_tree(name):
    c = connect(name)
    try:
        c.exec_command('mkdir -p /home/labadmin/naslab')[1].channel.recv_exit_status()
        s = c.open_sftp()
        for path in ROOT.rglob('*'):
            rel = path.relative_to(ROOT)
            if any(part in ('.runtime', '.git', '__pycache__') for part in rel.parts):
                continue
            target = '/home/labadmin/naslab/' + rel.as_posix()
            if path.is_dir():
                try:
                    s.mkdir(target)
                except OSError:
                    pass
            elif path.is_file():
                s.put(str(path), target)
        s.close()
    finally:
        c.close()


def shutdown(name):
    port = 4441 if name == 'nas01' else 4442
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=5) as sock:
            stream = sock.makefile('rwb', buffering=0)
            json.loads(stream.readline())
            for message in ({'execute': 'qmp_capabilities'}, {'execute': 'system_powerdown'}):
                stream.write(json.dumps(message).encode() + b'\n')
                while True:
                    reply = json.loads(stream.readline())
                    if 'return' in reply: break
                    if 'error' in reply: raise RuntimeError(reply)
        print(name, 'graceful ACPI shutdown requested')
    except ConnectionRefusedError:
        print(name, 'already stopped')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'start', 'wait', 'exec', 'upload', 'stop'])
    parser.add_argument('--node', choices=NODES, default='nas01')
    parser.add_argument('--accel', default='whpx', choices=['whpx', 'tcg'])
    parser.add_argument('--command', default='hostname')
    args = parser.parse_args()
    if args.action == 'prepare': prepare()
    elif args.action == 'start': start(args.accel)
    elif args.action == 'wait': wait_ready()
    elif args.action == 'upload': upload_tree(args.node)
    elif args.action == 'stop': shutdown(args.node)
    else:
        result = remote(args.node, args.command, 3600)
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(result['code'])
