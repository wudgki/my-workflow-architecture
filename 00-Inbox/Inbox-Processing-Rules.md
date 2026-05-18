# Inbox Processing Rules · 收件箱处理规则

> 入箱（Capture）→ 待处理（Triage）→ 草稿（Draft）→ 入库 / 上线（Publish）→ 归档（Archive）

本文件定义所有从外部进入 `00-Inbox/` 的素材如何被消化。规则要简单、能机器化、能让 Agent 半自动跑。

---

## 一、收件箱总览

| 子目录 | 来源 | 默认处理者 | 默认下游 |
|---|---|---|---|
| `Discord-Captures/` | Discord 频道 / DM | `intel-summarizer` agent | `10-Hermes-Wiki/30-Phase3-.../KOL-Tracking` 或 `Wiki-Drafts/` |
| `Telegram-Captures/` | Telegram 群 / 频道 | `intel-summarizer` | 同上 |
| `Feishu-Captures/` | 飞书机器人推送 | `intel-summarizer` | 同上 |
| `Web-Clips/` | r.jina.ai / mcp-chrome / Playwright 抓取的网页 | `wiki-writer` | `Wiki-Drafts/` 或 `60-Repo-Research/` |
| `Repo-Captures/` | GitHub 仓库原始抓取（README / 关键文件） | `repo-researcher` | `60-Repo-Research/reports/` |
| `To-Process/` | 任意未分类输入 | 人工 | 任一终点 |
| `Wiki-Drafts/` | 已被处理的中文草稿 | `wiki-writer` | `10-Hermes-Wiki/` |

---

## 二、命名约定

```
YYYY-MM-DD_<source>_<short-topic-kebab-case>.md
```

示例：

- `2026-05-18_telegram_kol-bigshort-call.md`
- `2026-05-18_repo_chencore-autoresearch-crypto.md`
- `2026-05-18_web_b2b-printing-overseas-trends.md`

> 文件**正文可以是中文**，**文件名一律 ASCII**，避免跨平台同步问题。

---

## 三、入箱时必填的 Front-Matter

每个新建的入箱文件必须有 YAML front-matter：

```yaml
---
captured_at: 2026-05-18T14:32:00+08:00
source: telegram          # discord | telegram | feishu | web | repo | manual
source_id: "群名/频道/URL/owner-repo"
phase: 3                  # 1 | 2 | 3 | 4 | null（暂未归类）
tags: [crypto, kol, perp]
status: new               # new | triaged | drafting | published | archived
priority: 2               # 1 高 | 2 中 | 3 低
owner: samuel             # samuel | claude | hermes
---
```

`status` 必须随处理步骤推进，让脚本能筛选未处理项。

---

## 四、处理流转 SOP

```
[Capture]      落入 00-Inbox/<source>-Captures/，status=new
   │
   ▼
[Triage]       人工或 intel-summarizer 阅读 → 决定去向：
   │           ├─ 直接归档（无价值）           → 90-Archive/，status=archived
   │           ├─ 拆为多条信号               → 复制到 To-Process/ 拆分
   │           └─ 进入下游处理               → status=triaged
   ▼
[Draft]        wiki-writer / repo-researcher 生成中文草稿
   │           落到 Wiki-Drafts/ 或 60-Repo-Research/reports/
   │           status=drafting
   ▼
[Publish]      润色 + 双链补全 → 入 10-Hermes-Wiki/ 对应 Phase 目录
   │           或入 60-Repo-Research/ 终稿
   │           status=published
   ▼
[Archive]      原始 capture 移到对应目录的 _archive/ 子目录
               status=archived
```

---

## 五、Phase 路由规则

读到一条新素材时，按下列优先级决定它属于哪个 Phase：

1. **front-matter `phase` 字段** 显式指定 → 以它为准。
2. 命中关键词字典（`50-Intelligence/pipelines/keywords.yaml`）：
   - `phase=2`：B2B、包装、印刷、Jinguan、独立站、外贸、SEO、Shopify、SKU…
   - `phase=3`：Binance、Bybit、合约、永续、链上、meme、A股、美股、KOL…
   - `phase=4`：Polymarket、Kalshi、prediction、event contract…
   - `phase=1`：infra、监控、MCP、Claude Code、Hermes、Obsidian、agent…
3. 都不命中 → 留 `phase: null`，进 `To-Process/` 等人工分诊。

---

## 六、自动化与人工的边界

| 操作 | 谁来做 |
|---|---|
| 抓取 + 写入 Capture | `50-Intelligence/community-bridges/` 各 bridge |
| Triage 初判（打 phase / tags） | `intel-summarizer` agent，给出建议 |
| Triage 终审 | **人工**（高价值素材必须人审） |
| 草稿生成 | `wiki-writer` / `repo-researcher` |
| 入库前最终润色 | **人工**（保证语气 / 双链 / 结论） |
| 归档 | 脚本（status=published 后 7 天自动移走原件） |

---

## 七、洪水防御

- 单一来源（如某个高频链上 bot）每日入箱 **> 200 条** 时，bridge 自动转入"摘要模式"：仅写一条 `daily-digest` 文件，原始消息存压缩归档。
- `00-Inbox/` 总文件数 **> 1000** 时触发告警（飞书），强制人工清理。
- 任意 capture 在 `status=new` 停留 **> 14 天** → 自动降级 `priority=3`，**> 30 天** → 自动 archive 并写入 `_archive/auto-expired/`。

---

## 八、不要做的事

- ❌ 不要直接在 `00-Inbox/` 编辑成最终笔记。Inbox 是流水线入口，不是知识沉淀地。
- ❌ 不要在 `Wiki-Drafts/` 放原始 capture（应放在对应 source 子目录）。
- ❌ 不要让任何 bridge 跳过 front-matter（无 front-matter 的文件视为格式错误）。
- ❌ 不要把交易决策直接基于 Inbox 内容 —— 必须先经 `Phase 3` 策略层结构化处理。

---

## 九、待补全（TODO）

- [ ] `50-Intelligence/pipelines/keywords.yaml` 关键词字典初稿
- [ ] `intel-summarizer` agent 的 system prompt（中文）
- [ ] 自动归档脚本（按 status + 时间）
- [ ] `00-Inbox/_dashboard.md`：用 Dataview 显示当前各 status 数量
