# Implemented v1.0 scope

The project follows the approved Linux NAS Storage Operations and Disaster Recovery Lab proposal: two guests, authenticated file services, encrypted remote backups, automatic checks/restore tests, monitoring, failure/recovery notifications, four controlled failure scenarios and static-share service DR.

The host inspection changed the hypervisor from VirtualBox to QEMU/WHPX. Windows 11 Home already provided usable WHPX acceleration; no new Windows virtual network driver or host reboot was required. Virtual network details, software versions and implementation limits are recorded in the architecture/setup/version documents.

The source tree contains the operating configurations, generated Dashboard, automation, acceptance scripts and runbooks. Runtime disks and secrets remain local and ignored by Git. Real acceptance data, including the corrected capacity monitoring issue, is preserved in the measured reports.

The original detailed proposal is a separate planning artifact. Current implementation and actual evidence take precedence over planned filenames, resource estimates or example result values.
