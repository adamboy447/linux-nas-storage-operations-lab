"""Exercise a real Persistent=true missed-calendar timer against the production backup unit."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time


def run(args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout


def state():
    return json.loads(Path('/var/lib/naslab/backup.json').read_text())


if __name__ == '__main__':
    unit = Path('/etc/systemd/system/naslab-persistent-validation.timer')
    before = state()
    target = time.time() + 12
    calendar = datetime.fromtimestamp(target, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    unit.write_text(f'''[Unit]
Description=NAS Lab bounded missed-calendar acceptance test
[Timer]
OnCalendar={calendar}
Persistent=true
AccuracySec=1s
Unit=naslab-backup.service
''')
    try:
        run(['systemctl', 'daemon-reload'])
        run(['systemctl', 'start', unit.name])
        run(['systemctl', 'stop', unit.name])
        time.sleep(15)
        while_stopped = state()
        assert while_stopped['last_run'] == before['last_run'], 'Backup unexpectedly ran while validation timer stopped'
        resumed_at = time.time()
        run(['systemctl', 'start', unit.name])
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            after = state()
            if after['last_run'] > resumed_at and after['success']:
                break
            time.sleep(2)
        else: raise RuntimeError('Missed calendar did not trigger a successful backup')
        result = {'pass': True, 'calendar_utc': calendar, 'timer_stopped_across_deadline': True,
            'before_last_run': before['last_run'], 'after_last_run': after['last_run'],
            'production_unit': 'naslab-backup.service', 'snapshot_id': after['details']['snapshot_id'],
            'catchup_delay_seconds': after['last_run'] - resumed_at}
        Path('/var/lib/naslab/schedule-test.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
    finally:
        run(['systemctl', 'stop', unit.name])
        unit.unlink(missing_ok=True)
        run(['systemctl', 'daemon-reload'])
