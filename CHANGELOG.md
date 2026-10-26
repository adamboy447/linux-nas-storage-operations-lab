# Changelog

## 1.0.0

- Two Ubuntu Server 24.04 QEMU/WHPX VMs with separate data/repository disks.
- Authenticated SMB and client-restricted read-only NFS.
- Encrypted remote Restic backups, version retention and full repository checks.
- Exact-version isolated restore, SHA-256 and basic ownership/mode verification.
- Persistent systemd jobs and health probes.
- Provisioned Grafana, Prometheus and Alertmanager with firing/resolved delivery inbox.
- Controlled failure drills, static-share service DR, measured evidence and runbooks.
- Windows startup/shutdown and SMB permission test scripts.

Acceptance and limitations are documented in `reports/measured-results` and `docs/limitations.md`.
