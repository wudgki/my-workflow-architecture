# 10-Hermes-Wiki · Obsidian 知识库

主电脑 / 副电脑共同维护的 Obsidian Vault，**中文为主**。Hermes（VPS）只读消费这个 Wiki 来生成情报与 Agent 上下文。

## 顶层结构

| 目录 | 用途 |
|---|---|
| `00-Map-of-Content/` | MOC 总入口，按 Phase 分页索引 |
| `10-Phase1-Infra-Intel/` | 基建 + 情报监控笔记 |
| `20-Phase2-B2B-Platform/` | 海外 B2B 包装平台（含 Jinguan 融合） |
| `30-Phase3-Crypto-Quant/` | Crypto 量化（合约 + meme + A股 / 美股） |
| `40-Phase4-Prediction-Market/` | Polymarket / Kalshi |
| `50-Repo-Research/` | 仓库分析中文报告（在 Wiki 内的入口） |
| `60-AI-Toolbox/` | MCP / Playwright / Skills 工具笔记 |
| `70-Personal-OS/` | Startup OS / 个人方法论 |
| `90-Archive/` | 归档 |
| `99-Templates/` | 模板（仓库分析、周报、Phase 模板） |
| `_attachments/` | 附件（图片 / PDF） |
| `.obsidian/` | Obsidian 配置（参与同步，但 `workspace*` 文件本地化） |

## Phase 2 内部

```
20-Phase2-B2B-Platform/
├── Jinguan-Brand/           # 家族企业 Guangdong Jinguan 品牌资产 / 背书素材
├── Product-Catalog/         # 产品 / SKU / 工艺
├── Marketing-Playbook/      # 外贸获客打法
├── Tech-Architecture/       # 平台技术架构笔记
├── Integration-Plan/        # Jinguan 海外独立站 ↔ Overseas 平台 融合方案
└── Competitor-Research/
```

## Phase 3 内部

```
30-Phase3-Crypto-Quant/
├── Strategy-Notes/
├── KOL-Tracking/            # 加密货币 KOL / 链上 / 现货合约博主
├── Onchain-Intel/           # 链上一级市场 / 监控
├── Macro-Notes/             # 海外英文交易员 / 宏观博主
├── AStock-USStock/          # A股 / 美股板块（同 Phase 内隔离）
└── Risk-Management/
```

## 与其他角色的关系

- **输入**：来自 `00-Inbox/Wiki-Drafts/`、`60-Repo-Research/reports/` 的成品。
- **被读取**：`20-Claude-Code/` 的 Agent / Skill 把 Wiki 作为上下文；`50-Intelligence/` 的 pipeline 写回相关页。
- **不放代码**：所有可执行代码归 `30-Phases/`、`40-Hermes-VPS/`、`50-Intelligence/`，Wiki 只放笔记 / 文档 / 决策记录。
