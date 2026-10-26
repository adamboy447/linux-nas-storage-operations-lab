param([string]$Drive = 'N:')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$credentials = Get-Content -LiteralPath (Join-Path $projectRoot '.runtime\credentials.json') -Raw | ConvertFrom-Json
if (Test-Path ($Drive + '\')) { throw "Drive $Drive is already in use; select another drive." }
$remotePath = '\\127.0.0.1\materials'
if (Get-SmbMapping -RemotePath $remotePath -ErrorAction SilentlyContinue) { throw 'A mapping for this share already exists.' }
$testResults = @()
foreach ($role in @('ta', 'student')) {
    $username = if ($role -eq 'ta') { 'ta01' } else { 'student01' }
    $password = if ($role -eq 'ta') { $credentials.ta_password } else { $credentials.student_password }
    $securePassword = ConvertTo-SecureString $password -AsPlainText -Force
    $credential = [System.Management.Automation.PSCredential]::new($username, $securePassword)
    try {
        New-SmbMapping -LocalPath $Drive -RemotePath $remotePath -TcpPort 1445 -Credential $credential -Persistent $false | Out-Null
        $read = [System.IO.File]::ReadAllText($Drive + '\course-guide.txt')
        $written = $false
        try {
            [System.IO.File]::WriteAllText($Drive + '\windows-permission-test.txt', 'Windows SMB permission verification')
            $written = $true
        } catch [System.UnauthorizedAccessException] {
            $written = $false
        }
        $expectedWrite = $role -eq 'ta'
        if ($written -ne $expectedWrite -or $read.Length -eq 0) { throw "Permission mismatch for $username" }
        $testResults += [pscustomobject]@{ role=$role; read=$true; write=$written; pass=$true; time=(Get-Date).ToUniversalTime().ToString('o') }
    } finally {
        Remove-SmbMapping -LocalPath $Drive -Force -ErrorAction SilentlyContinue
    }
}
$testResults | ConvertTo-Json | Tee-Object -FilePath (Join-Path $projectRoot '.runtime\windows-smb-result.json')
