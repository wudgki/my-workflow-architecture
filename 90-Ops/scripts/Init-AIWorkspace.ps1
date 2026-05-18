#Requires -Version 5.1
<#
.SYNOPSIS
    在主电脑 / 副电脑落地 AI-Workspace 蓝图（D:\AI-Workspace）。

.DESCRIPTION
    幂等脚本：
    - 在 -Target 目录下创建蓝图定义的全部目录结构
    - 从 -Source（本蓝图仓库 clone 出来的目录）复制文档（_about.md / README.md / SOP）
    - 生成 .machine-id（标记本机角色）
    - 生成 secrets/ 子目录占位
    - 安装 Wiki 模板（10-Hermes-Wiki/99-Templates/，copy-if-missing）
    - 安装 Syncthing .stignore（如果 90-Ops/sync/stignore/ 提供模板）
    - 默认不覆盖已存在的业务文件，仅 -Force 时覆盖文档与模板
    可重复执行，每次只补齐缺失项。

.PARAMETER Source
    本蓝图仓库已 clone 到本地的路径。
    例：C:\Code\my-workflow-architecture

.PARAMETER Target
    AI-Workspace 落地目录。默认 D:\AI-Workspace

.PARAMETER Role
    本机角色：primary | secondary。决定 .machine-id 内容与可写域。

.PARAMETER Hostname
    本机标识（写入 .machine-id）。默认 = $env:COMPUTERNAME

.PARAMETER Force
    覆盖已有文档（_about.md / README.md / 三份 SOP）与已有 Wiki 模板（99-Templates/）。
    **不会**覆盖业务数据（笔记、代码、运行期产物）。

.PARAMETER DryRun
    只打印将要执行的操作，不真正改文件系统。

.EXAMPLE
    # 主电脑首次落地
    .\Init-AIWorkspace.ps1 -Source C:\Code\my-workflow-architecture -Target D:\AI-Workspace -Role primary

.EXAMPLE
    # 副电脑首次落地（与主机不同的角色）
    .\Init-AIWorkspace.ps1 -Source C:\Code\my-workflow-architecture -Role secondary

.EXAMPLE
    # 蓝图仓库更新后，覆盖文档但保留业务数据
    .\Init-AIWorkspace.ps1 -Source C:\Code\my-workflow-architecture -Force

.EXAMPLE
    # 演练，不动文件系统
    .\Init-AIWorkspace.ps1 -Source C:\Code\my-workflow-architecture -Role primary -DryRun

.NOTES
    作者: Samuel Wu's workflow blueprint
    依赖: PowerShell 5.1+ 或 PowerShell 7
    平台: Windows 10/11
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
# 1) 蓝图定义：目录列表 + 文档清单
# ============================================================

# 顶层 + 子目录（与 README.md / _about.md 中的描述保持一致）
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

# 从 Source 复制到 Target 的文档（路径相对仓库根 / 落地根）
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

# Syncthing 共享根 -> 在 Target 内对应路径
# 用于把 90-Ops/sync/stignore/<scope>.stignore 安装为 <Target>/<path>/.stignore
$SyncShares = @{
    'wiki'        = '10-Hermes-Wiki'
    'claude-code' = '20-Claude-Code'
    'phases'      = '30-Phases'
    'inbox'       = '00-Inbox'
    'repo-research' = '60-Repo-Research'
}

# ============================================================
# 2) 工具函数
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
        Write-Step "目录已存在: $Path" 'SKIP'
        return
    }
    if ($DryRun) {
        Write-Step "创建目录: $Path" 'INFO'
        return
    }
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
    Write-Step "创建目录: $Path" 'OK'
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
        Write-Step "源文件缺失，跳过: $Relative" 'WARN'
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
            Write-Step "文档已存在（用 -Force 覆盖）: $Relative" 'SKIP'
            return
        }
        Write-Step "覆盖文档: $Relative" 'WARN'
    } else {
        Write-Step "复制文档: $Relative" 'OK'
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
            Write-Step "$Description 已存在: $Path" 'SKIP'
            return
        }
        Write-Step "覆盖 $Description : $Path" 'WARN'
    } else {
        Write-Step "写入 $Description : $Path" 'OK'
    }
    if ($DryRun) { return }
    $dir = Split-Path $Path -Parent
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    # PS 5.1 的 -Encoding UTF8 会写入 BOM；YAML / Markdown 工具均能识别，可接受。
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
        Write-Step ".stignore 模板目录不存在，跳过 Syncthing 步骤: $tplDir" 'WARN'
        return
    }
    foreach ($scope in $Shares.Keys) {
        $tpl = Join-Path $tplDir "$scope.stignore"
        if (-not (Test-Path -LiteralPath $tpl)) {
            Write-Step "无模板，跳过 .stignore for '$scope'" 'SKIP'
            continue
        }
        $shareRoot = Join-Path $DstRoot $Shares[$scope]
        $dst = Join-Path $shareRoot '.stignore'
        if (-not (Test-Path -LiteralPath $shareRoot)) {
            if (-not $DryRun) { New-Item -ItemType Directory -Path $shareRoot -Force | Out-Null }
        }
        if ((Test-Path -LiteralPath $dst) -and (-not $Force)) {
            Write-Step ".stignore 已存在（用 -Force 覆盖）: $($Shares[$scope])" 'SKIP'
            continue
        }
        if (-not $DryRun) { Copy-Item -LiteralPath $tpl -Destination $dst -Force }
        Write-Step "安装 .stignore: $($Shares[$scope])" 'OK'
    }
}

function Install-Templates {
    <#
    .SYNOPSIS
        把 Wiki 模板（10-Hermes-Wiki/99-Templates/）安装到目标工作区。

    .DESCRIPTION
        - 整目录递归扫描源端模板（含 _about.md 与所有 TPL-*.md / 子目录）
        - 默认 copy-if-missing：目标已存在 → 输出 SKIP 提示，不动文件
        - 仅当 -Force 显式启用时才覆盖目标
        - DryRun 模式：列出**每个**会被复制或跳过的模板文件
        - 路径锁定为 10-Hermes-Wiki/99-Templates/（与产出落地约定一致）
    #>
    param(
        [string]$SrcRoot,
        [string]$DstRoot
    )

    $relativeRoot = '10-Hermes-Wiki/99-Templates'
    $srcDir = Join-Path $SrcRoot $relativeRoot
    $dstDir = Join-Path $DstRoot $relativeRoot

    if (-not (Test-Path -LiteralPath $srcDir -PathType Container)) {
        Write-Step "Wiki 模板源目录不存在，跳过模板安装: $srcDir" 'WARN'
        return
    }

    # 确保目标目录存在
    if (-not (Test-Path -LiteralPath $dstDir -PathType Container)) {
        if ($DryRun) {
            Write-Step "将创建目录: $relativeRoot" 'INFO'
        } else {
            New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
            Write-Step "创建目录: $relativeRoot" 'OK'
        }
    }

    # 递归列出所有模板文件（排除 .gitkeep）
    $files = Get-ChildItem -LiteralPath $srcDir -Recurse -File `
                | Where-Object { $_.Name -ne '.gitkeep' }

    if (-not $files -or $files.Count -eq 0) {
        Write-Step '模板目录为空，无文件可安装' 'WARN'
        return
    }

    $countCopy = 0
    $countSkip = 0
    $countOverwrite = 0

    foreach ($f in $files) {
        # 计算相对路径（兼容子目录）
        $relativeFile = $f.FullName.Substring($srcDir.Length).TrimStart('\', '/')
        $dst = Join-Path $dstDir $relativeFile
        $displayPath = "$relativeRoot/$($relativeFile -replace '\\', '/')"

        # 父目录（如模板有子目录结构）
        $dstParent = Split-Path $dst -Parent
        if (-not (Test-Path -LiteralPath $dstParent)) {
            if (-not $DryRun) {
                New-Item -ItemType Directory -Path $dstParent -Force | Out-Null
            }
        }

        if (Test-Path -LiteralPath $dst) {
            if ($Force) {
                # 覆盖路径
                Write-Step "覆盖模板: $displayPath" 'WARN'
                if (-not $DryRun) {
                    Copy-Item -LiteralPath $f.FullName -Destination $dst -Force
                }
                $countOverwrite++
            } else {
                # copy-if-missing：跳过
                Write-Step "模板已存在（用 -Force 覆盖）: $displayPath" 'SKIP'
                $countSkip++
            }
        } else {
            # 新增
            Write-Step "复制模板: $displayPath" 'OK'
            if (-not $DryRun) {
                Copy-Item -LiteralPath $f.FullName -Destination $dst -Force
            }
            $countCopy++
        }
    }

    # 小结
    Write-Step "模板安装小结: 新增 $countCopy / 覆盖 $countOverwrite / 跳过 $countSkip （共 $($files.Count) 文件）" 'INFO'
}

# ============================================================
# 3) 预检
# ============================================================

Write-Host ''
Write-Host '=================================================' -ForegroundColor Magenta
Write-Host '  AI-Workspace Blueprint Initializer' -ForegroundColor Magenta
Write-Host '=================================================' -ForegroundColor Magenta
Write-Host ''

Write-Step "蓝图源:   $Source"
Write-Step "落地目标: $Target"
Write-Step "角色:     $(if ($Role) { $Role } else { '<未指定，跳过 .machine-id>' })"
Write-Step "本机名:   $Hostname"
Write-Step "Force:    $Force"
Write-Step "DryRun:   $DryRun"
Write-Host ''

# 校验 Source
if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "蓝图源目录不存在: $Source"
}
$readme = Join-Path $Source 'README.md'
$signature = Join-Path $Source '90-Ops/multi-machine-protocol.md'
if (-not (Test-Path -LiteralPath $readme) -or -not (Test-Path -LiteralPath $signature)) {
    throw "Source 看起来不是有效的蓝图仓库（缺少 README.md 或 90-Ops/multi-machine-protocol.md）: $Source"
}

# 校验 Target 父目录可达
$parent = Split-Path $Target -Parent
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    throw "Target 父目录不存在: $parent"
}

if (-not (Test-IsAdmin)) {
    Write-Step '当前非管理员权限运行（创建 D:\AI-Workspace 通常无需管理员，继续）' 'INFO'
}

# ============================================================
# 4) 创建 Target 根
# ============================================================

Ensure-Dir -Path $Target

# ============================================================
# 5) 创建全部目录
# ============================================================

Write-Host ''
Write-Step '阶段 1/5: 创建目录骨架' 'INFO'
foreach ($d in $Directories) {
    Ensure-Dir -Path (Join-Path $Target $d)
}

# ============================================================
# 6) 复制文档
# ============================================================

Write-Host ''
Write-Step '阶段 2/5: 复制文档（_about / SOP / README）' 'INFO'
foreach ($f in $DocFiles) {
    Copy-Doc -SrcRoot $Source -DstRoot $Target -Relative $f
}

# ============================================================
# 7) 生成 .machine-id（如指定 Role）
# ============================================================

Write-Host ''
Write-Step '阶段 3/5: 生成本机标识与配置文件' 'INFO'

if ($Role) {
    $machineIdPath = Join-Path $Target '.machine-id'
    $now = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')
    $machineIdContent = @"
# AI-Workspace machine identity (本文件不入 git，参见 .gitignore)
hostname: $Hostname
role: $Role
initialized_at: $now
last_handover: null
notes: |
  本文件由 90-Ops/scripts/Init-AIWorkspace.ps1 生成。
  写入受限目录前，脚本应检查本文件的 role 字段。
"@
    Write-FileIfMissing -Path $machineIdPath -Content $machineIdContent -Description '.machine-id'
}
else {
    Write-Step '未指定 -Role，跳过 .machine-id 生成' 'SKIP'
}

# 顶层 .gitignore 中已经忽略了 .machine-id 之类的本地文件；这里给 secrets/ 加一个 README（如果还没有）
$secretsReadme = Join-Path $Target '90-Ops/secrets/README.md'
if (-not (Test-Path -LiteralPath $secretsReadme)) {
    # 已通过 DocFiles 复制；这里只兜底
    Write-Step '90-Ops/secrets/README.md 应已通过 DocFiles 复制，请检查' 'INFO'
}

# 生成 secrets 子目录的 .gitkeep（保证空目录可见）
foreach ($scope in @('shared', 'phase2', 'phase3', 'phase4', 'hermes', 'intel')) {
    $keep = Join-Path $Target "90-Ops/secrets/$scope/.gitkeep"
    if (-not (Test-Path -LiteralPath $keep)) {
        if (-not $DryRun) { New-Item -ItemType File -Path $keep -Force | Out-Null }
        Write-Step "占位文件: 90-Ops/secrets/$scope/.gitkeep" 'OK'
    }
}

# ============================================================
# 8) 安装 Wiki 模板 (10-Hermes-Wiki/99-Templates/)
# ============================================================

Write-Host ''
Write-Step '阶段 4/5: 安装 Wiki 模板（99-Templates/）' 'INFO'
Install-Templates -SrcRoot $Source -DstRoot $Target

# ============================================================
# 9) 安装 Syncthing .stignore
# ============================================================

Write-Host ''
Write-Step '阶段 5/5: 安装 Syncthing .stignore（如有模板）' 'INFO'
Install-StIgnore -SrcRoot $Source -DstRoot $Target -Shares $SyncShares

# ============================================================
# 9) 生成本机操作摘要
# ============================================================

Write-Host ''
Write-Host '=================================================' -ForegroundColor Magenta
Write-Host '  完成。后续手动步骤建议：' -ForegroundColor Magenta
Write-Host '=================================================' -ForegroundColor Magenta
Write-Host ''

Write-Host "  1) 把 $Target 加入 Syncthing：参考 $Source\90-Ops\sync\README.md"
Write-Host "  2) 在 $Target\90-Ops\secrets\ 各子目录放入对应 .env（永不入 git）"
Write-Host "  3) 主电脑：把 10-Hermes-Wiki\.obsidian\ 配置好后，先在副电脑保持只读"
Write-Host "  4) 在仓库变更后，定期重新执行本脚本（可加 -Force 同步文档更新）："
Write-Host "       .\Init-AIWorkspace.ps1 -Source $Source -Target $Target -Force"
Write-Host ''

if ($Role -eq 'secondary') {
    Write-Host '  注意：本机角色=secondary，默认 10-Hermes-Wiki/ 只读。' -ForegroundColor Yellow
    Write-Host '       仅在主机不可用时按 multi-machine-protocol.md 第六节执行接管流程。' -ForegroundColor Yellow
    Write-Host ''
}

if ($DryRun) {
    Write-Host '  本次为 DryRun，文件系统未变更。去掉 -DryRun 实际执行。' -ForegroundColor Yellow
    Write-Host ''
}
