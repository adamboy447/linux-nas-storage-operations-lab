# Measured versions

## nas01

```text
nas01
Ubuntu 24.04.5 LTS
6.8.0-147-generic
restic 0.16.4 compiled with go1.22.2 on linux/amd64
prometheus-node-exporter	1.7.0-1ubuntu0.3
NAME     SIZE FSTYPE  LABEL           MOUNTPOINTS
sr0       66K iso9660 cidata          
sr1     1024M                         
vda       24G                         
├─vda1    23G ext4    cloudimg-rootfs /
├─vda14    4M                         
├─vda15  106M vfat    UEFI            /boot/efi
└─vda16  913M ext4    BOOT            /boot
vdb        5G ext4    NASLAB_DATA     /srv/nas-data
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda1        23G  2.3G   20G  11% /
NEXT                             LEFT LAST                         PASSED UNIT                      ACTIVATES
Fri 2026-10-23 23:41:46 CST        1s Fri 2026-10-23 23:41:31 CST 14s ago naslab-healthcheck.timer  naslab-healthcheck.service
Sat 2026-10-24 21:00:00 CST       21h Fri 2026-10-23 23:20:57 CST       - naslab-backup.timer       naslab-backup.service
Sun 2026-10-25 22:00:00 CST 1 day 22h Fri 2026-10-23 23:20:57 CST       - naslab-maintenance.timer  naslab-maintenance.service
Sun 2026-10-25 23:00:00 CST 1 day 23h Fri 2026-10-23 23:20:57 CST       - naslab-verify.timer       naslab-verify.service
Mon 2026-10-26 00:00:00 CST    2 days Fri 2026-10-23 23:20:58 CST       - naslab-restore-test.timer naslab-restore-test.service

5 timers listed.
Pass --all to see loaded but inactive timers, too.

```

## backup01

```text
backup01
Ubuntu 24.04.5 LTS
6.8.0-147-generic
restic 0.16.4 compiled with go1.22.2 on linux/amd64
prometheus-node-exporter	1.7.0-1ubuntu0.3
NAME     SIZE FSTYPE  LABEL           MOUNTPOINTS
sr0       66K iso9660 cidata          
sr1     1024M                         
vda       24G                         
├─vda1    23G ext4    cloudimg-rootfs /
├─vda14    4M                         
├─vda15  106M vfat    UEFI            /boot/efi
└─vda16  913M ext4    BOOT            /boot
vdb       15G ext4    NASLAB_BACKUP   /srv/restic-repo
Filesystem      Size  Used Avail Use% Mounted on
/dev/vda1        23G  5.1G   18G  23% /
NEXT                        LEFT LAST                         PASSED UNIT                     ACTIVATES
Fri 2026-10-23 23:41:50 CST   4s Fri 2026-10-23 23:41:35 CST 10s ago naslab-healthcheck.timer naslab-healthcheck.service

1 timers listed.
Pass --all to see loaded but inactive timers, too.

```

## Monitoring images and validation

```text
Checking /etc/prometheus/prometheus.yml
  SUCCESS: 2 rule files found
 SUCCESS: /etc/prometheus/prometheus.yml is valid prometheus config file syntax

Checking /etc/prometheus/rules/backup.yml
  SUCCESS: 3 rules found

Checking /etc/prometheus/rules/storage.yml
  SUCCESS: 6 rules found

Checking '/etc/alertmanager/alertmanager.yml'  SUCCESS
Found:
 - global config
 - route
 - 1 inhibit rules
 - 1 receivers
 - 0 templates

  SUCCESS

naslab-prometheus-1 Up About a minute
naslab-grafana-1 Up About a minute
naslab-alertmanager-1 Up About a minute
prom/prometheus:v3.15.1 sha256:fa3302279710be2f21a8301ec17a8b4f2301fd829bd113839b3b6b02b6f191a2
grafana/grafana:13.2.4 sha256:dbbc38ea21103cefb50396340cd88afec779c7e070b0a7bf5a75b4ce46651d3f
prom/alertmanager:v0.34.1 sha256:e9733bafb1bdef9b00e25a21f8f99dc26a22224bf16641ad754d1649f4c3357a

```
