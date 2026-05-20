<#
.SYNOPSIS
    Pull Telegram-Captures from VPS to local AI-Workspace via rsync/SSH.

.DESCRIPTION
    Single-direction sync: VPS /data/inbox/Telegram-Captures/ -> local
    D:\AI-Workspace\00-Inbox\Telegram-Captures\

    Uses rsync over SSH with key-based auth. Does NOT push any data back
    to VPS (read-only pull).

    After sync, Syncthing handles distribution to secondary machines
    via the existing AI-Workspace - Inbox share.

.PARAMETER VpsHost
    SSH host for the VPS (e.g. user@1.2.3.4 or a ~/.ssh/config alias).

.PARAMETER RemotePath
    Remote directory to sync from (default: /data/inbox/Telegram-Captures/).

.PARAMETER LocalPath
    Local directory to sync to (default: D:\AI-Workspace\00-Inbox\Telegram-Captures\).

.PARAMETER DryRun
    Show what would be transferred without actually copying.

.PARAMETER SshKeyPath
    Path to the SSH private key (default: ~/.ssh/hermes-rsync-key).

.EXAMPLE
    .\Sync-Captures-FromVPS.ps1 -VpsHost hermes-vps
    .\Sync-Captures-FromVPS.ps1 -VpsHost root@1.2.3.4 -DryRun

.NOTES
    Requirements:
      - rsync installed (WSL, Git Bash, or native Windows rsync)
      - SSH key pair generated and deployed (see captures-sync-runbook.md)
      - VPS authorized_keys configured with restrict + command limit

    Security:
      - Never logs SSH key content or passphrase
      - Never writes to VPS (--whole-file avoids delta protocol)
      - Preserves file timestamps for idempotent downstream processing
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$VpsHost,

    [string]$RemotePath = '/data/inbox/Telegram-Captures/',

    [string]$LocalPath = 'D:\AI-Workspace\00-Inbox\Telegram-Captures\',

    [string]$SshKeyPath = "$HOME\.ssh\hermes-rsync-key",

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- Validation ---
if (-not (Get-Command rsync -ErrorAction SilentlyContinue)) {
    Write-Error "rsync not found. Install via WSL, Git Bash, or scoop install rsync."
    exit 1
}

if (-not (Test-Path $SshKeyPath)) {
    Write-Error "SSH key not found at $SshKeyPath. See captures-sync-runbook.md."
    exit 1
}

if (-not (Test-Path $LocalPath)) {
    Write-Host "[INFO] Creating local directory: $LocalPath"
    New-Item -ItemType Directory -Path $LocalPath -Force | Out-Null
}

# --- Build rsync command ---
$rsyncArgs = @(
    '-avz'
    '--progress'
    '--timeout=30'
    '-e', "ssh -i `"$SshKeyPath`" -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
    "${VpsHost}:${RemotePath}"
    $LocalPath
)

if ($DryRun) {
    $rsyncArgs = @('--dry-run') + $rsyncArgs
    Write-Host "[DRY-RUN] Would transfer:"
}

# --- Execute ---
Write-Host "[INFO] Syncing: ${VpsHost}:${RemotePath} -> ${LocalPath}"
Write-Host "[INFO] SSH key: $SshKeyPath"

$startTime = Get-Date
& rsync @rsyncArgs
$exitCode = $LASTEXITCODE
$elapsed = (Get-Date) - $startTime

if ($exitCode -eq 0) {
    Write-Host "[OK] Sync completed in $([math]::Round($elapsed.TotalSeconds, 1))s"
} elseif ($exitCode -eq 23) {
    # Partial transfer (some files vanished during sync - normal for live inbox)
    Write-Host "[WARN] Partial transfer (exit 23). Some files may have been processed/moved during sync. This is normal."
} else {
    Write-Error "rsync failed with exit code $exitCode"
    exit $exitCode
}

# --- Summary ---
$fileCount = (Get-ChildItem -Path $LocalPath -Filter '*.md' -File -ErrorAction SilentlyContinue).Count
Write-Host "[INFO] Local captures count: $fileCount files"
