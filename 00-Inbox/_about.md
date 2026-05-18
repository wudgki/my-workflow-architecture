# 00-Inbox · 全局异步流转入口

所有外部输入（社区消息、Web 剪藏、仓库抓取、灵感速记）都先落到这里，再由人工或 Agent 流转到下游。

## 子目录

| 子目录 | 输入来源 | 流转去向 |
|---|---|---|
| `Discord-Captures/` | Discord 频道（金融社区 / KOL / 项目方） | `Wiki-Drafts/` 或 `30-Phase3-.../KOL-Tracking` |
| `Telegram-Captures/` | Telegram 群组 / 频道 | 同上 |
| `Feishu-Captures/` | 飞书推送（社区聚合） | 同上 |
| `Web-Clips/` | r.jina.ai / mcp-chrome / Playwright 抓取的网页 | `Wiki-Drafts/`、`60-Repo-Research/` |
| `Repo-Captures/` | GitHub 仓库原始抓取（README / 关键文件） | `60-Repo-Research/reports/` |
| `To-Process/` | 任意未分类的临时输入 | 任一终点 |
| `Wiki-Drafts/` | 待入 Wiki 的中文草稿 | `10-Hermes-Wiki/` |

## 处理规则

入箱处理的完整 SOP 见 [`Inbox-Processing-Rules.md`](./Inbox-Processing-Rules.md)。

## 命名约定

```
YYYY-MM-DD_<source>_<short-topic>.md
例：2026-05-18_telegram_kol-bigshort-call.md
```
