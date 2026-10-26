# Installation and reproducible rebuild

## Windows prerequisites

The measured host uses Windows 11 Home with firmware virtualisation enabled and Windows Hypervisor Platform already available. QEMU/WHPX successfully booted both guests without adding a Windows driver or rebooting. NAS01 uses 3 GB RAM; BACKUP01 uses 4 GB RAM. Dynamic qcow2 disks reduce allocated physical space but can grow up to their configured capacity.

Install QEMU from the MSYS2 official package registry, as used by this build:

```powershell
& C:\msys64\usr\bin\bash.exe -lc 'pacman -S --needed --noconfirm mingw-w64-ucrt-x86_64-qemu'
py -3.12 -m pip install -r requirements-host.txt
```

If MSYS2/Python are not installed on another host, install them from their official distributions first. `tools/host.py` currently expects `C:/msys64/ucrt64/bin`. Update that path when using another QEMU distribution. If WHPX is unavailable, enable Windows Hypervisor Platform and reboot, or select `--accel tcg` for slower software emulation.

Download the official Ubuntu image into `.runtime/downloads/ubuntu-24.04-server-cloudimg-amd64.img`:

```powershell
New-Item -ItemType Directory -Force .runtime\downloads
curl.exe -L --fail --output .runtime\downloads\ubuntu-24.04-server-cloudimg-amd64.img https://cloud-images.ubuntu.com/releases/noble/release/ubuntu-24.04-server-cloudimg-amd64.img
```

`prepare` verifies SHA-256 against the matching official SHA256SUMS and records the result locally. For a later exact rebuild, preserve the measured image and `.runtime/image-checksum.json`, or use a dated official release directory; the `release/` URL changes over time.

## Build sequence

Run the documented commands from README in order: `prepare`, `start`, `wait`, `packages`, `configure`, `dashboard`, `monitoring`.

- `prepare` creates new OS overlays, separate blank virtual data disks and NoCloud seed ISOs. Existing disks are not recreated.
- `packages` installs Ubuntu packages and formats only the new `/dev/vdb` with the expected Lab label. A disk with another label is rejected.
- `configure` creates guest accounts, receives randomly generated secrets over encrypted stdin, installs service configurations, pins backup host keys, initialises Restic and installs timers.
- `monitoring` configures a read-only NFS client mount and starts version-pinned Compose services.

Keep `.runtime/credentials.json` and `.runtime/admin.key` for access. The `.runtime` directory must never be committed or placed in a public download. On a fresh build, generate new credentials. A move of existing VMs also requires the shared backing image referenced by qcow2 overlays.

## First verification

1. Run `tools/Test-WindowsSmb.ps1`.
2. Start `naslab-backup.service`, `naslab-verify.service`, `naslab-restore-test.service` on NAS01.
3. Check Grafana and the notification inbox URLs.
4. Check `systemctl list-timers 'naslab-*'`.
5. Run acceptance only when intentional disruption of this Lab is acceptable.

## Start/stop and boot dependencies

Use `Stop-Lab.ps1` for both guests and wait for their QEMU processes to exit. Start NAS01 first, then BACKUP01 as automated by `Start-Lab.ps1`. The socket network client connects to the NAS01 backend, so restarting only NAS01 while BACKUP01 stays running may require reconnecting/restarting the second guest's virtual network; restarting both via the scripts is the supported path.

Samba, NFS, SSH, Docker, the inbox and health/job timers are enabled inside guests. Compose containers restart with Docker. NFS mounts are declared with `_netdev,nofail` and read-only soft timeout options for bounded monitoring probes, not writable production data access.

Re-running full `configure` can reset sample user/share settings. For ordinary source updates, upload source, install updated `/opt/naslab` scripts and restart the affected units instead.
