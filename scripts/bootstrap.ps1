# SuperAI bootstrap: install Python package + optional guided host tools / Postgres.
# Usage (from repo root):
#   powershell -File scripts/bootstrap.ps1
#   powershell -File scripts/bootstrap.ps1 -Profile agentic -LiveHostTools
#   powershell -File scripts/bootstrap.ps1 -Interactive
#   powershell -File scripts/bootstrap.ps1 -WithPostgres -LiveHostTools -Yes
#   powershell -File scripts/bootstrap.ps1 -Extras "dev,web,providers"
#
# Host CLIs and Postgres are NOT shipped inside the SuperAI wheel.
# Interactive mode prompts for profile + optional Postgres setup.

param(
    [string]$Profile = "core",
    [string]$Extras = "dev",
    [switch]$LiveHostTools,
    [switch]$SkipHostTools,
    [switch]$SkipPip,
    [switch]$Interactive,
    [switch]$WithPostgres,
    [switch]$SkipPostgres,
    [switch]$Yes
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

# Ensure CLI is importable
$env:PYTHONPATH = Join-Path $Root "src"

if ($Interactive -or $WithPostgres) {
    Write-Host "Running SuperAI install wizard..." -ForegroundColor Yellow
    $args = @("install")
    if ($Interactive) { $args += "--interactive" } else { $args += "--non-interactive" }
    if ($WithPostgres) { $args += "--with-postgres" }
    if ($SkipPostgres) { $args += "--skip-postgres" }
    if ($SkipHostTools) { $args += "--skip-host-tools" }
    else {
        $args += "--host-tools-profile"
        $args += $Profile
        $args += "--install-host-tools"
    }
    if ($LiveHostTools -or $Yes) { $args += "--live" }
    if ($Yes) { $args += "--yes" }
    python -m scli @args
    if ($LASTEXITCODE -ne 0) {
        python -c "from core.install_wizard import run_install_wizard; import json; print(json.dumps(run_install_wizard(interactive=False, with_postgres=$([int]$WithPostgres.IsPresent), host_tools_profile='$Profile', live=$([int]($LiveHostTools.IsPresent -or $Yes.IsPresent)), yes=$([int]$Yes.IsPresent), skip_postgres=$([int]$SkipPostgres.IsPresent), skip_host_tools=$([int]$SkipHostTools.IsPresent)), default=str, indent=2))"
    }
    Write-Host "Done. Next: superai doctor" -ForegroundColor Green
    exit 0
}

if ($SkipHostTools) {
    Write-Host "Skipping host tools." -ForegroundColor DarkGray
    exit 0
}

Write-Host "Host tools check (profile=$Profile)..." -ForegroundColor Yellow
python -m scli host-tools check --profile $Profile
if ($LASTEXITCODE -ne 0) {
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
    Write-Host "  # or interactive: powershell -File scripts/bootstrap.ps1 -Interactive"
    Write-Host "  # or: superai install"
    Write-Host "  # Postgres opt-in: superai install --with-postgres"
}

Write-Host "Done. Next: superai doctor  |  superai install" -ForegroundColor Green
