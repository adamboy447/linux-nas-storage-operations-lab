# Restore a known-good version

1. Record deleted/affected path and event time. Determine whether backups after the event already contain the deletion.
2. Inspect saved backup JSON/events or Restic snapshots. Select an explicit pre-incident snapshot ID.
3. Run `sudo python3 /opt/naslab/naslab.py restore_test --snapshot <id>` on NAS01.
4. Inspect `/var/lib/naslab/last-restore.json`. Validate the fixture checksum/metadata result and separately inspect requested user files.
5. Preserve any current files that would be overwritten. Copy only selected validated files back with ownership/mode preservation.
6. Verify access through the actual SMB/NFS Client and confirm intended permissions.
7. Record snapshot time, recovery-point age, elapsed end-to-end RTO and verification results. Use the full DR plan for shared directory/service loss.
