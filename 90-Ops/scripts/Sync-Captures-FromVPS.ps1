<#
.SYNOPSIS
    Pull Telegram-Captures from VPS to local AI-Workspace via rsync/SSH.

.DESCRIPTION
    Single-direction sync: VPS /data/inbox/Telegram-Captures/ -> local
    D:\AI-Workspace\00-Inbox\Telegram-Captures\

    Uses rsync over SSH with key-based auth. Does NOT push any data back
    to VPS (read-only pull).

    rsync resolution order:
      1. -RsyncPath parameter (explicit override)
      2. Get-Command rsync (already in PATH)
      3. Git for Windows bundled: C:\Program Files\Git\usr\bin\rsync.exe
      4. MSYS2 bundled: C:\msys64\usr\bin\rsync.exe
      5. Fail with actionable error message

    SSH resolution order (when MSYS rsync detected):
      1. -SshPath parameter (explicit override)
      2. MSYS2 ssh: C:\msys64\usr\bin\ssh.exe
      3. Git ssh: C:\Program Files\Git\usr\bin\ssh.exe
      4. Fallback to system ssh (may cause code 12 with MSYS rsync)

.PARAMETER VpsHost
    SSH host for the VPS (e.g. user@1.2.3.4 or a ~/.ssh/config alias).

.PARAMETER RemotePath
    Remote directory to sync from (default: /data/inbox/Telegram-Captures/).

.PARAMETER LocalPath
    Local directory to sync to.

.PARAMETER DryRun
    Show what would be transferred without actually copying.

.PARAMETER SshKeyPath
    Path to the SSH private key (default: ~/.ssh/hermes-rsync-key).

.PARAMETER RsyncPath
    Explicit path to rsync executable (optional).

.PARAMETER SshPath
    Explicit path to ssh executable (optional). Use MSYS2 ssh with MSYS2 rsync.

.EXAMPLE
    .\Sync-Captures-FromVPS.ps1 -VpsHost root@1.2.3.4 -DryRun
    .\Sync-Captures-FromVPS.ps1 -VpsHost root@1.2.3.4 -RsyncPath "C:\msys64\usr\bin\rsync.exe" -SshPath "C:\msys64\usr\bin\ssh.exe"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$VpsHost,

    [string]$RemotePath = '/data/inbox/Telegram-Captures/',

    [string]$LocalPath = 'D:\AI-Workspace\00-Inbox\Telegram-Captures\',

    [string]$SshKeyPath = "$HOME\.ssh\hermes-rsync-key",

    [string]$RsyncPath = '',

    [string]$SshPath = '',

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- rsync resolution ---
$IsMsysRsync = $false
$ResolvedRsync = ''

if ($RsyncPath) {
    if (-not (Test-Path $RsyncPath)) {
        Write-Error "Specified -RsyncPath not found: $RsyncPath"
        exit 1
    }
    $ResolvedRsync = $RsyncPath
    if ($RsyncPath -match 'Git\\usr\\bin|msys|mingw') {
        $IsMsysRsync = $true
    }
} elseif (Get-Command rsync -ErrorAction SilentlyContinue) {
    $ResolvedRsync = (Get-Command rsync).Source
    if ($ResolvedRsync -match 'Git\\usr\\bin|msys|mingw') {
        $IsMsysRsync = $true
    }
} elseif (Test-Path 'C:\Program Files\Git\usr\bin\rsync.exe') {
    $ResolvedRsync = 'C:\Program Files\Git\usr\bin\rsync.exe'
    $IsMsysRsync = $true
} elseif (Test-Path 'C:\msys64\usr\bin\rsync.exe') {
    $ResolvedRsync = 'C:\msys64\usr\bin\rsync.exe'
    $IsMsysRsync = $true
} else {
    Write-Error @"
rsync not found. Install one of the following:

  Option A: MSYS2 (recommended for this script)
    pacman -S rsync openssh

  Option B: Git for Windows
    https://git-scm.com/download/win

  Option C: scoop install rsync

  Option D: WSL (use 'wsl rsync ...' directly)

Or specify -RsyncPath explicitly.
"@
    exit 1
}

Write-Host "[INFO] rsync resolved: $ResolvedRsync (MSYS=$IsMsysRsync)"

# --- SSH resolution (for MSYS rsync) ---
# MSYS rsync must use a compatible SSH binary. Win32-OpenSSH
# (C:\Windows\System32\OpenSSH\ssh.exe) can cause 'connection
# unexpectedly closed' (code 12) when paired with MSYS rsync.
$ResolvedSsh = ''

if ($IsMsysRsync) {
    if ($SshPath) {
        if (-not (Test-Path $SshPath)) {
            Write-Error "Specified -SshPath not found: $SshPath"
            exit 1
        }
        $ResolvedSsh = $SshPath
    } elseif (Test-Path 'C:\msys64\usr\bin\ssh.exe') {
        $ResolvedSsh = 'C:\msys64\usr\bin\ssh.exe'
    } elseif (Test-Path 'C:\Program Files\Git\usr\bin\ssh.exe') {
        $ResolvedSsh = 'C:\Program Files\Git\usr\bin\ssh.exe'
    } else {
        # Fallback to system ssh with a warning
        $ResolvedSsh = 'ssh'
        Write-Host "[WARN] No MSYS2/Git ssh.exe found. Using system ssh."
        Write-Host "       If you get code 12, install MSYS2 OpenSSH:"
        Write-Host "         pacman -S openssh"
        Write-Host "       Or specify -SshPath explicitly."
    }
    Write-Host "[INFO] SSH resolved: $ResolvedSsh"
}

# --- Path conversion helpers ---
function ConvertTo-MsysPath {
    param([string]$WinPath)
    $resolved = [System.IO.Path]::GetFullPath($WinPath)
    if ($resolved -match '^([A-Za-z]):\\(.*)$') {
        $drive = $Matches[1].ToLower()
        $rest = $Matches[2] -replace '\\', '/'
        return "/$drive/$rest"
    }
    return $resolved -replace '\\', '/'
}

function ConvertTo-ForwardSlashPath {
    param([string]$WinPath)
    $resolved = [System.IO.Path]::GetFullPath($WinPath)
    return $resolved -replace '\\', '/'
}

# --- Convert paths for MSYS rsync ---
$RsyncLocalPath = $LocalPath
$RsyncSshKeyPath = $SshKeyPath
$RsyncSshExePath = ''

if ($IsMsysRsync) {
    $RsyncLocalPath = ConvertTo-MsysPath $LocalPath
    # SSH key: C:/Users/... format (works with MSYS2_ARG_CONV_EXCL=*)
    $RsyncSshKeyPath = ConvertTo-ForwardSlashPath $SshKeyPath
    # SSH exe: C:/msys64/... format for the -e argument
    $RsyncSshExePath = ConvertTo-ForwardSlashPath $ResolvedSsh
    Write-Host "[INFO] MSYS rsync path conversions:"
    Write-Host "       LocalPath  -> $RsyncLocalPath"
    Write-Host "       SshKeyPath -> $RsyncSshKeyPath"
    Write-Host "       SshExe     -> $RsyncSshExePath"
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
# Build the -e (remote shell) argument with the resolved SSH path + key.
if ($IsMsysRsync) {
    $sshCmd = "`"$RsyncSshExePath`" -i `"$RsyncSshKeyPath`" -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
} else {
    $sshCmd = "ssh -i `"$SshKeyPath`" -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
}

$rsyncArgs = @(
    '-avz'
    '--progress'
    '--timeout=30'
    '-e', $sshCmd
    "${VpsHost}:${RemotePath}"
    $RsyncLocalPath
)

if ($DryRun) {
    $rsyncArgs = @('--dry-run') + $rsyncArgs
    Write-Host "[DRY-RUN] Would transfer:"
}

# --- Execute ---
Write-Host "[INFO] Syncing: ${VpsHost}:${RemotePath} -> ${LocalPath}"
Write-Host "[INFO] rsync -e: $sshCmd"

# MSYS2 auto-converts arguments that look like Unix paths (starting with /).
# Setting MSYS2_ARG_CONV_EXCL="*" disables all argument conversion.
# We already pre-converted all local paths above.
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
    $env:MSYS2_ARG_CONV_EXCL = $savedMsys2ArgConvExcl
}
$elapsed = (Get-Date) - $startTime

if ($exitCode -eq 0) {
    Write-Host "[OK] Sync completed in $([math]::Round($elapsed.TotalSeconds, 1))s"
} elseif ($exitCode -eq 23) {
    Write-Host "[WARN] Partial transfer due to error (exit 23). Non-fatal for live inbox."
} elseif ($exitCode -eq 24) {
    Write-Host "[WARN] Partial transfer, vanished source files (exit 24). Normal for live inbox."
} else {
    Write-Error "rsync failed with exit code $exitCode"
    exit $exitCode
}

# --- Summary ---
$fileCount = (Get-ChildItem -Path $LocalPath -Filter '*.md' -File -ErrorAction SilentlyContinue).Count
Write-Host "[INFO] Local captures count: $fileCount files"
