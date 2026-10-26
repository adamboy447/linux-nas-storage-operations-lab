# v1.0 build progress

This is the working checklist, not a claim that tests have passed.

- [x] Inspect host: Windows 11 Home, Ryzen 5 7535HS, 31.2 GiB RAM, initially 68.8 GiB free.
- [x] Download official Ubuntu Server 24.04 cloud image.
- [x] Verify image checksum and boot two QEMU/WHPX VMs.
- [x] Install authenticated SMB, read-only NFS and separate data/repository disks.
- [x] Deploy Restic, retention, integrity checks and restore tests.
- [x] Deploy persistent scheduling, metrics, dashboards and notifications.
- [x] Test Windows SMB and Linux SMB/NFS permissions.
- [x] Run four failure drills and one data/service DR exercise.
- [x] Gracefully stop/restart both VMs, then revalidate mounts, services, containers, Windows access and jobs.
- [x] Verify all 12 Grafana panel queries through its real datasource proxy.
- [x] Save measured reports, runbooks and rebuild settings.

Browser visual checks/screenshots were blocked by the browser-origin permission gate. This does not change the recorded API/functional test results; see the measured report for the exact verification boundary.

All generated credentials, VM disks and machine state belong in ignored `.runtime/`.
