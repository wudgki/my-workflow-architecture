# AI-Workspace Baseline Smoke Tests

本 runbook 用于验证真实环境已跑通，确认以下系统基线正常运作：

- 主电脑 `D:\AI-Workspace`
- 副电脑 `D:\AI-Workspace`
- Claude Code agents 蓝图文件
- Wiki templates（6 份）
- Intelligence pipelines keywords
- Syncthing 5 个共享根
- Obsidian / Hermes Wiki 基础链路

---

## 前置条件

在运行 smoke tests 之前，确保以下条件全部满足：

- [ ] PR #6 / #7 / #8 / #9 已合并到 main
- [ ] 主电脑已运行 `Init-AIWorkspace.ps1 -Source <repo> -Target D:\AI-Workspace -Role primary`
- [ ] 副电脑已运行 `Init-AIWorkspace.ps1 -Source <repo> -Target D:\AI-Workspace -Role secondary`
- [ ] Syncthing 已在两台机器上安装并配置 5 个共享根：
  - `AI-Workspace - Hermes Wiki`（副电脑 Receive Only）
  - `AI-Workspace - Claude Code`（双向）
  - `AI-Workspace - Inbox`（双向）
  - `AI-Workspace - Phases`（双向）
  - `AI-Workspace - Repo Research`（双向）
- [ ] 副电脑的 Wiki 共享为 **Receive Only / 仅接收**
- [ ] 不要在副电脑编辑 Hermes Wiki，除非执行接管流程（参见 `multi-machine-protocol.md` 第六节）

---

## 基线验证命令

在**主电脑**的 PowerShell 中执行：

```powershell
# 检查关键文件是否存在
$checks = @(
    'D:\AI-Workspace\.machine-id',
    'D:\AI-Workspace\20-Claude-Code\agents\repo-researcher.md',
    'D:\AI-Workspace\20-Claude-Code\agents\wiki-writer.md',
    'D:\AI-Workspace\20-Claude-Code\agents\intel-summarizer.md',
    'D:\AI-Workspace\20-Claude-Code\agents\phase-coordinator.md',
    'D:\AI-Workspace\50-Intelligence\pipelines\keywords.yaml',
    'D:\AI-Workspace\50-Intelligence\pipelines\README.md',
    'D:\AI-Workspace\10-Hermes-Wiki\99-Templates\TPL-交易复盘.md',
    'D:\AI-Workspace\10-Hermes-Wiki\99-Templates\TPL-情报日报.md',
    'D:\AI-Workspace\10-Hermes-Wiki\99-Templates\TPL-仓库对比.md',
    'D:\AI-Workspace\10-Hermes-Wiki\99-Templates\TPL-仓库分析报告.md',
    'D:\AI-Workspace\10-Hermes-Wiki\99-Templates\TPL-周报.md',
    'D:\AI-Workspace\10-Hermes-Wiki\99-Templates\TPL-Phase周期规划.md'
)

$allPass = $true
foreach ($path in $checks) {
    $exists = Test-Path $path
    $status = if ($exists) { 'PASS' } else { 'FAIL' }
    Write-Host "$status  $path" -ForegroundColor (& { if ($exists) { 'Green' } else { 'Red' } })
    if (-not $exists) { $allPass = $false }
}

Write-Host ''
if ($allPass) {
    Write-Host 'Baseline: ALL PASS' -ForegroundColor Green
} else {
    Write-Host 'Baseline: SOME FAILED - re-run Init-AIWorkspace.ps1' -ForegroundColor Red
}
```

预期：全部返回 `PASS`。

在**副电脑**上运行相同命令，同样预期全部 `PASS`。

---

## Syncthing 验证

打开两台机器的 Syncthing Web GUI（`http://127.0.0.1:8384`），确认：

### 主电脑

- [ ] 5 个共享根全部显示"Up to Date / 最新"
- [ ] 无 Out of Sync / Failed Items
- [ ] 副电脑设备状态为 Connected

### 副电脑

- [ ] 5 个共享根全部显示"Up to Date / 最新"
- [ ] Wiki 共享类型为 **Receive Only**
- [ ] 无 Out of Sync / Failed Items

### 处理 Receive Only 文件夹的"本地添加 / Local Changes"

如果副电脑的 Receive Only 文件夹出现"本地添加"提示：

1. 点击"查看本地更改"查看具体文件列表
2. **如果只是 `.sync-conflict-*` 文件或 Init 脚本生成的模板冲突副本**：
   - 可以安全地执行"还原本地更改 / Revert Local Changes"
3. **如果是人工笔记或有价值的内容**：
   - 先把文件复制到主电脑对应目录
   - 确认主电脑已收到后，再在副电脑执行还原
4. **如果不确定**：
   - 不要还原，先在 `90-Ops/sync/handover.md` 记录情况
   - 联系 Samuel 决定

---

## Smoke Test A: repo-researcher

> 目的：验证 repo-researcher agent 能按照蓝图定义完成一次完整的仓库分析流程。

### 工作目录

```powershell
cd D:\AI-Workspace
claude
```

### 测试 Prompt

在 Claude Code 主对话中输入：

```text
这是一次 smoke test，不是正式深度研究。

请读取并遵守这个 agent 定义：
D:\AI-Workspace\20-Claude-Code\agents\repo-researcher.md

请读取并使用这个输出模板：
D:\AI-Workspace\10-Hermes-Wiki\99-Templates\TPL-仓库分析报告.md

任务：
分析这个 GitHub 仓库：
https://github.com/kevinho/clawfeed

要求：
1. 只做 smoke-test 级别分析，不需要极深代码审计；
2. 如果你无法联网读取 GitHub，请在报告里明确写出 NETWORK_ACCESS_FAILED，不要编造；
3. 不要修改任何仓库代码；
4. 不要安装依赖；
5. 不要执行未知脚本；
6. 输出必须保存为 Markdown 文件；
7. 保存路径为：
D:\AI-Workspace\60-Repo-Research\reports\YYYY-MM-DD-clawfeed-smoke-test.md

报告必须至少包含：
- 仓库基本信息
- 这个仓库大概解决什么问题
- 对我的系统是否有参考价值
- 可以学习的设计
- 风险或不确定点
- 是否值得后续深度分析
- 下一步建议

完成后请告诉我文件是否已成功写入。
```

（注：`YYYY-MM-DD` 替换为当天日期，如 `2026-05-20`）

### 验证命令

```powershell
# 替换 YYYY-MM-DD 为实际日期
Test-Path D:\AI-Workspace\60-Repo-Research\reports\YYYY-MM-DD-clawfeed-smoke-test.md
```

### 通过标准

- [ ] 文件成功生成
- [ ] 路径在 `D:\AI-Workspace\60-Repo-Research\reports\`（不是 `C:\Code`）
- [ ] 报告至少包含 7 个必填章节
- [ ] 没有修改仓库源码
- [ ] 无法联网时如实标注 `NETWORK_ACCESS_FAILED`，不编造数据
- [ ] 副电脑能通过 Syncthing（`AI-Workspace - Repo Research`）收到该文件

---

## Smoke Test B: phase-coordinator

> 目的：验证 phase-coordinator agent 能基于当前系统状态生成一份结构化的 Phase 总览草稿。

### 测试 Prompt

在 Claude Code 主对话中输入：

```text
这是一次 smoke test，不是正式周报。

请读取并遵守这个 agent 定义：
D:\AI-Workspace\20-Claude-Code\agents\phase-coordinator.md

请读取并参考这些文件：
D:\AI-Workspace\10-Hermes-Wiki\99-Templates\TPL-Phase周期规划.md
D:\AI-Workspace\10-Hermes-Wiki\99-Templates\TPL-周报.md
D:\AI-Workspace\50-Intelligence\pipelines\keywords.yaml
D:\AI-Workspace\README.md
D:\AI-Workspace\90-Ops\multi-machine-protocol.md

任务：
基于当前已经完成的工作，生成一份"Phase 协调 smoke test 草稿"。

已知背景：
- Phase 1：基础架构、GitHub、Obsidian、Syncthing、多机同步已经基本完成；
- Phase 2：海外 B2B 包装平台创业系统正在建设；
- Phase 3：Crypto 量化交易系统后续搭建；
- Phase 4：Prediction Market / Polymarket / Kalshi 后续并行；
- 当前已经完成 Agent 定义、Wiki 模板、keywords.yaml、Init 脚本、Syncthing 多机同步基线。

要求：
1. 不要执行任何交易相关操作；
2. 不要修改任何配置；
3. 不要创建任务自动化；
4. 只生成一份 Markdown 草稿；
5. 保存路径为：
D:\AI-Workspace\10-Hermes-Wiki\00-Map-of-Content\YYYY-MM-DD-phase-coordinator-smoke-test.md

草稿必须包含：
- 当前 Phase 总览
- 已完成事项
- 当前风险
- 下一个 7 天建议
- 哪些任务适合继续开 PR
- 哪些任务暂时不要自动化
- 主电脑 / 副电脑协作注意事项

完成后请告诉我文件是否已成功写入。
```

### 验证命令

```powershell
# 替换 YYYY-MM-DD 为实际日期
Test-Path D:\AI-Workspace\10-Hermes-Wiki\00-Map-of-Content\YYYY-MM-DD-phase-coordinator-smoke-test.md
```

### 通过标准

- [ ] 文件成功生成
- [ ] 输出路径在 `10-Hermes-Wiki\00-Map-of-Content\`
- [ ] 内容有 Phase 1/2/3/4 分层
- [ ] 没有建议马上接实盘交易
- [ ] 没有修改任何已有配置文件
- [ ] 副电脑能通过 Syncthing（`AI-Workspace - Hermes Wiki`）收到该文件

---

## 失败排查

| 症状 | 排查方向 |
|---|---|
| `git` 命令不存在 | 安装 Git for Windows |
| PowerShell 禁止脚本执行 | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| Init 脚本报 Source 路径不存在 | 确认蓝图仓库已 `git clone` 到 `-Source` 指定的路径 |
| 文件没同步到副电脑 | 打开 Syncthing GUI 检查共享根是否显示"Up to Date" |
| 副电脑出现 `.sync-conflict-*` | 确认不是人工笔记后执行"还原本地更改" |
| Claude Code 无法联网 | 在报告里写 `NETWORK_ACCESS_FAILED`，不编造内容 |
| 输出路径错误（写到 `C:\Code`） | 检查 prompt 中路径是否明确为 `D:\AI-Workspace` |
| Agent 没按模板格式输出 | 检查 prompt 中是否明确要求"读取并使用这个模板" |
| `.machine-id` 缺失 | 重新运行 Init 脚本并指定 `-Role primary/secondary` |

---

## Guardrails（安全边界）

执行 smoke tests 时请严格遵守：

- **Smoke test 只在主电脑执行**。副电脑只做接收验证。
- **不执行交易**。任何 agent 输出如果包含交易指令，忽略。
- **不修改实盘策略**。不改 `limits.yaml`、不改 `config.yaml`、不改 blacklist。
- **不安装依赖**。不 `npm install`、不 `pip install`、不 `cargo build`。
- **不执行未知脚本**。不运行来源不明的 `.sh` / `.bat` / `.py`。
- **不把 secrets 写入 Wiki 或 GitHub**。API key / `.env` / 私钥 / 助记词永远不进入 `10-Hermes-Wiki/` 或任何 git tracked 文件。
- **副电脑只做只读验证**。确认文件通过 Syncthing 到达即可，不主动产生内容。

---

## 验收记录

每次跑完 smoke test 后，在下表打勾并注明日期：

| 日期 | 基线验证 | Syncthing | Test A (repo-researcher) | Test B (phase-coordinator) | 副电脑接收 | 备注 |
|---|---|---|---|---|---|---|
| {{YYYY-MM-DD}} | [ ] | [ ] | [ ] | [ ] | [ ] | |

---

<!--
维护说明：
- 本文件只是文档，不执行任何逻辑。
- 如需新增 smoke test，直接追加章节即可。
- 季度审查时检查 prompt 里引用的路径是否仍然有效。
- 如果蓝图目录结构变更，同步更新"基线验证命令"中的路径列表。
-->
