# 99-Templates · 模板库

> 所有 Obsidian 笔记模板集中管理。Agent 和人工都从这里复制模板，确保格式一致。

## 模板清单

| 模板文件 | 用途 | 产出落地位置 | 使用者 |
|---|---|---|---|
| `TPL-仓库分析报告.md` | GitHub 仓库分析（中文） | `60-Repo-Research/reports/` | repo-researcher agent / 人工 |
| `TPL-周报.md` | 周度回顾与计划 | `10-Hermes-Wiki/70-Personal-OS/Weekly/` | phase-coordinator / 人工 |
| `TPL-Phase周期规划.md` | Phase 级周期 OKR + 里程碑 + 任务分解 | `10-Hermes-Wiki/<Phase>/Cycle-Plans/` | phase-coordinator / 人工 |

## 命名约定

- 模板文件名统一前缀 `TPL-`，方便文件管理器排序 & Agent 识别。
- 中文标题 + 英文后缀（如需区分变体可加 `-v2`）。

## 使用方式

### 人工

1. 在 Obsidian 里 Ctrl+N 新建笔记。
2. 复制对应 `TPL-*.md` 内容粘贴。
3. 把 `{{}}` 占位符替换为实际内容。
4. 保存到指定落地目录，文件名按约定命名。

### Agent（repo-researcher / wiki-writer / phase-coordinator）

1. Agent 读取模板文件内容。
2. 用 LLM 填充 `{{}}` 占位符。
3. 人工审阅 → 确认 → 入库。

## 新增模板流程

1. 按 `TPL-<中文名>.md` 命名。
2. 加入 YAML front-matter（注释说明来源、使用方、落地位置）。
3. 用 `{{}}` 标记所有可变内容。
4. 在本文件的"模板清单"表格加一行。
5. 提交 Git。

## 待补（TODO）

- [ ] `TPL-情报日报.md`：intel-summarizer agent 的日/周情报简报模板
- [ ] `TPL-仓库对比.md`：多仓库横向对比模板（`60-Repo-Research/comparisons/`）
- [ ] `TPL-决策记录-ADR.md`：Architecture Decision Record 独立模板
- [ ] `TPL-交易复盘.md`：Phase 3 / 4 交易复盘模板
