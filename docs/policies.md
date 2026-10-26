# Backup, retention and monitoring policy

| Work | Default schedule (Asia/Taipei) | Success criterion |
|---|---|---|
| Backup | Every day 21:00 | Complete Restic job, explicit snapshot ID and state update |
| Retention/prune | Sunday 22:00 | Recent complete backup, preview, apply, prune and post-check |
| Full repository integrity | Sunday 23:00 | `check --read-data` reads all repository data without error |
| Restore test | Monday 00:00 | Exact-version fixture SHA-256 and metadata match |
| Health probes | Every ~15 seconds while running | Dedicated mounts valid and Client share probes pass |
| Prometheus scrape/evaluation | Every 15 seconds | Targets up and rules evaluated |

Retention: `--keep-daily 7 --keep-weekly 4 --keep-monthly 3`, restricted to host `nas01` and tag `naslab-v1`. Conditions overlap, so this is not a fixed count of 14 backups. The configured weekly/monthly behaviour needs sufficient real history before it can be assessed; current short-term tests cover syntax, preview, application and a still-readable repository.

All repository jobs use the same local lock and Restic locks. A queued job waits up to 120 seconds for the local lock, then reports a failure requiring retry. Contention is not permission to force-unlock a live job. A failed or partial backup does not update the last successful backup time.

Alerts: filesystem use >80% warning/>90% critical for 2 minutes; Client SMB/NFS probe failure for 2 minutes; backup job failure after 15 seconds; no complete backup in 26 hours; missing metrics and stale health checks. Repository and restore failures have their own job labels. Critical capacity inhibits the duplicate warning. Alertmanager delivers both firing and resolved states to the local inbox.

The capacity drill uses a separate 128 MiB filesystem. No test fills the Windows disk or a VM root filesystem. Backup disruption stops SSH/SFTP with an automatic local recovery timer arranged beforehand. Normal operation has no artificial failure metrics.

NAS data consists of static lab fixtures and sample documents. Files may otherwise change during a file-level backup; application-consistent database backup is outside this policy.

Secret policy: no real passwords, private keys, VM disks or repository content in Git. Random initial credentials are local to the owner; the backup account has no sudo. `restrict` on the backup SSH key disables forwarding/PTY but does not limit the account to one executable. This is not an immutable or ransomware-resistant backup design.
