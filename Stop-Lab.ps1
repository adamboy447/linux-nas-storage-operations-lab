$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    py -3.12 tools/host.py stop --node backup01
    py -3.12 tools/host.py stop --node nas01
    Write-Host 'Guest shutdown requested. Wait for both QEMU processes to exit before moving VM disks.'
} finally { Pop-Location }
