# One-off helper, launched only for the user's explicit shutdown request.
param([int]$DelaySeconds = 60)

$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
$manifestPath = Join-Path $projectDirectory '.models\bge-small-zh-v1.5\local_manifest.json'
$cancelPath = Join-Path $projectDirectory 'reports\cancel-embedding-shutdown.flag'
$statusPath = Join-Path $projectDirectory 'reports\embedding-shutdown-status.json'

if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw 'Local inference verification has not completed; shutdown cancelled.'
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($manifest.weights_sha256 -ne '354763b9b1357bc9c44f62c6be2276321081ed2567773608c0d0785b61d5a026' -or $manifest.dimension -ne 512) {
    throw 'Model verification does not match the expected file; shutdown cancelled.'
}

function Write-ShutdownStatus([string]$State) {
    @{
        state = $State
        helper_pid = $PID
        delay_seconds = $DelaySeconds
        time_utc = [DateTimeOffset]::UtcNow.ToString('o')
        forced_app_close = $false
    } | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
}

Write-ShutdownStatus 'waiting'
Start-Sleep -Seconds $DelaySeconds
if (Test-Path -LiteralPath $cancelPath) {
    Write-ShutdownStatus 'cancelled'
    exit 0
}

Write-ShutdownStatus 'requesting_shutdown'
# /t > 0 implies /f on Windows. Delay above instead, then request a non-forced shutdown.
& (Join-Path $env:SystemRoot 'System32\shutdown.exe') /s /t 0 /c 'Embedding model verified; shutdown explicitly requested by user.'
if ($LASTEXITCODE -ne 0) {
    Write-ShutdownStatus 'shutdown_request_failed'
    exit $LASTEXITCODE
}
Write-ShutdownStatus 'shutdown_requested'
