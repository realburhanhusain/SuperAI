# SuperAI checkpoint — durable recovery point for hardware/network faults.
# Usage (from repo root):
#   powershell -File scripts/checkpoint.ps1 -Label "F3.1-embeddings"
# Creates:
#   - docs/checkpoints/CHECKPOINT_*.md  (status snapshot)
#   - git commit if git repo and changes exist (local only; no push)

param(
    [Parameter(Mandatory = $true)]
    [string]$Label,
    [switch]$SkipTests,
    [switch]$NoGit
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$dir = Join-Path $Root "docs\checkpoints"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$path = Join-Path $dir "CHECKPOINT_${stamp}_${Label}.md"

$pytestLine = "skipped"
if (-not $SkipTests) {
    $out = & python -m pytest -q 2>&1 | Out-String
    $pytestLine = ($out -split "`n" | Where-Object { $_ -match "passed|failed|error" } | Select-Object -Last 3) -join " | "
}

$gitHead = "n/a"
$gitDirty = "n/a"
if (Test-Path (Join-Path $Root ".git")) {
    $gitHead = (& git rev-parse --short HEAD 2>$null)
    $gitDirty = (& git status -sb 2>$null | Select-Object -First 1)
}

$tbSnippet = ""
if (Test-Path (Join-Path $Root "TASKBOARD.md")) {
    $tbSnippet = Get-Content (Join-Path $Root "TASKBOARD.md") -Raw
    if ($tbSnippet.Length -gt 4000) { $tbSnippet = $tbSnippet.Substring(0, 4000) + "`n...[truncated]..." }
}

@"
# Checkpoint: $Label

- **When:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss K")
- **Host:** $env:COMPUTERNAME
- **Repo:** $Root
- **Git HEAD:** $gitHead
- **Git status:** $gitDirty
- **Pytest:** $pytestLine

## Recovery

1. Open this repo path.
2. Read ``TASKBOARD.md`` Last session + first ``[ ]`` / ``[~]`` item.
3. If tree is corrupted, restore from last git commit: ``git status`` / ``git log -5 --oneline`` / ``git stash list``.
4. Runtime data (not always in git): ``~/.superai/`` — use ``superai backup-verify`` / ``superai restore``.

## TASKBOARD snapshot (truncated)

``````markdown
$tbSnippet
``````
"@ | Set-Content -Path $path -Encoding UTF8

Write-Host "Wrote $path"

if (-not $NoGit -and (Test-Path (Join-Path $Root ".git"))) {
    & git add -A
    $msg = "checkpoint: $Label ($stamp)"
    # Allow empty commit only if nothing to commit? Prefer real commit.
    $staged = & git diff --cached --name-only
    if ($staged) {
        & git commit -m $msg
        Write-Host "Git commit: $msg"
    } else {
        Write-Host "No staged changes for git commit."
    }
}

Write-Host "CHECKPOINT_OK label=$Label file=$path"
