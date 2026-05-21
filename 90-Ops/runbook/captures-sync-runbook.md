# VPS Telegram-Captures 回传 Runbook

本文档记录如何配置 VPS → 主电脑的 Telegram-Captures 单向 rsync 同步，
使你本地 Obsidian 能直接查看 bridge-ingress 落盘的消息文件。

> ⚠️ **单向：VPS → 主电脑。主电脑永不写回 VPS。**
> Syncthing 已配好主电脑→副电脑的 `00-Inbox` 共享，所以副电脑也能看到。

---

## 架构

```
VPS /data/inbox/Telegram-Captures/
         |
         | rsync over SSH (pull, 单向)
         v
主电脑 D:\AI-Workspace\00-Inbox\Telegram-Captures\
         |
         | Syncthing (已有 AI-Workspace - Inbox 共享)
         v
副电脑 D:\AI-Workspace\00-Inbox\Telegram-Captures\
```

---

## 前置条件

- [ ] bridge-ingress 已在 VPS 上运行并落盘
- [ ] 主电脑已安装 rsync（见下方安装指南）
- [ ] 主电脑可通过 SSH 连接 VPS

---

## rsync Windows 安装指南

Windows 原生不自带 rsync，推荐以下方案（按优先级排列）：

### 方案 A：Git for Windows 自带的 rsync（推荐）

如果你已安装 Git for Windows（大概率已有），它自带 MSYS2 环境中的 rsync。

验证：

```powershell
& "C:\Program Files\Git\usr\bin\rsync.exe" --version
```

如果输出版本号，直接用。把脚本中的 `rsync` 改为完整路径，或把
`C:\Program Files\Git\usr\bin\` 加入 `$env:PATH`：

```powershell
$env:PATH = "C:\Program Files\Git\usr\bin;" + $env:PATH
rsync --version
```

> ⚠️ 注意：Git for Windows 的 rsync 版本可能较旧（3.2.x），但对本场景
> （纯文本 .md 文件增量拉取）完全够用。

### 方案 B：WSL（Windows Subsystem for Linux）

如果你已装了 WSL（Ubuntu / Debian），rsync 是内置的：

```bash
# 在 WSL 中
rsync --version    # 通常 3.2+ 已可用
# 如果没有：
sudo apt install rsync
```

从 PowerShell 调用 WSL rsync：

```powershell
wsl rsync -avz -e "ssh -i ~/.ssh/hermes-rsync-key" root@<VPS_IP>:/data/inbox/Telegram-Captures/ /mnt/d/AI-Workspace/00-Inbox/Telegram-Captures/
```

> 注意路径转换：Windows `D:\` 在 WSL 里是 `/mnt/d/`。

### 方案 C：Scoop 包管理器安装

```powershell
# 安装 scoop（如果还没有）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression

# 安装 rsync
scoop install rsync
rsync --version
```

Scoop 的 rsync 来自 MSYS2 编译，兼容性好，自动加入 PATH。

### 方案 D：cwrsync（独立安装包）

从 [https://itefix.net/cwrsync](https://itefix.net/cwrsync) 下载免费版。
解压后把 `bin\` 目录加入 PATH。适合不想装 Git / WSL / Scoop 的环境。

### 选哪个？

| 你的环境 | 推荐 |
|---|---|
| 已有 Git for Windows | 方案 A（零安装） |
| 已有 WSL Ubuntu | 方案 B（零安装，但路径需转换） |
| 喜欢包管理器 | 方案 C（scoop，一行命令） |
| 只想最小依赖 | 方案 D（独立 zip 解压） |

安装后验证：

```powershell
rsync --version
# 期望输出：rsync  version 3.x.x  protocol version 31+
```

---

## 步骤 1：生成 SSH 密钥对（主电脑）

```powershell
ssh-keygen -t ed25519 -f $HOME\.ssh\hermes-rsync-key -C "hermes-rsync-readonly"
```

**不要设 passphrase**（自动化 cron/Task Scheduler 无法交互输入）。

生成两个文件：
- `~/.ssh/hermes-rsync-key` (私钥，留在主电脑)
- `~/.ssh/hermes-rsync-key.pub` (公钥，部署到 VPS)

---

## 步骤 2：部署 guard 脚本 + 公钥到 VPS

### 2a. 部署 rsync guard 脚本

将 `90-Ops/scripts/rsync-captures-guard.sh` 复制到 VPS：

```bash
# 在 VPS 上执行
scp rsync-captures-guard.sh root@<VPS_IP>:/root/.ssh/rsync-captures-guard.sh
# 或直接在 VPS 上：
nano /root/.ssh/rsync-captures-guard.sh
# 粘贴 90-Ops/scripts/rsync-captures-guard.sh 的内容

chmod 700 /root/.ssh/rsync-captures-guard.sh
```

guard 脚本的作用：

- 读取 `SSH_ORIGINAL_COMMAND`（rsync 客户端自动发送的服务端命令）
- 验证必须以 `rsync --server --sender` 开头（只允许读取）
- 验证最终路径必须是 `/data/inbox/Telegram-Captures/`
- 拒绝任何含 shell 元字符的命令（防注入）
- 通过验证后 exec 执行原始命令（不经 eval）
- 日志写入 `/tmp/hermes-rsync-original-command.log`（仅命令+时间戳，无 secret）

为什么不用静态 `command="rsync --server --sender -logDtprze..."`：

- rsync 客户端发送的 `--server` 标志会随版本变化（3.2 vs 3.3 不同）
- `--dry-run`、`--progress`、压缩选项都会改变 flag 字符串
- 静态匹配会导致 DryRun 或跨版本场景下连接被拒绝

### 2b. 配置 authorized_keys

```bash
nano ~/.ssh/authorized_keys
```

添加一行（用你的 .pub 内容替换 `ssh-ed25519 AAAA...`）：

```
restrict,command="/root/.ssh/rsync-captures-guard.sh" ssh-ed25519 AAAA... hermes-rsync-readonly
```

**说明**：

- `restrict`：禁止 port forwarding / agent forwarding / pty / X11
- `command="...guard.sh"`：所有 SSH 请求都先经过 guard 脚本验证
- guard 脚本只放行 `rsync --server --sender ... /data/inbox/Telegram-Captures/`
- 即使私钥泄露，攻击者只能 rsync 读取这一个目录，不能执行任何命令
- 兼容所有 rsync 版本和 flag 组合（--dry-run、--progress 等）

---

## 步骤 3：测试连通性

```powershell
ssh -i $HOME\.ssh\hermes-rsync-key root@<VPS_IP> echo hello
```

期望输出：被 `command=` 限制，显示 rsync 协议协商文本或报错 "command not allowed"。

更好的测试：

```powershell
.\90-Ops\scripts\Sync-Captures-FromVPS.ps1 -VpsHost root@<VPS_IP> -DryRun
```

期望：列出远端文件，不实际传输。

---

## 步骤 4：首次全量同步

```powershell
.\90-Ops\scripts\Sync-Captures-FromVPS.ps1 -VpsHost root@<VPS_IP>
```

期望：`D:\AI-Workspace\00-Inbox\Telegram-Captures\` 出现 VPS 上的 `.md` 文件。

---

## 步骤 5：配置定时任务

### Windows Task Scheduler（推荐）

```powershell
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"C:\Code\my-workflow-architecture\90-Ops\scripts\Sync-Captures-FromVPS.ps1`" -VpsHost root@<VPS_IP>"

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Days 3650)

Register-ScheduledTask -TaskName "Hermes-Captures-Sync" -Action $action -Trigger $trigger -RunLevel Limited
```

每 15 分钟拉取一次。rsync 是增量的，无新文件时几乎不传数据。

### WSL cron（替代）

```bash
crontab -e
# 添加：
*/15 * * * * rsync -avz -e "ssh -i ~/.ssh/hermes-rsync-key" root@<VPS_IP>:/data/inbox/Telegram-Captures/ /mnt/d/AI-Workspace/00-Inbox/Telegram-Captures/
```

---

## 步骤 6：验证 Syncthing 传递到副电脑

同步完成后，检查副电脑 `D:\AI-Workspace\00-Inbox\Telegram-Captures\` 是否出现文件。

如果副电脑设为 Receive Only（你之前的配置），文件应自动出现，无需额外操作。

---

## 安全要求

- ❌ **私钥不提交 git**（`~/.ssh/hermes-rsync-key` 留在主电脑本地）
- ❌ **公钥不写入 PR / README**（只手动部署到 VPS）
- ❌ **永不从主电脑推文件到 VPS**（rsync 方向锁定）
- ✅ VPS 的 `authorized_keys` 用 `restrict,command=` 最小权限
- ✅ 私钥无 passphrase（自动化需要），但文件权限 600
- ✅ 如果私钥泄露：从 VPS `authorized_keys` 删除该行即可

---

## 故障排查

| 现象 | 可能原因 | 处置 |
|---|---|---|
| `Permission denied (publickey)` | 公钥没部署 / 路径错 | 核对 VPS authorized_keys |
| `rsync: connection unexpectedly closed` | VPS 重启 / 网络断 | 重试；检查 VPS 是否在线 |
| `rsync error: some files vanished` (exit 24) | 文件在传输中被移走 | 正常现象（bridge 在写新 .tmp 文件然后 rename）；脚本视为 WARN 不报错 |
| `rsync: partial transfer` (exit 23) | 部分文件因错误无法传输 | 通常非致命；脚本视为 WARN；下次 sync 会补齐 |
| 同步后 Syncthing 未分发到副电脑 | Syncthing 暂停 / Receive Only 冲突 | 检查 Syncthing Web UI |
| 文件时间戳不对 | rsync 没加 `-t` | 脚本已含 `-avz`（`-a` 包含 `-t`） |

---

## 验收记录

| 日期 | 主电脑 | DryRun 通过 | 首次全量同步 | Task Scheduler 配置 | 副电脑收到文件 | 备注 |
|---|---|---|---|---|---|---|
| YYYY-MM-DD | _ | OK/FAIL | OK/FAIL | OK/FAIL | OK/FAIL | _ |

---

## 不做（明确边界）

- ❌ 不从主电脑写回 VPS（单向）
- ❌ 不动 Syncthing 五个共享的配置
- ❌ 不在 VPS 装 Syncthing
- ❌ 不用 rclone / 对象存储 / 云盘中转
- ❌ 不同步 bridge 日志 / docker 日志（只同步 Telegram-Captures）
- ❌ 不处理 intel-pipelines 产出（那是未来 PR 的事）
