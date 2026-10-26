# Operations runbooks

Start by recording the impact, time and affected host/share. Collect evidence before changes; restore service before undertaking destructive repository repairs.

| Symptom | Runbook |
|---|---|
| Backup/retention/check failed | [Backup failure](backup-failure.md) |
| Filesystem nearly full or mount missing | [Storage capacity](storage-capacity.md) |
| SMB/NFS Client cannot access files | [Share unavailable](share-unavailable.md) |
| Guest/exporter/monitoring unavailable | [Service recovery](service-recovery.md) |
| Files missing or data recovery requested | [Restore procedure](restore-procedure.md) |

Commands are intended for the two lab guests. Host access is via `tools/host.py exec --node <name> --command <command>`.
