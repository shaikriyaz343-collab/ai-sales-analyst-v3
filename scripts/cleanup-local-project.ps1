[CmdletBinding()]
param(
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Write-Host "AI Sales Analyst local cleanup"
Write-Host "Repo root: $RepoRoot"
Write-Host ""

# These are generated dependency/build/test artifacts and are safe to recreate.
$SafeDirectories = @(
    "node_modules",
    "frontend/node_modules",
    "frontend/.next",
    "e2e/node_modules",
    "e2e/test-results",
    "e2e/v4-playwright-report",
    "e2e/.auth",
    "test-results"
)

$existingDirs = foreach ($relative in $SafeDirectories) {
    $full = Join-Path $RepoRoot $relative
    if (Test-Path -LiteralPath $full -PathType Container) {
        Get-Item -LiteralPath $full
    }
}

$cacheDirs = Get-ChildItem -LiteralPath $RepoRoot -Directory -Force -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -in @("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache") }

$cacheFiles = Get-ChildItem -LiteralPath $RepoRoot -File -Force -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -in @(".coverage") -or $_.Extension -in @(".pyc", ".pyo") }

$targets = @($existingDirs) + @($cacheDirs) + @($cacheFiles) |
    Sort-Object FullName -Unique

if ($targets.Count -eq 0) {
    Write-Host "No cleanup targets found."
    exit 0
}

$targetFileCount = 0
$targetBytes = 0

foreach ($item in $targets) {
    if ($item.PSIsContainer) {
        $stats = Get-ChildItem -LiteralPath $item.FullName -File -Force -Recurse -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum
        $count = [int]$stats.Count
        $bytes = [int64]($stats.Sum ?? 0)
        $targetFileCount += $count
        $targetBytes += $bytes
        Write-Host ("DIR  {0}  ({1:N0} files, {2:N2} MB)" -f $item.FullName, $count, ($bytes / 1MB))
    } else {
        $targetFileCount += 1
        $targetBytes += [int64]$item.Length
        Write-Host ("FILE {0}  ({1:N0} bytes)" -f $item.FullName, $item.Length)
    }
}

Write-Host ""
Write-Host ("Potential cleanup: {0:N0} files, {1:N2} MB" -f $targetFileCount, ($targetBytes / 1MB))

if (-not $Apply) {
    Write-Host ""
    Write-Host "Preview only. Nothing was deleted."
    Write-Host "Run again with:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\cleanup-local-project.ps1 -Apply"
    exit 0
}

foreach ($item in $targets) {
    Remove-Item -LiteralPath $item.FullName -Recurse -Force
}

Write-Host ""
Write-Host ("Deleted cleanup targets: {0:N0} files, {1:N2} MB" -f $targetFileCount, ($targetBytes / 1MB))
Write-Host ""
Write-Host "Intentionally NOT removed:"
Write-Host "  - backend/runtime_*"
Write-Host "  - root/runtime_*"
Write-Host "These may contain local development state; remove them separately only when you confirm they are disposable."
