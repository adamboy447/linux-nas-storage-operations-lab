# SMB/NFS unavailable

1. Determine whether one Client, one share or all Clients are affected. Preserve the error and time.
2. Verify NAS01 reachability and the corresponding TCP service (445 SMB, 2049 NFSv4).
3. On NAS01 inspect `systemctl status smbd nfs-server`, relevant journal output, `findmnt /srv/nas-data`, directory existence and `namei -l` permissions.
4. For SMB check `testparm -s`, the username, Samba account and share write list. A readonly student's denied write is expected behaviour.
5. For NFS inspect `exportfs -v`, Client IP and `/mnt/naslab-nfs` mount options. After service/data recreation, stale NFS handles can require a Client remount.
6. Correct the identified issue and start the service. Do not use broad `chmod 777` as a permission fix.
7. Repeat an authenticated Client read, an intended writer write, and a readonly write denial. Confirm probe metrics and resolved notification.
