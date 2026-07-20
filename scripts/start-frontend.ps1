param(
    [string]$BackendHost = '127.0.0.1',
    [int]$BackendPort = 8010,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Frontend = Join-Path $Root 'frontend'
$NodeModules = Join-Path $Frontend 'node_modules'

if (-not (Test-Path -LiteralPath $Frontend)) {
    Write-Error "Missing frontend directory: $Frontend"
}

if (-not (Test-Path -LiteralPath $NodeModules)) {
    Write-Error "Missing frontend dependencies. Run 'npm install' inside $Frontend first."
}

$env:NEXT_PUBLIC_API_BASE_URL = "http://${BackendHost}:${BackendPort}/api"
$env:PORT = "$FrontendPort"

Set-Location $Frontend

Write-Host "Starting PaperHermes frontend: http://localhost:$FrontendPort"
Write-Host "API base URL: $env:NEXT_PUBLIC_API_BASE_URL"

& npm run dev
