# 50-Intelligence · 情报管道

把外部世界的信号 → 抓取 / 聚合 / 清洗 → 投递到 `00-Inbox/` 或直接推 Hermes Webhook。

## 子目录

| 目录 | 监控对象 |
|---|---|
| `github-watch/` | GitHub 仓库 / Trending / Star 监控 |
| `crypto-watch/` | 加密货币 KOL / 链上玩家 / 现货合约博主 |
| `stock-watch/` | A股 / 美股博主 |
| `macro-watch/` | 海外英文交易员 / 宏观博主 |
| `prediction-watch/` | Polymarket / Kalshi 市场监控 |
| `community-bridges/` | Discord / Telegram / 飞书 桥接器（统一封装） |
| `pipelines/` | ETL / 调度 / 去重 / 摘要 |

## 数据流

```
[外部源] → community-bridges/ → pipelines/ → 00-Inbox/{source}-Captures/
                                          ↘ Hermes Webhook（高优信号直推）
                                          ↘ Phase 3 策略（结构化信号）
```

## 设计约束

- 所有 bridge 输出 **统一 schema**（来源、时间、原文、标签、初步打分）。
- 高频源（链上）必须做 **去重 + 限流**，避免 Inbox 洪水。
- 任何 bridge 必须支持 **dry-run** 模式（不实际写入），方便联调。
