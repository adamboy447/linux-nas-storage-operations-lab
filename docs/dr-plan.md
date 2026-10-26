# Disaster recovery plan

## Scope and targets

Scenario: controlled loss/isolation of the lab's static `materials` and `team-share` data plus stopped SMB/NFS services. The existing NAS VM and remote repository remain available.

Targets: RPO <=24 hours under normal daily successful backups; small static-share service RTO <=30 minutes. Laptop offline time is not excluded from reported gaps. An actual test reports observed recovery-point age and elapsed recovery time, not a guaranteed annual service objective.

## Procedure

1. Open an incident and record scope, event time, detection time and start of response.
2. Verify BACKUP01 and its dedicated disk are available; inspect repository integrity and recent backup state.
3. Select an explicit snapshot from before the incident. Record its timestamp and ID. Never select an unexamined `latest` after an accidental deletion has already been backed up.
4. Stop affected share access when needed. Preserve faulty/current data in a named quarantine directory rather than overwriting it.
5. Restore into `/srv/nas-restore/<run-id>` using `naslab.py restore_test --snapshot <id>`.
6. Validate that snapshot's fixture manifest, basic metadata and expected files. On mismatch, preserve evidence and choose another usable point; do not report success.
7. Copy validated selected directories/files to the expected active paths with UID/GID/mode preservation.
8. Restore/review Samba/NFS settings if changed, run `testparm -s` and `exportfs -ra`, then start the services.
9. Reconnect the read-only NFS Client if stale handles remain. Verify authenticated SMB and NFS reading; retest readonly denial and intended writer permissions.
10. Record service recovery time, observed recovery-point age, missing data, checksum results and incident closure. Retain before/after evidence and corrective actions.

## Rebuild considerations

For a new NAS VM, the settings export includes Samba/NFS configuration and account UID/GID references. Password databases/private keys are not included in the ordinary sample config export. Recover them via an independently secured secret store or re-enrol credentials, verify host keys, and re-establish access. Follow `docs/setup.md`; this extra scenario must be measured separately.

## Measured report fields

Date; host resources/versions; dataset scope/size; incident/recovery timestamps; snapshot ID/time; isolation steps; restore duration; verification duration; Client confirmation; RTO; recovery-point age; target comparison; exceptions; root cause; follow-up owner.
