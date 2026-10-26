# Measured v1.0 acceptance results

Collected: 2026-10-23T15:41:45.236370+00:00

These are actual local tests, not illustrative result values. The raw evidence is in [acceptance.json](acceptance.json) and [final-state.json](final-state.json).

| Test | Result | Elapsed |
|---|---|---:|
| Authenticated SMB and read-only NFS permissions | PASS | 0.67 s |
| Versioned backups, read-all-data integrity check and retention | PASS | 13.70 s |
| T01 Accidental deletion and exact-version restore | PASS | 2.50 s |
| T02 SFTP unavailable: failure and recovery notifications | PASS | 119.77 s |
| T04 SMB outage: failure and recovery notifications | PASS | 191.47 s |
| T03 Capacity pressure: critical and recovery notifications | PASS | 181.18 s |
| T08 Data and SMB/NFS service disaster recovery | PASS | 7.42 s |

## Additional checks

- Five meaningful Python unit tests passed.
- Shell syntax/ShellCheck, Compose deployment, Prometheus configuration/rules and Alertmanager configuration validated.
- Promtool alert-rule tests passed, including failed job and missing metric cases.
- Real stopped-calendar Persistent=true catch-up triggered the production backup service in 2.62 seconds after timer reactivation.
- All scrape targets were up; Grafana loaded the 12-panel Dashboard and all 12 queries succeeded through its actual datasource proxy.
- Actual firing and resolved notifications were delivered to the local inbox for the backup, SMB and capacity drills.
- Both VMs were gracefully shut down and restarted; Windows permissions, dedicated mounts, NFS Client access, Docker containers and systemd backup/check/restore jobs were revalidated afterwards.
- The actual encrypted repository rejected an incorrect password; runtime credentials and private keys were excluded from versionable source files.

## DR result

- Scope: Controlled static share data and SMB/NFS service recovery on existing NAS VM.
- Snapshot: `538a5b690a069481dbead58c975b63a52c82d39d29beb9ce8f9c12e3c1f70c8c`.
- Dataset: approximately 4.00 MiB, with 3 deterministic fixture files checked for SHA-256, size and basic UID/GID/mode.
- End-to-end recovery after isolation: **2.76 seconds**, target 1800 seconds.
- Recovery-point age at incident: **3.04 seconds**. This is the fresh recovery point used in this exercise, not proof of a sustained 24-hour RPO under laptop downtime.
- Client SMB reading and NFS probes passed after share data/service recovery.

## Issues found and corrected

The initial capacity drill failed because the Ubuntu Node Exporter package excluded `/mnt` by default. The versioned exporter configuration now includes the dedicated test filesystem. The failed attempt remains in `acceptance.json` under `previous_failed_attempts`; the repeated real test passed.

The initial restricted forced-command SSH experiment was removed in favour of a dedicated non-sudo backup account with `restrict` key options. The active design is documented without claiming an SFTP-only sandbox.

## Verification limits

- Browser visual verification/screenshots remain unavailable because the browser tool rejected access to the local origin. No substitute screenshot is presented as real evidence. Backend provisioning and all panel queries were verified.
- Two VMs share one physical laptop. No offsite/HA claim is made.
- Retention over months has not been observed; current tests cover configured policy execution and repository readability.
- The DR exercise uses the existing NAS VM, not a clean new-host or backup-repository-loss rebuild.
