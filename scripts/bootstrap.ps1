# SuperAI bootstrap: install Python package + optional host tools (not bundled).
# Usage (from repo root):
#   powershell -File scripts/bootstrap.ps1
#   powershell -File scripts/bootstrap.ps1 -Profile agentic -LiveHostTools
#   powershell -File scripts/bootstrap.ps1 -Extras "dev,web,providers"
#
# Host CLIs (git, gh, aws, claude, …) are installed via winget/pip/npm when
# available — they are NOT shipped inside the SuperAI wheel.

param(
    [string]$Profile = "core",
    [string]$Extras = "dev",
    [switch]$LiveHostTools,
    [switch]$SkipHostTools,
    [switch]$SkipPip
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== SuperAI bootstrap ==" -ForegroundColor Cyan
Write-Host "Repo: $Root"

if (-not $SkipPip) {
    $spec = "."
    if ($Extras) {
        $spec = ".[$Extras]"
    }
    Write-Host "pip install -e $spec" -ForegroundColor Yellow
    python -m pip install -e $spec
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
}

if ($SkipHostTools) {
    Write-Host "Skipping host tools." -ForegroundColor DarkGray
    exit 0
}

# Ensure CLI is importable
$env:PYTHONPATH = Join-Path $Root "src"

Write-Host "Host tools check (profile=$Profile)..." -ForegroundColor Yellow
python -m scli host-tools check --profile $Profile
if ($LASTEXITCODE -ne 0) {
    # fallback entry
    python -c "from core.host_tools import checklist; import json; print(json.dumps(checklist(profile='$Profile')['totals']))"
}

if ($LiveHostTools) {
    Write-Host "LIVE host tools install (profile=$Profile)..." -ForegroundColor Red
    python -m scli host-tools install --profile $Profile --live
} else {
    Write-Host "Dry-run host tools install (profile=$Profile)..." -ForegroundColor Yellow
    python -m scli host-tools install --profile $Profile --dry-run
    Write-Host ""
    Write-Host "To actually install missing host tools:" -ForegroundColor Cyan
    Write-Host "  powershell -File scripts/bootstrap.ps1 -Profile $Profile -LiveHostTools"
    Write-Host "  # or: superai host-tools install --profile $Profile --live"
}

Write-Host "Done. Next: superai doctor" -ForegroundColor Green
