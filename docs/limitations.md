# Known limits

1. Both VMs and their disks share one laptop and physical drive. Separate VMs are logical isolation; failure/loss of the laptop can lose both source and backups.
2. BACKUP01 contains both the backup repository and monitoring. Its complete outage also disables Alertmanager/inbox. The SFTP-only drill preserves the monitoring plane and does not demonstrate independent monitoring HA.
3. Sleeping/offline guests cannot make backups or notify. Persistent calendar timers catch up once on return; RPO may exceed 24 hours during downtime or repeated failures.
4. QEMU virtual disks do not expose meaningful physical SMART health in this setup. No fabricated SMART status is reported.
5. No physical RAID, redundant controller, Fibre Channel, Cisco MDS or enterprise vendor administration is included.
6. Static fixture restore tests verify the version-bound SHA-256, file sizes and basic UID/GID/mode. They do not prove application consistency, extended ACL/xattr restoration or every user's file contents.
7. The measured DR scenario restores static shared data and services on an existing NAS VM. A new VM rebuild, recovery of the backup server itself, credential re-enrolment and offsite failover require additional exercises.
8. The backup account can modify its repository. Encryption protects backup contents but does not prevent deletion by a compromised writer. Offline/append-only backups are future extensions.
9. NFS AUTH_SYS with Client IP restrictions and root squash is not Kerberos authentication. The NFS export is read-only and limited to the lab client.
10. Operating system, data and repository disks are dynamically allocated qcow2. Monitor Windows free space as well as guest filesystems; a large virtual capacity is not pre-reserved physical storage.
11. Host paths currently target Windows/Python 3.12/MSYS2 QEMU. Another host may need prerequisite/path adjustment. The supported virtual network start order is NAS01 then BACKUP01.
12. The lab has short measured operating history. Retention over months, long-term capacity prediction and uptime targets cannot be inferred from a brief acceptance run.
