# Daily operations

## Access

Start both VMs using `Start-Lab.ps1`. Grafana login is `admin`; retrieve its password locally from `.runtime/credentials.json`. SMB users are `ta01` and `student01`; their passwords are also in this private file.

Windows 11 on the measured host supports alternative SMB TCP ports. Use an unused local drive and credentials in memory:

```powershell
$labSecrets = Get-Content .runtime\credentials.json -Raw | ConvertFrom-Json
$labSecure = ConvertTo-SecureString $labSecrets.ta_password -AsPlainText -Force
$labCredential = [pscredential]::new('ta01', $labSecure)
New-SmbMapping -LocalPath 'N:' -RemotePath '\\127.0.0.1\materials' -TcpPort 1445 -Credential $labCredential -Persistent $false
# When finished:
Remove-SmbMapping -LocalPath 'N:' -Force
```

Check that N: is unused first. Use `team-share` for shared writable test files. Do not place personal or school data in this test lab without separately planning backup and access controls.

## Routine checks

On NAS01:

```bash
sudo systemctl list-timers 'naslab-*'
sudo journalctl -u naslab-backup.service -n 50 --no-pager
sudo cat /var/lib/naslab/backup.json
findmnt /srv/nas-data
df -h /srv/nas-data
```

On BACKUP01 check `docker ps`, `findmnt /srv/restic-repo`, `/var/lib/naslab/notifications.jsonl` and Client probes. Grafana shows real job status; an absent metric is not evidence of success.

## Backup, verify and restore

Start the corresponding systemd services, or run `sudo python3 /opt/naslab/naslab.py backup`, `repository_check`, `restore_test`.

For an exact version: `sudo python3 /opt/naslab/naslab.py restore_test --snapshot <snapshot-id>`. The default target is an isolated `/srv/nas-restore/<run-id>` and never automatically overwrites current data. The latest result is saved in `/var/lib/naslab/last-restore.json`.

`restore_test` validates the controlled fixture manifest. It is not a blanket checksum assertion for every user file. Repository `check --read-data` covers stored pack data separately.

Only after validation should the administrator copy selected files back with metadata preservation, then verify SMB/NFS access from a Client. Clean up old isolated restore folders after retaining evidence; do not delete the active NAS source or repository.

## Change management

Record the reason, affected service, original settings, validation and rollback before a change. Keep configurations in Git, secrets outside Git. Changes that affect group IDs or permissions require client-level permission retesting.

For monitoring configuration, validate before reload/restart. Host helper `tools/host.py exec` connects through pinned locally recorded guest host keys. Rebuilt VMs have different host keys; verify the replacement before updating the saved known_hosts file.
