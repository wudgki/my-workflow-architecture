# 20-Claude-Code · Claude Code 共用资产

跨项目复用的 Claude Code 配置、Agent、Skill、MCP、Prompt、长期记忆。**与具体业务项目解耦**：业务代码在 `30-Phases/`，本目录只放可重用的"工具人"。

## 子目录

| 目录 | 内容 |
|---|---|
| `agents/` | 子 Agent 定义（含 `repo-researcher`、`intel-summarizer`、`wiki-writer` 等） |
| `commands/` | 自定义 slash 命令（`/repo-analysis`、`/wiki-draft`、`/phase-status`） |
| `skills/` | Skill 包（按主题打包：crypto / b2b / repo-research / 内容创作） |
| `mcp-servers/` | MCP 服务器配置：`playwright-mcp`、`mcp-chrome`、`r.jina.ai` 等 |
| `prompts/` | 中文系统提示模板、风格模板、人设 |
| `memory/` | 全局 `CLAUDE.md`、长期记忆 / 项目记忆索引 |
| `logs/` | 任务执行日志（按日期分卷） |

## 核心原则

1. **中文优先**：所有 prompts / 输出模板默认中文。
2. **模块化**：一个 Skill 只做一件事，组合优于嵌套。
3. **可被任意 Phase 引用**：Phase 项目的 `CLAUDE.md` 通过相对路径引用本目录的 agents / skills，不复制。
4. **多机一致**：本目录与 Wiki 一起强同步（见 `90-Ops/multi-machine-protocol.md`）。

## 关键 Agent 清单（建议落地）

- `repo-researcher`：抓取 GitHub 仓库 → 中文分析报告 → 落地到 `60-Repo-Research/reports/`。
- `wiki-writer`：把 `00-Inbox/Wiki-Drafts/` 的草稿润色 + 双链补全 → 入 `10-Hermes-Wiki/`。
- `intel-summarizer`：汇总 `00-Inbox/{Discord,Telegram,Feishu}-Captures/` → 生成日/周情报简报。
- `phase-coordinator`：跨 Phase 状态同步，更新 `00-Map-of-Content/` MOC。
