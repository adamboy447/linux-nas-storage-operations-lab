# Backup failure

1. Identify which `job` failed in Grafana/Alertmanager. A successful backup does not clear a failed restore test automatically.
2. On NAS01, inspect `journalctl -u naslab-backup.service`, `/var/lib/naslab/<job>.json` and `/var/lib/naslab/events.jsonl`. Record the last successful timestamp and snapshot.
3. Confirm `/srv/nas-data` is the expected `NASLAB_DATA` mount. Do not back up an empty underlying directory.
4. Check connectivity to `172.28.90.20:22`, BACKUP01 SSH/socket services, dedicated repository mount and free space.
5. Review root's pinned backup host key and key permissions. Do not disable host-key verification as a routine fix.
6. If there is lock contention, determine whether another job is active. Do not force-unlock a live Restic job.
7. Correct the cause, rerun the failed job, inspect its explicit successful state, and verify the Alertmanager resolved notification.
8. If integrity check failed, preserve repository evidence and consider another valid backup. Avoid pruning or modifying the only copy during diagnosis.
9. Complete the incident timeline, cause, response and preventive action.

SFTP drill recovery is prearranged using a local BACKUP01 systemd timer. If BACKUP01 SSH unexpectedly remains unavailable, inspect its QEMU console or safely restart the lab guest; NAS01 SSH remains independent.
