# Architecture and component ownership

| Component | Location | Responsibility |
|---|---|---|
| Samba/NFS | NAS01 | Authenticated SMB, client-restricted read-only NFS |
| ext4 data disk | NAS01 /dev/vdb | `/srv/nas-data`, label `NASLAB_DATA` |
| Restic runner | NAS01 | Reads local files; sends encrypted backup to BACKUP01 |
| Repository | BACKUP01 /dev/vdb | `/srv/restic-repo/repository`, label `NASLAB_BACKUP` |
| Dedicated backup account | BACKUP01 | No sudo; key restricts forwarding and PTY; account owns repository |
| Node Exporter | Both guests | OS metrics and textfile job/probe results |
| Client probes | BACKUP01 | Reads SMB sentinel with student account and NFS sentinel |
| Prometheus | BACKUP01 Docker | Scrapes every 15 seconds; evaluates rules every 15 seconds |
| Grafana | BACKUP01 Docker | Provisioned, versioned Dashboard |
| Alertmanager | BACKUP01 Docker | Groups notifications and sends firing/resolved webhooks |
| Notification inbox | BACKUP01 systemd | Persists delivery evidence as JSONL, exposes local web/API view |

NAS01: `172.28.90.10`, BACKUP01: `172.28.90.20`. Each guest also uses QEMU NAT `10.0.2.15`; these NAT segments are separate. Dedicated `lab0` traffic goes through QEMU's local socket backend on host port 13001. Windows services reach guests through loopback-only forwards. No host firewall disabling or router port forwarding is required.

NAS01 is the only repository writer. A shared `flock` prevents backup, retention, check and restore test overlap. Restic provides its repository-level locks as an additional layer. Job metadata contains snapshot IDs; Prometheus uses bounded job labels and never stores per-file names.

The Node Exporter scrape sets `honor_labels: true` because custom metrics deliberately use `job="backup"`, `job="restore_test"`, etc. System metrics retain the scrape job `node`.

Backup order: source mount identity → remote mount identity → configuration export → version-bound fixture manifest → Restic backup → record snapshot/time → atomic state and metrics. The previous successful timestamp is preserved after failures.

Restore order: select explicit snapshot → isolated target → read the manifest from that snapshot → verify SHA-256, size, UID/GID and mode → administrator restores validated files to the active share → client-level validation.

Host credentials and disks stay in `.runtime`. No Windows personal folders are part of the backup source. Guest test data is generated specifically for this lab.
