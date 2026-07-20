param(
    [string]$HostAddress = '127.0.0.1',
    [int]$Port = 8010,
    [switch]$NoReload
)

$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root

if (-not (Test-Path -LiteralPath (Join-Path $Root '.env'))) {
    Write-Error "Missing .env in $Root. Copy .env.example to .env and fill required values before starting the backend."
}

$uvicornArgs = @('backend.main:app')
if (-not $NoReload) {
    $uvicornArgs += '--reload'
}
$uvicornArgs += @('--host', $HostAddress, '--port', "$Port")

Write-Host "Starting PaperHermes backend: http://${HostAddress}:$Port"
Write-Host "Config source: $Root\.env plus current process environment overrides"

& python -m uvicorn @uvicornArgs
