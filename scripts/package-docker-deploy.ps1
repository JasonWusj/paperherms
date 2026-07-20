param(
    [string]$OutputPath = "dist/paperhermes-docker-deploy.zip"
)

$ErrorActionPreference = 'Stop'

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Stage = Join-Path $env:TEMP ("paperhermes-docker-deploy-" + [guid]::NewGuid().ToString('N'))
$ResolvedOutput = Join-Path $Root $OutputPath

New-Item -ItemType Directory -Path $Stage | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $ResolvedOutput) -Force | Out-Null

$directories = @(
    'backend',
    'agent_core',
    'rag',
    'tools',
    'evaluator',
    'frontend/app',
    'frontend/components',
    'frontend/lib',
    'scripts'
)

$files = @(
    'pyproject.toml',
    'docker-compose.yml',
    'Dockerfile.backend',
    '.dockerignore',
    'frontend/Dockerfile',
    'frontend/package.json',
    'frontend/package-lock.json',
    'frontend/next.config.mjs',
    'frontend/postcss.config.js',
    'frontend/tailwind.config.ts',
    'frontend/tsconfig.json',
    'frontend/next-env.d.ts'
)

foreach ($directory in $directories) {
    $source = Join-Path $Root $directory
    if (Test-Path -LiteralPath $source) {
        $target = Join-Path $Stage $directory
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $target -Recurse
    }
}

foreach ($file in $files) {
    $source = Join-Path $Root $file
    if (Test-Path -LiteralPath $source) {
        $target = Join-Path $Stage $file
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $target
    }
}

$excludedItems = @(
    '__pycache__',
    '.pytest_cache',
    '.ruff_cache',
    '.next',
    'node_modules'
)

foreach ($item in $excludedItems) {
    Get-ChildItem -LiteralPath $Stage -Directory -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq $item } |
        Remove-Item -Recurse -Force
}

Get-ChildItem -LiteralPath $Stage -File -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in @('.pyc', '.pyo') } |
    Remove-Item -Force

if (Test-Path -LiteralPath $ResolvedOutput) {
    Remove-Item -LiteralPath $ResolvedOutput -Force
}

Compress-Archive -Path (Join-Path $Stage '*') -DestinationPath $ResolvedOutput
Remove-Item -LiteralPath $Stage -Recurse -Force

Write-Host "Created deploy package: $ResolvedOutput"
