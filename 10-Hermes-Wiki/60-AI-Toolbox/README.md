---
title: Hermes 60-AI-Toolbox
phase: 60-AI-Toolbox
status: living-doc
last_updated: 2026-05-21
---

# Hermes 60-AI-Toolbox

> **AI 基础设施层**。本目录不直接产生业务价值，而是为 Phase 3 (Crypto-Quant)、Phase 4 (Prediction Market)、Phase 6 (Personal-OS) 提供可复用的能力。

---

## 1. 这是什么

60-AI-Toolbox 是 Hermes 项目的**横切基础设施**，包含：

- LLM 调用统一封装（`llm_client.py` 抽象）
- Agent runtime（先 n8n 起步，必要时升级 Python）
- 工具注册与 memory 机制
- 提示词版本管理
- 向量索引（如需要）
- 多 LLM 路由 / 成本控制

**一句话定位**：所有"AI 用法选择"的决策都落在这里，所有 Phase 都从这里取用工具。

---

## 2. 启动时机（三档增量）

60-Toolbox 不是一次启动整块，**拆成 3 个增量**，按需推进。

### v0 — 研究 Agent 原型（轻）

| 项 | 内容 |
|---|---|
| 范围 | n8n AI Agent 节点 + 4 个工具 + 1 个研究任务（见 §4） |
| 启动条件 | Phase 1 PR #30–#33 **全部合并部署** + captures 链路稳定 ≥ 2 周 + `hermes-n8n` 容器就绪 |
| 工作方式 | **单独开 60-Toolbox 窗口**（不在 Phase 1 窗口里做） |
| 与其他 Phase 关系 | 与 Phase 1 收尾后维护、Phase 2 B2B 窗口、Phase 4 研究窗口**并行** |
| 月成本提升 | DeepSeek 预算从 \$5 → \$10 |
| 验收 | 研究 agent 跑通：给定 token symbol → 输出带来源链接的研究 wiki |

### v1 — Infra 决策（中）

| 项 | 内容 |
|---|---|
| 范围 | prompt-versioning / memory 策略 / 第二个 agent（新闻研判 / 竞品分析等） |
| 启动条件 | v0 稳定运行 ≥ 1 个月，月调用 ≥ 30 次 |
| 工作方式 | 同 60-Toolbox 窗口继续 |
| 验收 | `prompt-versioning.md` + `memory-strategy.md` + `cost-budget.md` 落地；第二个 agent 跑通 |
| **Phase 3 / Phase 4 实盘前置** | ✅ **v1 必须就位** |

### v2 — Python 生产 Runtime（重）

| 项 | 内容 |
|---|---|
| 范围 | LangGraph 或自写 runtime；向量库；多 LLM 路由 |
| 启动条件 | n8n AI Agent 出现明确瓶颈，对照 `工具选型.md` §11 触发条件 |
| 工作方式 | 单独 PR 集，可能跨多个窗口 |
| 验收 | Phase 3 / Phase 4 / Phase 6 中任一高频 agent 切到 Python runtime |

**反过来说**：

- Phase 4 / Phase 3 的**研究阶段**只需 v0 就够（甚至 v0 之前也可以做纯纸面研究）
- Phase 4 / Phase 3 的**实盘 / 资金交互**必须等 **v1 就位**
- v2 是**按需升级**，不是必经之路

---

## 3. 不包含什么

- ❌ 具体的 crypto 交易策略 → Phase 3
- ❌ 具体的赔率分析模型 → Phase 4
- ❌ B2B 客户管理 → Phase 2
- ❌ 个人邮件分流规则 → Phase 6
- ❌ 平台 ingestor 实现（Reddit / TikTok / ...）→ Phase 1 的 bridge 体系，规范见 `平台扩展模式.md`

60-Toolbox 只放**通用能力**。业务策略一律放回各自 Phase。

---

## 4. v0 第一个验证任务：研究 Agent

启动 v0 后第一件事不是搭一堆基础设施，而是**用最简陋的方式跑通一个 agent**：

- **输入**：一个 token symbol（例如 `SOL`）
- **实现**：
  - n8n AI Agent 节点 + DeepSeek
  - tool 1：读 captures（把 Phase 1 的 `capture_loader` 包成 n8n workflow）
  - tool 2：查 CoinGecko 价格
  - tool 3：查链上数据（任选一家 API）
  - tool 4：写 wiki markdown
- **输出**：一篇带来源链接的中文研究 markdown，落到 `10-Hermes-Wiki/30-Phase3-Crypto-Quant/Onchain-Intel/`

**这个任务同时验证 4 件事**：

1. agent runtime 选型（n8n AI Agent 是否够用）
2. 工具注册机制
3. 与 Phase 1 captures 的接驳契约
4. DeepSeek 在多轮工具调用下的稳定性

**v0 → v1 的入口**：稳定运行 ≥ 1 个月、月调用 ≥ 30 次。频次不到说明 agent 设计本身有问题，**先迭代 v0 而不是上 v1**。

---

## 5. 前置依赖（来自 Phase 1）

| 产物 | 路径 | 60-Toolbox 何时使用 |
|---|---|---|
| `llm_client.py` | `50-Intelligence/pipelines/digest/` | runtime 直接复用 |
| `capture_loader.py` | 同上 | 包装成 agent tool |
| captures 元数据规范 | 见 `平台扩展模式.md` §3 | 研究 agent 检索基础 |
| n8n 部署 | VPS `hermes-n8n` 容器 | agent 原型 host |
| Prompt 目录约定 | `50-Intelligence/prompts/{task}/v{N}.md` | agent 系统提示版本管理 |

**如果 Phase 1 这些产物不稳定，不要启动 v0**。

---

## 6. 文档索引

| 文档 | 主题 | 状态 |
|---|---|---|
| `README.md`（本文件） | 入口 / v0/v1/v2 启动条件 / 与各 Phase 关系 | ✅ |
| `工具选型.md` | Python / n8n / Agent 各自的边界与决策矩阵 | ✅ |
| `平台扩展模式.md` | 新数据源（Reddit / LinkedIn / TikTok / ...）接入规范 | ✅ |
| `已知坑.md` | 教训累积模板（先建空模板，持续累积） | ⏳ v0 启动时建 |
| `prompt-versioning.md` | Prompt 目录、版本号、A/B 切换规范 | ⏳ **v1 启动时**写 |
| `memory-strategy.md` | agent 短期 / 长期 memory 选型 | ⏳ **v1 启动时**写 |
| `cost-budget.md` | 月度成本监控与告警（**Phase 3 / Phase 4 实盘前必须**） | ⏳ **v1 启动时**写 |
| `vector-store-选型.md` | chroma / pgvector / qdrant 选型 | ⏳ 真正需要向量检索时写 |
| `runtime-升级评估.md` | 何时从 n8n 升到 LangGraph / 自写 | ⏳ **v2 启动时**写 |

---

## 7. 与各 Phase 的关系图

```
            Phase 1 情报基建 (pipelines)
                       │
                       │ 提供 llm_client / captures 规范 / n8n 容器
                       ▼
       60-AI-Toolbox v0 ──► v1 ──► v2（按需）
                  │          │
                  │          │ v1 实盘前置
       ┌──────────┴──────────┼─────────────────┐
       │                     │                 │
       ▼ (研究阶段够)         ▼ (实盘必须)       ▼
  Phase 4 研究          Phase 3 / Phase 4   Phase 6
  Phase 3 调研           实盘                Personal-OS
```

60-Toolbox **不写业务策略**，业务策略一律落到各自 Phase 目录。

---

## 8. 启动 checklist

### 8.1 v0 启动 checklist（开 60-Toolbox 窗口前必须勾完）

- [ ] Phase 1 PR #30–#33 全部合并并部署
- [ ] captures 链路稳定运行 ≥ 2 周（VPS 上 `find /data/inbox/Telegram-Captures -mmin -30 | wc -l` 持续 > 0）
- [ ] `hermes-n8n` 容器在 VPS 部署完成 + reverse proxy + auth 配齐
- [ ] DeepSeek API 月预算上调至 \$10（从 Phase 1 的 \$5）
- [ ] 决定研究 agent v0 的 4 个工具（captures / 价格 / 链上 / 写 wiki）
- [ ] `工具选型.md` ✅ 已就位
- [ ] `平台扩展模式.md` ✅ 已就位
- [ ] `90-Ops/n8n-workflows/` 目录建好（用于 workflow JSON 版本管理）
- [ ] `60-AI-Toolbox/已知坑.md` 空模板建好

### 8.2 v0 → v1 进入条件

- [ ] v0 研究 agent 稳定运行 ≥ 1 个月
- [ ] 月调用次数 ≥ 30 次（频次不到先迭代 v0，不上 v1）
- [ ] v0 阶段累计成本未超 \$10/月（超了先优化再上 v1）
- [ ] 至少一份 v0 输出的研究 wiki 你看完觉得"有用"

### 8.3 v1 启动 checklist

- [ ] DeepSeek 月预算上调至 \$20–30
- [ ] `prompt-versioning.md` 写完
- [ ] `memory-strategy.md` 写完
- [ ] `cost-budget.md` 写完（Phase 3 / Phase 4 实盘前置）
- [ ] 第二个 agent 设计完成（建议"新闻研判 agent"或"竞品分析 agent"）
- [ ] n8n executions 失败率 < 5%

### 8.4 v2 触发条件（不是 checklist，是触发器）

参见 `工具选型.md` §11。出现以下**任一**情况启动 v2：

- 单次 agent 调用 > 90 秒
- 单 agent 工具数 > 8
- 需要并发 > 5 个 agent 实例
- n8n executions 失败率 > 10% 且无法 debug
- 需要 streaming 输出 / 严格 JSON schema

---

## 9. 修订历史

| 日期 | 修订人 | 内容 |
|---|---|---|
| 2026-05-21 | 初始版本 | 确立 60-AI-Toolbox 定位、启动条件、第一个验证任务 |
| 2026-05-21 | v0/v1/v2 拆分 | 把 60-Toolbox 拆成 3 个增量；明确 v0 与 Phase 1 收尾后维护 / Phase 2 / Phase 4 并行；**v1 是 Phase 3 / Phase 4 实盘前置**；v2 按需升级 |
