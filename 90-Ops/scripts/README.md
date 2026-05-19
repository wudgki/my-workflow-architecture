# 90-Ops/scripts/

Operations scripts for setting up, syncing, and auditing the AI-Workspace blueprint.

| 脚本 | 用途 | 详细文档 |
|---|---|---|
| [`Init-AIWorkspace.ps1`](./Init-AIWorkspace.ps1) | 在主电脑 / 副电脑落地 AI-Workspace 蓝图 | 见脚本顶部 `<# .SYNOPSIS #>` |
| [`Audit-ScriptHygiene.ps1`](./Audit-ScriptHygiene.ps1) | 审计 PowerShell 脚本的编码隐患（防止 PS 5.1 解析失败） | 见下文 |

---

## Audit-ScriptHygiene.ps1

### 为什么需要这个工具

PR #3 实测中我们踩到了一个坑：UTF-8 no-BOM + 中文字符串在 Windows PowerShell 5.1 下被误判为 ANSI 编码，结果输出乱码、引号配对错乱、解析失败。这类问题肉眼很难发现，但**机器一扫即知**。

`Audit-ScriptHygiene.ps1` 把所有可能导致 PS 解析失败或被恶意利用的字符问题集中在一个工具里检测。

### 检测项目

| # | 检查 | 严重度 | 解释 |
|---|---|---|---|
| 1 | UTF-8 BOM 缺失 + 含非 ASCII 字符的 `.ps1` | CRITICAL | PS 5.1 无 BOM 时按 ANSI 读，必乱码 |
| 2 | 代码区出现非 ASCII 字符 | CRITICAL | 字符串/注释里允许，代码里禁止 |
| 3 | 双向控制字符 (U+202A-U+202E, U+2066-U+2069) | CRITICAL | "Trojan Source" 攻击向量 |
| 4 | 零宽字符 / Word Joiner | CRITICAL | 隐藏字符可能藏命令注入 |
| 5 | C0 / C1 控制字符（除 `\t\n\r`） | CRITICAL | 常规非法字符 |
| 6 | 智能引号 / em-dash / NBSP（非空格） | CRITICAL | 看似 ASCII 但解析器拒收 |
| 7 | 软连字符 / 不寻常空格 / 省略号 | WARNING | 通常是粘贴文档时引入的脏字符 |
| 8 | `.ps1` 含 BOM | INFO | PS 5.1 OK，PS 7 OK，仅提示 |
| 9 | 同一文件混合 CRLF / LF | WARNING | 排版不一致 |
| 10 | 行尾空白（可选，`-CheckTrailingWhitespace`） | INFO | 仅美观 |

### 严重度分级

- **CRITICAL** — 一定要修。要么 PS 解析失败，要么是潜在安全隐患。
- **WARNING** — 强烈建议修。`-Strict` 时升级为致命错。
- **INFO** — 提示性，用于审阅，不影响构建。

### 退出码

| 退出码 | 含义 |
|---|---|
| 0 | 全部通过（按 `-FailOn` 阈值判定） |
| 1 | 有未通过项 |
| 2 | 参数错误 / I/O 失败 |

### 常用命令

```powershell
# 1. 默认：扫当前目录所有 .ps1 / .psm1 / .psd1
.\Audit-ScriptHygiene.ps1

# 2. 单文件
.\Audit-ScriptHygiene.ps1 -Path .\Init-AIWorkspace.ps1

# 3. 扩展到 yaml / md（适合发版前总扫）
.\Audit-ScriptHygiene.ps1 -Path . -Include '*.ps1','*.yaml','*.md'

# 4. CI 模式（warning 也算失败）
.\Audit-ScriptHygiene.ps1 -Strict -Format summary

# 5. JSON 输出（管道给其他工具）
.\Audit-ScriptHygiene.ps1 -Format json | ConvertFrom-Json

# 6. 加查行尾空白
.\Audit-ScriptHygiene.ps1 -CheckTrailingWhitespace
```

### 输出格式

**`-Format text`（默认）**：每个文件一段，列出所有 finding，按严重度着色。

```
PASS  C:\AI-Workspace\90-Ops\scripts\Init-AIWorkspace.ps1  (19980 bytes, BOM=False)
FAIL  C:\path\to\bad.ps1  (3072 bytes, BOM=False)
  [CRITICAL] CODE_NONASCII          L42:18  Non-ASCII codepoint U+4E2D in CODE region (...)
  [CRITICAL] PS_NONASCII_NO_BOM     L1:1    .ps1 contains non-ASCII characters but has no UTF-8 BOM (...)
  [WARNING ] MIXED_LINE_ENDINGS             Mixed line endings: CRLF=12, lone LF=4
```

**`-Format summary`**：每个文件一行，适合 CI。

```
PASS  C=0  W=0  I=0  C:\AI-Workspace\90-Ops\scripts\Init-AIWorkspace.ps1
FAIL  C=2  W=1  I=0  C:\path\to\bad.ps1
```

**`-Format json`**：完整结构化数据，stdout 输出（其它日志静默）。

```json
{
  "scanned_at": "2026-05-19T12:34:56.789+08:00",
  "scan_root":  "C:\\Code\\my-workflow-architecture",
  "file_count": 2,
  "files": [
    {
      "Path": "C:\\...\\Init-AIWorkspace.ps1",
      "Size": 19980,
      "HasBom": false,
      "IsPowerShell": true,
      "Findings": [],
      "CriticalCount": 0,
      "WarningCount": 0,
      "InfoCount": 0,
      "ReadError": null
    }
  ]
}
```

### 开发约定

1. **本工具自身必须通过自身审计** — 任何修改后请先跑：
   ```powershell
   .\Audit-ScriptHygiene.ps1 -Path .\Audit-ScriptHygiene.ps1
   ```
   目标：`C=0  W=0`。
2. 不要在 `<# .SYNOPSIS #>` 块里写文字 `#>`（它会被 PS 解析器当成块结束标记，提前终止帮助文档）。
3. 不要在 `Init-AIWorkspace.ps1` 等其他脚本里直接 invoke 本工具 —— 审计是 CI / 开发者手动操作，不属于 init 路径。

### 路线图（暂未实现）

- [ ] GitHub Actions workflow：PR 自动跑 audit，CRITICAL 阻止合并
- [ ] PSScriptAnalyzer 集成：在审计基础上加 PowerShell 风格检查
- [ ] Pre-commit hook：本地 commit 前自动跑
- [ ] HTML 报告输出（适合非 CI 环境的 review）

详见 PR #4 描述与未来 PR。
