# 20-Claude-Code/agents/

Claude Code 子 Agent 定义集合。每个 `.md` 文件就是一个 Agent，包含 YAML frontmatter（name / description / tools）+ 中文系统提示正文。

## Agent 清单

| Agent | 触发场景 | 主要产出 | 详细文档 |
|---|---|---|---|
| `repo-researcher` | "分析这个仓库" / "对比这几个仓库" | `60-Repo-Research/reports/` 中文报告 | [`repo-researcher.md`](./repo-researcher.md) |
| `wiki-writer` | "把草稿润色入 Wiki" | `10-Hermes-Wiki/<Phase>/...md` 双链笔记 | [`wiki-writer.md`](./wiki-writer.md) |
| `intel-summarizer` | "总结今天/这周的情报" | `<Phase>/Daily-Digest/` 或 `Weekly-Digest/` 简报 | [`intel-summarizer.md`](./intel-summarizer.md) |
| `phase-coordinator` | "出周报" / "更新 MOC" / "看 Phase 依赖" | `Weekly/`、`00-Map-of-Content/` | [`phase-coordinator.md`](./phase-coordinator.md) |

## 设计原则

1. **中文优先**：所有 agent 默认用中文产出。
2. **不替代决策**：agent 只做素材压缩、结构化、双链补全；交易决策 / 商业决策 / 仓库判定 / 周报反思 必须由 Samuel 亲自写。
3. **写入域受限**：每个 agent 在 frontmatter 注释里明确"边界"小节，禁止跨域写入。例如 `intel-summarizer` 不能改 `30-Phases/`；`wiki-writer` 不能动 `60-Repo-Research/`。
4. **不要造数据 / 死链**：报告里的数字必须可追溯；`[[]]` 双链必须指向真实存在的笔记。
5. **可由其它机器复用**：本目录与 Wiki 一起强同步（参见 `90-Ops/multi-machine-protocol.md`），主机 / 副机 调用同一份 agent 定义。

## 落地时序

四个 agent 之间不强依赖，但典型协作链是：

```
[外部源]
  -> 50-Intelligence/community-bridges/  (PR #8 之后启用)
  -> 00-Inbox/<source>-Captures/         (写入 capture)
  -> intel-summarizer                    (生成简报)
  -> wiki-writer                         (把简报里的关键素材润色入 Wiki)
  -> phase-coordinator                   (周报里引用 Wiki + 简报)

外加一条侧线：
[GitHub URL]
  -> repo-researcher                     (生成中文报告)
  -> 60-Repo-Research/reports/
```

## 调用方式

在 Claude Code 主对话里说出与 Agent `description` 字段匹配的请求即可，Claude Code 会自动选用对应 agent。

例：
- "分析一下 https://github.com/foo/bar，看看适不适合 Phase 3" → `repo-researcher`
- "把 Inbox 里 telegram-2026-05-19-xxx 那条整理进 Wiki" → `wiki-writer`
- "出一份本周 Phase 3 的情报日报" → `intel-summarizer`
- "更新所有 Phase 的 MOC" → `phase-coordinator`

## 不在本 PR 范围内

以下内容会在后续 PR 单独处理：

- ❌ slash 命令 (`/repo-analysis` 等) - 后续 PR
- ❌ Skill 包定义 - 后续 PR
- ❌ MCP 服务器配置 (`playwright-mcp` / `mcp-chrome` / `r.jina.ai`) - 后续 PR
- ❌ 全局 prompt 模板 (`prompts/`) - 后续 PR
- ❌ 长期记忆 (`memory/CLAUDE.md`) - 后续 PR

## 模板锚点

各 agent 引用的中文模板在 `10-Hermes-Wiki/99-Templates/`：

- `TPL-仓库分析报告.md` ← `repo-researcher`
- `TPL-周报.md`         ← `phase-coordinator`
- `TPL-Phase周期规划.md` ← 由 Samuel 与 ChatGPT 维护，agent 只读

未来若 PR #7 落地新模板（情报日报 / 仓库对比 / 交易复盘），相应 agent 需要更新对应章节的引用。
