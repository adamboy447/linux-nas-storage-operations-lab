# Guest, exporter or monitoring unavailable

1. Check whether both QEMU processes are running. The management forwards listen only on Windows localhost.
2. Verify guest SSH. If the planned SFTP drill is active, wait for its scheduled recovery rather than treating its temporary SSH rejection as a new failure.
3. Check Node Exporter and healthcheck timer independently. A stale textfile is not proof of a healthy service.
4. On BACKUP01 check Docker and the three `naslab-*` monitoring containers, their logs, configuration and persistent volumes.
5. Validate Prometheus rules with promtool and Alertmanager config with amtool before restart.
6. If the laptop/whole BACKUP01 was down, note that remote notifications were unavailable. Check NAS01 local events after recovery.
7. For a normal full restart, gracefully stop both VMs and use Start-Lab.ps1, which starts NAS01 before BACKUP01. Check NFS remount and all scrape targets afterwards.
