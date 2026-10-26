#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
role="${1:?nas01 or backup01}"
case "$role" in nas01|backup01) ;; *) exit 2;; esac
apt-get update -q
apt-get install -y -q restic nfs-common smbclient python3 python3-yaml curl jq acl prometheus-node-exporter openssh-server util-linux
if [[ "$role" == nas01 ]]; then
    apt-get install -y -q samba nfs-kernel-server
    mountpoint=/srv/nas-data
    label=NASLAB_DATA
else
    apt-get install -y -q docker.io docker-compose-v2
    mountpoint=/srv/restic-repo
    label=NASLAB_BACKUP
    systemctl enable --now docker
fi
# Only the newly-created, dedicated /dev/vdb may be formatted. Never touch OS disk.
[[ -b /dev/vdb ]] || { echo 'Dedicated virtual data disk /dev/vdb missing'; exit 1; }
if ! blkid /dev/vdb >/dev/null; then
    [[ -z "$(lsblk -nr -o MOUNTPOINT /dev/vdb)" ]] || exit 1
    mkfs.ext4 -L "$label" /dev/vdb
fi
[[ "$(blkid -s LABEL -o value /dev/vdb)" == "$label" ]] || { echo 'Unexpected data disk label'; exit 1; }
mkdir -p "$mountpoint"
uuid="$(blkid -s UUID -o value /dev/vdb)"
grep -q "UUID=$uuid " /etc/fstab || printf 'UUID=%s %s ext4 defaults 0 2\n' "$uuid" "$mountpoint" >>/etc/fstab
mountpoint -q "$mountpoint" || mount "$mountpoint"
install -d -m 0755 /opt/naslab /etc/naslab /var/lib/naslab /var/log/naslab /var/lib/prometheus/node-exporter
install -m 0644 /home/labadmin/naslab/scripts/naslab.py /opt/naslab/naslab.py
install -m 0644 /home/labadmin/naslab/scripts/notifier.py /opt/naslab/notifier.py
install -m 0644 /home/labadmin/naslab/scripts/webhook.py /opt/naslab/webhook.py
systemctl enable --now prometheus-node-exporter
echo "Provision packages and disk completed: $role"
