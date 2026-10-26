"""Bounded fault injection: dedicated fixtures and a 128 MiB loop filesystem only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

DATA = Path('/srv/nas-data')
STATE = Path('/var/lib/naslab')
assert (DATA / '.naslab-marker').exists(), 'Dedicated Lab source identity missing'


def run(args, check=True):
    return subprocess.run(args, check=check, text=True, capture_output=True)


def scenario(action):
    fixture = DATA / 'team-share/fixtures/report.txt'
    if action == 'version2':
        fixture.write_text('Lab report version 2: verified version management\n')
        return {'path': str(fixture), 'sha256': hashlib.sha256(fixture.read_bytes()).hexdigest()}
    if action == 'delete-file':
        before = hashlib.sha256(fixture.read_bytes()).hexdigest()
        fixture.unlink()
        return {'path': str(fixture), 'deleted_sha256': before, 'deleted': not fixture.exists()}
    if action == 'recover-file':
        info = json.loads((STATE / 'last-restore.json').read_text())
        source = Path(info['restored_source']) / 'team-share/fixtures/report.txt'
        assert source.resolve().is_relative_to('/srv/nas-restore')
        run(['cp', '-a', str(source), str(fixture)])
        return {'path': str(fixture), 'sha256': hashlib.sha256(fixture.read_bytes()).hexdigest()}
    if action == 'capacity-up':
        image = STATE / 'capacity-test.ext4'
        mount = Path('/mnt/naslab-capacity-test')
        mount.mkdir(exist_ok=True)
        if not image.exists():
            with image.open('wb') as f: f.truncate(128 * 1024 * 1024)
            run(['mkfs.ext4', '-F', '-m', '0', '-L', 'NASLAB_CAPTEST', str(image)])
        if run(['mountpoint', '-q', str(mount)], check=False).returncode:
            run(['mount', '-o', 'loop', str(image), str(mount)])
        usage = shutil.disk_usage(mount)
        target = int(usage.total * .94) - usage.used
        with (mount / 'controlled-fill.bin').open('wb') as f:
            for _ in range(max(0, target // 1048576)):
                f.write(b'X' * 1048576)
        return {'mountpoint': str(mount), 'used_percent': shutil.disk_usage(mount).used / usage.total * 100}
    if action == 'capacity-down':
        mount = Path('/mnt/naslab-capacity-test')
        if (mount / 'controlled-fill.bin').exists(): (mount / 'controlled-fill.bin').unlink()
        return {'used_percent': shutil.disk_usage(mount).used / shutil.disk_usage(mount).total * 100}
    if action == 'dr-isolate':
        quarantine = DATA / '.lab-quarantine' / str(int(time.time()))
        quarantine.mkdir(parents=True)
        run(['systemctl', 'stop', 'smbd', 'nfs-server'])
        for name in ('materials', 'team-share'):
            source = DATA / name
            assert source.resolve().parent == DATA
            shutil.move(str(source), str(quarantine / name))
        return {'quarantine': str(quarantine), 'shares_unavailable': True}
    if action == 'dr-recover':
        info = json.loads((STATE / 'last-restore.json').read_text())
        restored = Path(info['restored_source'])
        assert restored.resolve().is_relative_to('/srv/nas-restore')
        for name in ('materials', 'team-share'):
            assert not (DATA / name).exists()
            run(['cp', '-a', str(restored / name), str(DATA / name)])
        run(['exportfs', '-ra'])
        run(['systemctl', 'start', 'nfs-server', 'smbd'])
        return {'services_restored': True, 'source_snapshot': info['snapshot_id']}
    raise ValueError(action)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['version2', 'delete-file', 'recover-file', 'capacity-up', 'capacity-down', 'dr-isolate', 'dr-recover'])
    print(json.dumps(scenario(p.parse_args().action)))
