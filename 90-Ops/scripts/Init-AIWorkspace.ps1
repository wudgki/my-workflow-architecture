#Requires -Version 5.1
<#
.SYNOPSIS
    Initialize AI-Workspace blueprint on primary or secondary machine (D:\AI-Workspace).

.DESCRIPTION
    Idempotent script that:
    - Creates the full directory structure defined in the blueprint
    - Copies documentation files (_about.md / README.md / SOPs) from -Source
    - Generates .machine-id (marks machine role)
    - Creates secrets/ subdirectory placeholders
    - Installs Wiki templates (10-Hermes-Wiki/99-Templates/)
    - Installs Claude Code agents (20-Claude-Code/agents/)
    - Installs Intelligence pipeline configs (50-Intelligence/pipelines/)
    - Installs Syncthing .stignore files (from 90-Ops/sync/stignore/ templates)
    - All asset installs use copy-if-missing; use -Force to overwrite
    Safe to run repeatedly; each run only fills in missing items.

    Tested on: Windows PowerShell 5.1 and PowerShell 7.x

.PARAMETER Source
    Path to the cloned blueprint repository on local disk.
    Example: C:\Code\my-workflow-architecture

.PARAMETER Target
    AI-Workspace landing directory. Default: D:\AI-Workspace

.PARAMETER Role
    Machine role: primary | secondary. Determines .machine-id content and write permissions.

.PARAMETER Hostname
    Machine identifier (written to .machine-id). Default: $env:COMPUTERNAME

.PARAMETER Force
    Overwrite existing docs (_about.md / README.md / SOPs) and Wiki templates (99-Templates/).
    Does NOT overwrite business data (notes, code, runtime artifacts).

.PARAMETER DryRun
    Print planned operations without modifying the filesystem.

.EXAMPLE
    # Primary machine first-time setup
    .\Init-AIWorkspace.ps1 -Source C:\Code\my-workflow-architecture -Target D:\AI-Workspace -Role primary

.EXAMPLE
    # Secondary machine setup
    .\Init-AIWorkspace.ps1 -Source C:\Code\my-workflow-architecture -Role secondary

.EXAMPLE
    # After blueprint repo update, sync docs (overwrite) but keep business data
    .\Init-AIWorkspace.ps1 -Source C:\Code\my-workflow-architecture -Force

.EXAMPLE
    # Dry run (no filesystem changes)
    .\Init-AIWorkspace.ps1 -Source C:\Code\my-workflow-architecture -Role primary -DryRun

.NOTES
    Author: Samuel Wu workflow blueprint
    Requires: PowerShell 5.1+ or PowerShell 7
    Platform: Windows 10/11
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Source,

    [Parameter(Mandatory = $false)]
    [string]$Target = 'D:\AI-Workspace',

    [Parameter(Mandatory = $false)]
    [ValidateSet('primary', 'secondary')]
    [string]$Role,

    [Parameter(Mandatory = $false)]
    [string]$Hostname = $env:COMPUTERNAME,

    [Parameter(Mandatory = $false)]
    [switch]$Force,

    [Parameter(Mandatory = $false)]
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ============================================================
# 1) Blueprint definition: directory list + document manifest
# ============================================================

# Top-level + subdirectories (mirrors README.md / _about.md structure)
$Directories = @(
    '00-Inbox',
    '00-Inbox/Discord-Captures',
    '00-Inbox/Telegram-Captures',
    '00-Inbox/Feishu-Captures',
    '00-Inbox/Web-Clips',
    '00-Inbox/Repo-Captures',
    '00-Inbox/To-Process',
    '00-Inbox/Wiki-Drafts',

    '10-Hermes-Wiki',
    '10-Hermes-Wiki/00-Map-of-Content',
    '10-Hermes-Wiki/10-Phase1-Infra-Intel',
    '10-Hermes-Wiki/20-Phase2-B2B-Platform',
    '10-Hermes-Wiki/20-Phase2-B2B-Platform/Jinguan-Brand',
    '10-Hermes-Wiki/20-Phase2-B2B-Platform/Product-Catalog',
    '10-Hermes-Wiki/20-Phase2-B2B-Platform/Marketing-Playbook',
    '10-Hermes-Wiki/20-Phase2-B2B-Platform/Tech-Architecture',
    '10-Hermes-Wiki/20-Phase2-B2B-Platform/Integration-Plan',
    '10-Hermes-Wiki/20-Phase2-B2B-Platform/Competitor-Research',
    '10-Hermes-Wiki/30-Phase3-Crypto-Quant',
    '10-Hermes-Wiki/30-Phase3-Crypto-Quant/Strategy-Notes',
    '10-Hermes-Wiki/30-Phase3-Crypto-Quant/KOL-Tracking',
    '10-Hermes-Wiki/30-Phase3-Crypto-Quant/Onchain-Intel',
    '10-Hermes-Wiki/30-Phase3-Crypto-Quant/Macro-Notes',
    '10-Hermes-Wiki/30-Phase3-Crypto-Quant/AStock-USStock',
    '10-Hermes-Wiki/30-Phase3-Crypto-Quant/Risk-Management',
    '10-Hermes-Wiki/40-Phase4-Prediction-Market',
    '10-Hermes-Wiki/50-Repo-Research',
    '10-Hermes-Wiki/60-AI-Toolbox',
    '10-Hermes-Wiki/70-Personal-OS',
    '10-Hermes-Wiki/90-Archive',
    '10-Hermes-Wiki/99-Templates',
    '10-Hermes-Wiki/_attachments',
    '10-Hermes-Wiki/.obsidian',

    '20-Claude-Code',
    '20-Claude-Code/agents',
    '20-Claude-Code/commands',
    '20-Claude-Code/skills',
    '20-Claude-Code/mcp-servers',
    '20-Claude-Code/prompts',
    '20-Claude-Code/memory',
    '20-Claude-Code/logs',

    '30-Phases',
    '30-Phases/phase1-infra-intel',
    '30-Phases/phase2-b2b-platform',
    '30-Phases/phase2-b2b-platform/overseas-platform',
    '30-Phases/phase2-b2b-platform/jinguan-site',
    '30-Phases/phase2-b2b-platform/integration',
    '30-Phases/phase3-crypto-quant',
    '30-Phases/phase3-crypto-quant/perp-contracts',
    '30-Phases/phase3-crypto-quant/meme-trading',
    '30-Phases/phase3-crypto-quant/astock-ustock',
    '30-Phases/phase3-crypto-quant/shared-lib',
    '30-Phases/phase4-prediction-market',

    '40-Hermes-VPS',
    '40-Hermes-VPS/deploy',
    '40-Hermes-VPS/services',
    '40-Hermes-VPS/env',
    '40-Hermes-VPS/monitoring',
    '40-Hermes-VPS/runbook',

    '50-Intelligence',
    '50-Intelligence/github-watch',
    '50-Intelligence/crypto-watch',
    '50-Intelligence/stock-watch',
    '50-Intelligence/macro-watch',
    '50-Intelligence/prediction-watch',
    '50-Intelligence/community-bridges',
    '50-Intelligence/pipelines',

    '60-Repo-Research',
    '60-Repo-Research/reports',
    '60-Repo-Research/comparisons',
    '60-Repo-Research/adopt-list',
    '60-Repo-Research/reject-list',

    '70-Sandbox',

    '90-Ops',
    '90-Ops/sync',
    '90-Ops/secrets',
    '90-Ops/secrets/shared',
    '90-Ops/secrets/phase2',
    '90-Ops/secrets/phase3',
    '90-Ops/secrets/phase4',
    '90-Ops/secrets/hermes',
    '90-Ops/secrets/intel',
    '90-Ops/backup',
    '90-Ops/backup/wiki',
    '90-Ops/backup/reports',
    '90-Ops/scripts'
)

# Documents to copy from Source to Target (paths relative to repo root)
$DocFiles = @(
    'README.md',
    '.gitignore',
    '00-Inbox/_about.md',
    '00-Inbox/Inbox-Processing-Rules.md',
    '10-Hermes-Wiki/_about.md',
    '20-Claude-Code/_about.md',
    '30-Phases/_about.md',
    '30-Phases/phase2-b2b-platform/_about.md',
    '30-Phases/phase3-crypto-quant/_about.md',
    '40-Hermes-VPS/_about.md',
    '40-Hermes-VPS/runbook/migration-vps-to-local.md',
    '50-Intelligence/_about.md',
    '60-Repo-Research/_about.md',
    '70-Sandbox/_about.md',
    '90-Ops/_about.md',
    '90-Ops/multi-machine-protocol.md',
    '90-Ops/secrets/README.md',
    '90-Ops/scripts/Init-AIWorkspace.ps1'
)

# Syncthing share roots -> target subdirectory mapping
$SyncShares = @{
    'wiki'           = '10-Hermes-Wiki'
    'claude-code'    = '20-Claude-Code'
    'phases'         = '30-Phases'
    'inbox'          = '00-Inbox'
    'repo-research'  = '60-Repo-Research'
}

# ============================================================
# 2) Utility functions
# ============================================================

function Write-Step {
    param([string]$Message, [string]$Level = 'INFO')
    $color = switch ($Level) {
        'INFO'  { 'Cyan' }
        'OK'    { 'Green' }
        'WARN'  { 'Yellow' }
        'ERROR' { 'Red' }
        'SKIP'  { 'DarkGray' }
        default { 'White' }
    }
    $tag = if ($DryRun) { '[DRY-RUN] ' } else { '' }
    Write-Host "$tag[$Level] $Message" -ForegroundColor $color
}

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p  = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Ensure-Dir {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path -PathType Container) {
        Write-Step "Dir exists: $Path" 'SKIP'
        return
    }
    if ($DryRun) {
        Write-Step "Would create dir: $Path" 'INFO'
        return
    }
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
    Write-Step "Created dir: $Path" 'OK'
}

function Copy-Doc {
    param(
        [string]$SrcRoot,
        [string]$DstRoot,
        [string]$Relative
    )
    $src = Join-Path $SrcRoot $Relative
    $dst = Join-Path $DstRoot $Relative

    if (-not (Test-Path -LiteralPath $src)) {
        Write-Step "Source missing, skip: $Relative" 'WARN'
        return
    }

    $dstDir = Split-Path $dst -Parent
    if (-not (Test-Path -LiteralPath $dstDir)) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
        }
    }

    if (Test-Path -LiteralPath $dst) {
        if (-not $Force) {
            Write-Step "Doc exists (use -Force to overwrite): $Relative" 'SKIP'
            return
        }
        Write-Step "Overwriting doc: $Relative" 'WARN'
    } else {
        Write-Step "Copy doc: $Relative" 'OK'
    }

    if (-not $DryRun) {
        Copy-Item -LiteralPath $src -Destination $dst -Force
    }
}

function Write-FileIfMissing {
    param(
        [string]$Path,
        [string]$Content,
        [string]$Description
    )
    if (Test-Path -LiteralPath $Path) {
        if (-not $Force) {
            Write-Step "$Description exists: $Path" 'SKIP'
            return
        }
        Write-Step "Overwriting $Description : $Path" 'WARN'
    } else {
        Write-Step "Writing $Description : $Path" 'OK'
    }
    if ($DryRun) { return }
    $dir = Split-Path $Path -Parent
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    Set-Content -LiteralPath $Path -Value $Content -Encoding UTF8
}

function Install-StIgnore {
    param(
        [string]$SrcRoot,
        [string]$DstRoot,
        [hashtable]$Shares
    )
    $tplDir = Join-Path $SrcRoot '90-Ops/sync/stignore'
    if (-not (Test-Path -LiteralPath $tplDir)) {
        Write-Step ".stignore template dir missing, skip Syncthing step: $tplDir" 'WARN'
        return
    }
    foreach ($scope in $Shares.Keys) {
        $tpl = Join-Path $tplDir "$scope.stignore"
        if (-not (Test-Path -LiteralPath $tpl)) {
            Write-Step "No template, skip .stignore for '$scope'" 'SKIP'
            continue
        }
        $shareRoot = Join-Path $DstRoot $Shares[$scope]
        $dst = Join-Path $shareRoot '.stignore'
        if (-not (Test-Path -LiteralPath $shareRoot)) {
            if (-not $DryRun) { New-Item -ItemType Directory -Path $shareRoot -Force | Out-Null }
        }
        if ((Test-Path -LiteralPath $dst) -and (-not $Force)) {
            Write-Step ".stignore exists (use -Force to overwrite): $($Shares[$scope])" 'SKIP'
            continue
        }
        if (-not $DryRun) { Copy-Item -LiteralPath $tpl -Destination $dst -Force }
        Write-Step "Installed .stignore: $($Shares[$scope])" 'OK'
    }
}

function Install-Assets {
    <#
    .SYNOPSIS
        Install blueprint assets from a source subdirectory to target workspace.

    .DESCRIPTION
        Generic copy-if-missing installer for any blueprint directory.
        - Recursively scans the source subdirectory
        - Default: copy-if-missing. If target file exists, outputs SKIP
        - Only overwrites when -Force is explicitly set
        - DryRun mode: lists every file that would be copied or skipped
        - Excludes .gitkeep files
    #>
    param(
        [string]$SrcRoot,
        [string]$DstRoot,
        [string]$RelativeRoot,
        [string]$Label
    )

    $relativeRoot = $RelativeRoot
    $srcDir = Join-Path $SrcRoot $relativeRoot
    $dstDir = Join-Path $DstRoot $relativeRoot

    if (-not (Test-Path -LiteralPath $srcDir -PathType Container)) {
        Write-Step "$Label source dir missing, skip: $srcDir" 'WARN'
        return
    }

    # Ensure target directory exists
    if (-not (Test-Path -LiteralPath $dstDir -PathType Container)) {
        if ($DryRun) {
            Write-Step "Would create dir: $relativeRoot" 'INFO'
        } else {
            New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
            Write-Step "Created dir: $relativeRoot" 'OK'
        }
    }

    # List all template files recursively (exclude .gitkeep)
    $files = Get-ChildItem -LiteralPath $srcDir -Recurse -File `
                | Where-Object { $_.Name -ne '.gitkeep' }

    if (-not $files -or $files.Count -eq 0) {
        Write-Step "$Label dir is empty, nothing to install" 'WARN'
        return
    }

    $countCopy = 0
    $countSkip = 0
    $countOverwrite = 0

    foreach ($f in $files) {
        # Compute relative path (handles subdirectories)
        $relativeFile = $f.FullName.Substring($srcDir.Length).TrimStart('\', '/')
        $dst = Join-Path $dstDir $relativeFile
        $displayPath = "$relativeRoot/$($relativeFile -replace '\\', '/')"

        # Ensure parent directory
        $dstParent = Split-Path $dst -Parent
        if (-not (Test-Path -LiteralPath $dstParent)) {
            if (-not $DryRun) {
                New-Item -ItemType Directory -Path $dstParent -Force | Out-Null
            }
        }

        if (Test-Path -LiteralPath $dst) {
            if ($Force) {
                Write-Step "Overwrite: $displayPath" 'WARN'
                if (-not $DryRun) {
                    Copy-Item -LiteralPath $f.FullName -Destination $dst -Force
                }
                $countOverwrite++
            } else {
                # copy-if-missing: skip existing
                Write-Step "Exists (use -Force to overwrite): $displayPath" 'SKIP'
                $countSkip++
            }
        } else {
            Write-Step "Copy: $displayPath" 'OK'
            if (-not $DryRun) {
                Copy-Item -LiteralPath $f.FullName -Destination $dst -Force
            }
            $countCopy++
        }
    }

    # Summary
    Write-Step "$Label summary: copied=$countCopy / overwritten=$countOverwrite / skipped=$countSkip (total=$($files.Count))" 'INFO'
}

# ============================================================
# 3) Pre-flight checks
# ============================================================

Write-Host ''
Write-Host '=================================================' -ForegroundColor Magenta
Write-Host '  AI-Workspace Blueprint Initializer' -ForegroundColor Magenta
Write-Host '=================================================' -ForegroundColor Magenta
Write-Host ''

Write-Step "Source:   $Source"
Write-Step "Target:   $Target"
Write-Step "Role:     $(if ($Role) { $Role } else { '<not specified, skip .machine-id>' })"
Write-Step "Hostname: $Hostname"
Write-Step "Force:    $Force"
Write-Step "DryRun:   $DryRun"
Write-Host ''

# Validate Source
if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "Blueprint source directory does not exist: $Source"
}
$readme = Join-Path $Source 'README.md'
$signature = Join-Path $Source '90-Ops/multi-machine-protocol.md'
if (-not (Test-Path -LiteralPath $readme) -or -not (Test-Path -LiteralPath $signature)) {
    throw "Source does not look like a valid blueprint repo (missing README.md or 90-Ops/multi-machine-protocol.md): $Source"
}

# Validate Target parent exists
$parent = Split-Path $Target -Parent
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    throw "Target parent directory does not exist: $parent"
}

if (-not (Test-IsAdmin)) {
    Write-Step 'Running without admin privileges (usually fine for D:\AI-Workspace)' 'INFO'
}

# ============================================================
# 4) Create Target root
# ============================================================

Ensure-Dir -Path $Target

# ============================================================
# 5) Create all directories
# ============================================================

Write-Host ''
Write-Step 'Phase 1/8: Creating directory skeleton' 'INFO'
foreach ($d in $Directories) {
    Ensure-Dir -Path (Join-Path $Target $d)
}

# ============================================================
# 6) Copy documents
# ============================================================

Write-Host ''
Write-Step 'Phase 2/8: Copying documents (_about / SOP / README)' 'INFO'
foreach ($f in $DocFiles) {
    Copy-Doc -SrcRoot $Source -DstRoot $Target -Relative $f
}

# ============================================================
# 7) Generate .machine-id (if Role specified)
# ============================================================

Write-Host ''
Write-Step 'Phase 3/8: Generating machine identity and config' 'INFO'

if ($Role) {
    $machineIdPath = Join-Path $Target '.machine-id'
    $now = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')
    $machineIdContent = @"
# AI-Workspace machine identity (not tracked by git, see .gitignore)
hostname: $Hostname
role: $Role
initialized_at: $now
last_handover: null
notes: |
  Generated by 90-Ops/scripts/Init-AIWorkspace.ps1
  Scripts should check the role field before writing to restricted directories.
"@
    Write-FileIfMissing -Path $machineIdPath -Content $machineIdContent -Description '.machine-id'
}
else {
    Write-Step 'No -Role specified, skipping .machine-id generation' 'SKIP'
}

# Ensure secrets/README.md was copied (sanity check)
$secretsReadme = Join-Path $Target '90-Ops/secrets/README.md'
if (-not (Test-Path -LiteralPath $secretsReadme)) {
    Write-Step '90-Ops/secrets/README.md should have been copied via DocFiles, please verify' 'INFO'
}

# Create secrets subdirectory placeholders
foreach ($scope in @('shared', 'phase2', 'phase3', 'phase4', 'hermes', 'intel')) {
    $keep = Join-Path $Target "90-Ops/secrets/$scope/.gitkeep"
    if (-not (Test-Path -LiteralPath $keep)) {
        if (-not $DryRun) { New-Item -ItemType File -Path $keep -Force | Out-Null }
        Write-Step "Placeholder: 90-Ops/secrets/$scope/.gitkeep" 'OK'
    }
}

# ============================================================
# 8) Install Wiki templates (10-Hermes-Wiki/99-Templates/)
# ============================================================

Write-Host ''
Write-Step 'Phase 4/8: Installing Wiki templates (99-Templates/)' 'INFO'
Install-Assets -SrcRoot $Source -DstRoot $Target `
               -RelativeRoot '10-Hermes-Wiki/99-Templates' -Label 'Wiki templates'

# ============================================================
# 9) Install Claude Code agents (20-Claude-Code/agents/)
# ============================================================

Write-Host ''
Write-Step 'Phase 5/8: Installing Claude Code agents' 'INFO'
Install-Assets -SrcRoot $Source -DstRoot $Target `
               -RelativeRoot '20-Claude-Code/agents' -Label 'Claude Code agents'

# ============================================================
# 10) Install Intelligence pipelines (50-Intelligence/pipelines/)
# ============================================================

Write-Host ''
Write-Step 'Phase 6/8: Installing Intelligence pipelines config' 'INFO'
Install-Assets -SrcRoot $Source -DstRoot $Target `
               -RelativeRoot '50-Intelligence/pipelines' -Label 'Intel pipelines'

# ============================================================
# 9) Install Syncthing .stignore
# ============================================================

Write-Host ''
Write-Step 'Phase 7/8: Installing Ops runbook' 'INFO'
Install-Assets -SrcRoot $Source -DstRoot $Target `
               -RelativeRoot '90-Ops/runbook' -Label 'Ops runbook'

# ============================================================
# 12) Install Syncthing .stignore
# ============================================================

Write-Host ''
Write-Step 'Phase 8/8: Installing Syncthing .stignore (if templates available)' 'INFO'
Install-StIgnore -SrcRoot $Source -DstRoot $Target -Shares $SyncShares

# ============================================================
# 10) Summary and next steps
# ============================================================

Write-Host ''
Write-Host '=================================================' -ForegroundColor Magenta
Write-Host '  Done. Suggested next steps:' -ForegroundColor Magenta
Write-Host '=================================================' -ForegroundColor Magenta
Write-Host ''

Write-Host "  1) Add $Target to Syncthing: see $Source\90-Ops\sync\README.md"
Write-Host "  2) Place .env files in $Target\90-Ops\secrets\ subdirectories (never commit)"
Write-Host "  3) Primary: configure 10-Hermes-Wiki\.obsidian\, keep secondary read-only"
Write-Host "  4) After blueprint updates, re-run with -Force to sync docs:"
Write-Host "       .\Init-AIWorkspace.ps1 -Source $Source -Target $Target -Force"
Write-Host ''

if ($Role -eq 'secondary') {
    Write-Host '  NOTE: This machine role=secondary. 10-Hermes-Wiki/ defaults to read-only.' -ForegroundColor Yellow
    Write-Host '        Only take over when primary is unavailable (see multi-machine-protocol.md section 6).' -ForegroundColor Yellow
    Write-Host ''
}

if ($DryRun) {
    Write-Host '  This was a DRY RUN. No filesystem changes were made. Remove -DryRun to execute.' -ForegroundColor Yellow
    Write-Host ''
}
