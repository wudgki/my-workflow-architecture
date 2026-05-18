# AI-Workspace 架构蓝图

> 本仓库是 **`D:\AI-Workspace`** 的**架构蓝图**（只放骨架与文档，不放业务代码与笔记内容）。
> 真实数据（Obsidian Wiki、各 Phase 项目、Hermes 服务等）在主电脑 / 副电脑 / VPS 各自落地，参照本仓库的目录约定来组织。

- 主用户：Samuel Wu
- AI 协作伙伴：ChatGPT（架构 / 决策） + Claude Code（代码 / Agent 执行）
- 主要工作语言：**中文**（Repo-Researcher / Wiki 草稿等所有工作流默认中文输出）

---

## 一、三轴模型

整个工作空间由 **三条交叉的轴** 组织起来，目录结构是这三条轴的投影：

| 轴 | 含义 | 表现形式 |
|---|---|---|
| **业务轴 Phase** | Phase 1 基建/情报 → Phase 2 B2B 包装 → Phase 3 Crypto 量化 → Phase 4 预测市场 | 在 Wiki / 项目代码 / 情报管道 内部分子目录 |
| **能力轴 角色** | 知识库（Obsidian）/ 代码（Claude Code）/ 服务运行时（Hermes-VPS）/ 情报（Intel） | 顶层一级目录 |
| **流转轴 生命周期** | Inbox 原始 → 待处理 → 草稿 → 入库/上线 → 归档 | `00-Inbox/` 与各处的 `Archive/` |

设计原则：**顶层按角色 + 内部按 Phase + 全局共用 Inbox / Ops**。

---

## 二、Phase 总览

| Phase | 状态 | 主题 | 主要落地目录 |
|---|---|---|---|
| Phase 1 | 已完成基础 | 基建 + 泛 AI / GitHub / 投资情报监控 | `50-Intelligence/`、`10-Hermes-Wiki/10-Phase1-Infra-Intel/` |
| Phase 2 | 进行中 | 海外 B2B 网络印刷包装平台（与 Jinguan 海外独立站融合） | `30-Phases/phase2-b2b-platform/`、`10-Hermes-Wiki/20-Phase2-B2B-Platform/` |
| Phase 3 | 规划中 | AI 驱动的 Crypto 量化（合约 + meme + A股 / 美股共置） | `30-Phases/phase3-crypto-quant/`、`10-Hermes-Wiki/30-Phase3-Crypto-Quant/` |
| Phase 4 | 规划中 | Polymarket / Kalshi 预测市场自动化交易 | `30-Phases/phase4-prediction-market/`、`10-Hermes-Wiki/40-Phase4-Prediction-Market/` |

> Phase 3 内部 A股 / 美股 暂与 Crypto 共置但**子目录硬隔离**，将来抽离为独立 Phase 时整目录搬走即可。

---

## 三、顶层目录速查

```
AI-Workspace/
├── 00-Inbox/                # 全局异步流转入口（Discord/Telegram/Feishu/Web/Repo Captures）
├── 10-Hermes-Wiki/          # Obsidian 知识库（中文为主，含 .obsidian 配置）
├── 20-Claude-Code/          # Claude Code 共用资产（agents/commands/skills/mcp-servers/prompts）
├── 30-Phases/               # 各 Phase 的可执行项目代码
├── 40-Hermes-VPS/           # Hermes 服务层（VPS 现役，可迁副机）
├── 50-Intelligence/         # 情报管道（输出统一打到 00-Inbox）
├── 60-Repo-Research/        # 仓库分析中文产物
├── 70-Sandbox/              # 实验 / 原型（短命）
├── 90-Ops/                  # 双机协作 / 同步 / 密钥
└── README.md
```

每个目录下都有一个 `_about.md`，说明其用途、子结构和与其他目录的关系。

---

## 四、关键流程文档

| 文档 | 位置 | 作用 |
|---|---|---|
| 收件箱处理规则 | [`00-Inbox/Inbox-Processing-Rules.md`](./00-Inbox/Inbox-Processing-Rules.md) | 定义入箱 → 待处理 → 草稿 → 入库的流转规则 |
| 多机协作协议 | [`90-Ops/multi-machine-protocol.md`](./90-Ops/multi-machine-protocol.md) | 主机 / 副机 / VPS 三方的写入权 / 同步 / 冲突约定 |
| Hermes 迁移手册 | [`40-Hermes-VPS/runbook/migration-vps-to-local.md`](./40-Hermes-VPS/runbook/migration-vps-to-local.md) | Hermes 从 VPS 迁回本地副机的 SOP |

---

## 五、命名与排序约定

- 顶层目录使用 `两位数字 + 短横 + 英文名` 前缀（如 `10-Hermes-Wiki`）保证文件管理器排序稳定。
- Wiki 内一级目录同样使用 `10-/20-/30-/...` 前缀。
- 工作产物（仓库分析报告、周报）统一文件名 `YYYY-MM-DD-<topic>.md`。
- 中文笔记标题中可以含中文，但**目录名一律 ASCII**，避免跨平台同步问题。

---

## 六、如何把蓝图落到本机

```bash
# 主电脑 / 副电脑首次落地
git clone https://github.com/wudgki/my-workflow-architecture.git D:/AI-Workspace-Blueprint
# 然后参照 _about.md 在 D:\AI-Workspace 下手动建好真实业务目录
```

蓝图仓库 **只跟踪结构和文档**，业务数据由各机本地保管，参见 `90-Ops/multi-machine-protocol.md`。
