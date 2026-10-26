"""Generate a version-controlled Grafana dashboard from explicit PromQL panels."""
import json
from pathlib import Path

PANELS = [
    ('Node availability', 'up{job="node"}', 'stat', 'short'),
    ('Client share probes', 'naslab_service_probe_success', 'stat', 'short'),
    ('Last job result', 'naslab_job_last_run_success', 'stat', 'short'),
    ('Backup age (hours)', '(time() - naslab_job_last_success_timestamp_seconds{job="backup"}) / 3600', 'stat', 'h'),
    ('Data and repository usage', '100 * (1 - node_filesystem_avail_bytes{mountpoint=~"/srv/nas-data|/srv/restic-repo",fstype="ext4"} / node_filesystem_size_bytes{mountpoint=~"/srv/nas-data|/srv/restic-repo",fstype="ext4"})', 'timeseries', 'percent'),
    ('Filesystem inodes used', '100 * (1 - node_filesystem_files_free{mountpoint=~"/srv/nas-data|/srv/restic-repo"} / node_filesystem_files{mountpoint=~"/srv/nas-data|/srv/restic-repo"})', 'timeseries', 'percent'),
    ('Disk read throughput', 'rate(node_disk_read_bytes_total{device=~"vd.*"}[1m])', 'timeseries', 'Bps'),
    ('Disk write throughput', 'rate(node_disk_written_bytes_total{device=~"vd.*"}[1m])', 'timeseries', 'Bps'),
    ('Disk IOPS', 'rate(node_disk_reads_completed_total{device=~"vd.*"}[1m]) + rate(node_disk_writes_completed_total{device=~"vd.*"}[1m])', 'timeseries', 'iops'),
    ('Job duration', 'naslab_job_duration_seconds', 'timeseries', 's'),
    ('Memory used', '100 * (1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)', 'timeseries', 'percent'),
    ('Firing alerts', 'ALERTS{alertstate="firing"}', 'table', 'short'),
]


def build():
    panels = []
    for index, (title, expr, kind, unit) in enumerate(PANELS):
        panels.append({'id': index + 1, 'title': title, 'type': kind,
            'datasource': {'type': 'prometheus', 'uid': 'prometheus'},
            'gridPos': {'x': (index % 2) * 12, 'y': (index // 2) * 8, 'w': 12, 'h': 8},
            'targets': [{'expr': expr, 'legendFormat': '{{host}} {{job}} {{service}} {{mountpoint}} {{device}}', 'refId': 'A'}],
            'fieldConfig': {'defaults': {'unit': unit}, 'overrides': []},
            'options': {'legend': {'displayMode': 'list', 'placement': 'bottom'}, 'reduceOptions': {'calcs': ['lastNotNull']}}})
    return {'uid': 'naslab-operations', 'title': 'Linux NAS Storage Operations and Disaster Recovery Lab',
        'schemaVersion': 41, 'version': 1, 'editable': True, 'timezone': 'browser',
        'tags': ['NAS', 'backup', 'DR'], 'refresh': '15s', 'time': {'from': 'now-1h', 'to': 'now'},
        'panels': panels}


if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / 'monitoring/grafana/dashboards/storage-operations.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build(), indent=2) + '\n')
