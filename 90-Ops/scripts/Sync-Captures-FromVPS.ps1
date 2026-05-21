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

    rsync resolution order:
      1. -RsyncPath parameter (explicit override)
      2. Get-Command rsync (already in PATH)
      3. Git for Windows bundled rsync (C:\Program Files\Git\usr\bin\rsync.exe)
      4. Fail with actionable error message

    Path format:
      Git/MSYS rsync requires MSYS-style paths (/d/... instead of D:\...).
      This script auto-converts Windows paths to MSYS format when using
      Git/MSYS rsync.

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

.PARAMETER RsyncPath
    Explicit path to rsync executable (optional). Overrides auto-detection.

.EXAMPLE
    .\Sync-Captures-FromVPS.ps1 -VpsHost hermes-vps
    .\Sync-Captures-FromVPS.ps1 -VpsHost root@1.2.3.4 -DryRun
    .\Sync-Captures-FromVPS.ps1 -VpsHost root@1.2.3.4 -RsyncPath "C:\tools\rsync.exe"

.NOTES
    Requirements:
      - rsync available (Git for Windows, WSL, scoop, or cwrsync)
      - SSH key pair generated and deployed (see captures-sync-runbook.md)
      - VPS authorized_keys configured with restrict + command limit

    Security:
      - Never logs SSH key content or passphrase
      - Never writes to VPS (read-only pull)
      - Preserves file timestamps for idempotent downstream processing
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$VpsHost,

    [string]$RemotePath = '/data/inbox/Telegram-Captures/',

    [string]$LocalPath = 'D:\AI-Workspace\00-Inbox\Telegram-Captures\',

    [string]$SshKeyPath = "$HOME\.ssh\hermes-rsync-key",

    [string]$RsyncPath = '',

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- rsync resolution ---
# Determines the path to the rsync executable and whether it is MSYS-based
# (which requires path format conversion).

$IsMsysRsync = $false
$ResolvedRsync = ''

if ($RsyncPath) {
    # 1. Explicit parameter
    if (-not (Test-Path $RsyncPath)) {
        Write-Error "Specified -RsyncPath not found: $RsyncPath"
        exit 1
    }
    $ResolvedRsync = $RsyncPath
    # Detect if this is an MSYS/Git rsync by checking the path
    if ($RsyncPath -match 'Git\\usr\\bin|msys|mingw') {
        $IsMsysRsync = $true
    }
} elseif (Get-Command rsync -ErrorAction SilentlyContinue) {
    # 2. Already in PATH
    $ResolvedRsync = (Get-Command rsync).Source
    if ($ResolvedRsync -match 'Git\\usr\\bin|msys|mingw') {
        $IsMsysRsync = $true
    }
} elseif (Test-Path 'C:\Program Files\Git\usr\bin\rsync.exe') {
    # 3. Git for Windows bundled rsync
    $ResolvedRsync = 'C:\Program Files\Git\usr\bin\rsync.exe'
    $IsMsysRsync = $true
    Write-Host "[INFO] Using Git for Windows bundled rsync: $ResolvedRsync"
} else {
    # 4. Not found anywhere
    Write-Error @"
rsync not found. Install one of the following:

  Option A (recommended): Git for Windows (includes rsync at C:\Program Files\Git\usr\bin\rsync.exe)
    https://git-scm.com/download/win

  Option B: scoop install rsync
    Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
    Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
    scoop install rsync

  Option C: WSL (use 'wsl rsync ...' directly)

  Option D: cwrsync (https://itefix.net/cwrsync)

Or specify -RsyncPath explicitly:
    .\Sync-Captures-FromVPS.ps1 -VpsHost <host> -RsyncPath "C:\path\to\rsync.exe"
"@
    exit 1
}

# --- Path conversion for MSYS rsync ---
# MSYS/Git rsync does not understand Windows paths like D:\foo\bar.
# Convert to /d/foo/bar format for rsync's own arguments (local dest).
#
# IMPORTANT: The SSH -i key path must NOT use /c/Users/... format because
# when MSYS2_ARG_CONV_EXCL=* is set, MSYS2 will not convert it back to a
# Windows path that ssh.exe can open. Instead we use C:/Users/... format
# (Windows path with forward slashes) which both MSYS ssh and native ssh
# understand regardless of MSYS2_ARG_CONV_EXCL setting.

function ConvertTo-MsysPath {
    param([string]$WinPath)
    # Resolve to absolute path first
    $resolved = [System.IO.Path]::GetFullPath($WinPath)
    # D:\foo\bar -> /d/foo/bar
    if ($resolved -match '^([A-Za-z]):\\(.*)$') {
        $drive = $Matches[1].ToLower()
        $rest = $Matches[2] -replace '\\', '/'
        return "/$drive/$rest"
    }
    # Already unix-style or UNC, return as-is
    return $resolved -replace '\\', '/'
}

function ConvertTo-ForwardSlashPath {
    param([string]$WinPath)
    # Resolve to absolute then just replace backslashes with forward slashes.
    # Result: C:/Users/Administrator/.ssh/hermes-rsync-key
    # This format is understood by both MSYS ssh and native Windows ssh.
    $resolved = [System.IO.Path]::GetFullPath($WinPath)
    return $resolved -replace '\\', '/'
}

$RsyncLocalPath = $LocalPath
$RsyncSshKeyPath = $SshKeyPath

if ($IsMsysRsync) {
    # Local destination path: use MSYS format (/d/...) for rsync
    $RsyncLocalPath = ConvertTo-MsysPath $LocalPath
    # SSH key path: use Windows-with-forward-slashes (C:/...) for ssh -i
    # This works with MSYS2_ARG_CONV_EXCL=* because ssh sees a real Windows path.
    $RsyncSshKeyPath = ConvertTo-ForwardSlashPath $SshKeyPath
    Write-Host "[INFO] MSYS rsync detected; converted paths:"
    Write-Host "       LocalPath -> $RsyncLocalPath"
    Write-Host "       SshKeyPath -> $RsyncSshKeyPath"
}

# --- Validation ---
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
    '-e', "ssh -i `"$RsyncSshKeyPath`" -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
    "${VpsHost}:${RemotePath}"
    $RsyncLocalPath
)

if ($DryRun) {
    $rsyncArgs = @('--dry-run') + $rsyncArgs
    Write-Host "[DRY-RUN] Would transfer:"
}

# --- Execute ---
Write-Host "[INFO] Syncing: ${VpsHost}:${RemotePath} -> ${LocalPath}"
Write-Host "[INFO] rsync: $ResolvedRsync"
Write-Host "[INFO] SSH key: $SshKeyPath"

# MSYS2 auto-converts arguments that look like Unix paths (starting with /).
# This mangles the remote path (e.g. /data/inbox/... becomes C:/msys64/data/...).
# Setting MSYS2_ARG_CONV_EXCL="*" disables all argument conversion for the
# rsync call. We already pre-converted LocalPath and SshKeyPath to MSYS format
# above, so blanket exclusion is safe and prevents remote path corruption.
$savedMsys2ArgConvExcl = $env:MSYS2_ARG_CONV_EXCL

$startTime = Get-Date
try {
    if ($IsMsysRsync) {
        $env:MSYS2_ARG_CONV_EXCL = '*'
        Write-Host "[INFO] Set MSYS2_ARG_CONV_EXCL=* for rsync invocation"
    }
    & $ResolvedRsync @rsyncArgs
    $exitCode = $LASTEXITCODE
} finally {
    # Restore previous value (may be $null if was not set).
    $env:MSYS2_ARG_CONV_EXCL = $savedMsys2ArgConvExcl
}
$elapsed = (Get-Date) - $startTime

if ($exitCode -eq 0) {
    Write-Host "[OK] Sync completed in $([math]::Round($elapsed.TotalSeconds, 1))s"
} elseif ($exitCode -eq 23) {
    # Exit 23: Partial transfer due to error (some files could not be transferred)
    Write-Host "[WARN] Partial transfer due to error (exit 23). Some files could not be transferred. This is usually non-fatal for a live inbox."
} elseif ($exitCode -eq 24) {
    # Exit 24: Partial transfer due to vanished source files (normal for live inbox
    # where bridge-ingress may be writing new .tmp files that disappear before rsync finishes)
    Write-Host "[WARN] Partial transfer due to vanished source files (exit 24). Files were created/removed during sync. This is normal."
} else {
    Write-Error "rsync failed with exit code $exitCode"
    exit $exitCode
}

# --- Summary ---
$fileCount = (Get-ChildItem -Path $LocalPath -Filter '*.md' -File -ErrorAction SilentlyContinue).Count
Write-Host "[INFO] Local captures count: $fileCount files"
