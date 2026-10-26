# Capacity / mount incident

1. Identify exact host and mountpoint. Inspect `findmnt`, `df -h` and `df -i` for that filesystem, plus Windows physical free space.
2. Check whether the problem is bytes, inodes, a missing data mount or unexpected data growth. Review Grafana trend and recent changes.
3. For `/mnt/naslab-capacity-test`, only remove its controlled fill file using `guest_scenarios.py capacity-down`. This is the bounded acceptance filesystem.
4. For live data/repository paths, identify the owner and retention requirements before cleanup. A Restic repository cannot be cleaned by deleting arbitrary pack files.
5. Retention requires a recent complete backup and a dry-run preview. Prune itself requires working space.
6. If a mount is missing, stop affected writes/backup, verify UUID/device identity and restore the expected mount. Recheck permissions and Client access.
7. Confirm usage is below thresholds and resolved notification is delivered. Record corrective action such as capacity expansion, quota or reduced retention.
