$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    py -3.12 tools/host.py start --accel whpx
    if ($LASTEXITCODE -ne 0) { throw 'VM startup failed' }
    py -3.12 tools/host.py wait
    if ($LASTEXITCODE -ne 0) { throw 'VM boot timeout' }
    Write-Host 'Grafana: http://127.0.0.1:3000/d/naslab-operations'
    Write-Host 'Notification inbox: http://127.0.0.1:8088'
    Write-Host 'Credentials: .runtime\credentials.json (private; never commit)'
} finally { Pop-Location }
