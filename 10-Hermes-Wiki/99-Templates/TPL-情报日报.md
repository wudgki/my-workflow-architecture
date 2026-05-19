---
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 模板：情报日报 / 情报周报（中文）
# 使用方：intel-summarizer agent / 人工
# 产出落地：
#   日报：10-Hermes-Wiki/<Phase>/Daily-Digest/YYYY-MM-DD.md
#   周报：10-Hermes-Wiki/<Phase>/Weekly-Digest/YYYY-Www.md
# 数据源：00-Inbox/{Discord,Telegram,Feishu,Web,Repo}-Captures/
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
title: "{{Phase 名}} 情报简报 {{YYYY-MM-DD 或 YYYY-Www}}"
date: {{YYYY-MM-DD}}
phase: {{1|2|3|4}}
window: daily            # daily | weekly | custom
window_start: {{YYYY-MM-DD}}
window_end: {{YYYY-MM-DD}}
captures_total: {{int}}        # 时间窗口内总入箱条数
captures_after_dedup: {{int}}  # 去重后保留条数
status: published
tags: [情报, daily, phase{{N}}]
---

# {{Phase 名}} 情报简报 {{YYYY-MM-DD 或 YYYY-Www}}

> 时间窗口：{{窗口起}} ~ {{窗口止}}
> 入箱总数：{{captures_total}} → 去重后：{{captures_after_dedup}}
> 来源分布：Discord {{n}} / Telegram {{n}} / Feishu {{n}} / Web {{n}} / Repo {{n}}

---

## 一、TL;DR（3-5 行）

<!-- 整个时间窗口最值得关注的 3-5 件事，每条不超过 25 字，按重要性排序 -->

- {{要点 1}}
- {{要点 2}}
- {{要点 3}}

---

## 二、P0 高优先级

> 明确交易信号 / 监管动作 / 安全事件 / 关键人物表态 / 社区告警

| 时间 | 来源 | 摘要 | 行动建议 | 原始 capture |
|---|---|---|---|---|
| {{HH:MM}} | {{telegram-channel-x}} | {{一句话摘要}} | {{跟进 / 等确认 / 已处理}} | [[{{YYYY-MM-DD_telegram_xxx}}]] |
| | | | | |

---

## 三、P1 中优先级

> 研究报告 / 新项目预告 / KOL 重要观点

### 主题 A：{{主题名}}

- {{一句话观点}} — 来自 [[{{capture-id}}]]
- {{一句话观点}} — 来自 [[{{capture-id}}]]

### 主题 B：{{主题名}}

- {{一句话观点}} — 来自 [[{{capture-id}}]]

### 主题 C：{{主题名（可选）}}

- {{一句话观点}} — 来自 [[{{capture-id}}]]

---

## 四、P2 低优先级（仅列数）

<!-- 不引用具体内容，只数总数；防止简报被噪声淹没 -->

- {{discord-channel-x}}：{{n}} 条普通讨论
- {{telegram-group-y}}：{{n}} 条转发
- {{feishu-bridge-z}}：{{n}} 条提示
- {{web-clips}}：{{n}} 条剪藏

---

## 五、关键人物 / 项目 提及次数（可选）

> 仅在窗口内被提到 ≥ 3 次时列出

| 实体 | 提及次数 | 类型 | 主要事件 |
|---|---|---|---|
| {{KOL/项目/币种}} | {{n}} | KOL/项目/资产 | {{一句话}} |

---

## 六、跟进清单

<!-- 在简报里 P0 / P1 中需要后续动作的事项，由人工或下游 agent 处理 -->

- [ ] {{动作}} - 关联 [[{{capture-id}}]] - 期望完成日 {{YYYY-MM-DD}}
- [ ] {{动作}}
- [ ] {{动作}}

---

## 七、原始 capture 索引

> 全部已纳入本简报的 capture（按时间倒序），便于追溯

- [[{{YYYY-MM-DD_source_topic-1}}]]
- [[{{YYYY-MM-DD_source_topic-2}}]]
- [[{{YYYY-MM-DD_source_topic-3}}]]

---

## 八、洪水降级（如触发）

<!-- 单一来源 24h 内 > 200 条时，bridge 自动转入摘要模式；本节记录哪些来源被降级 -->

- {{source}}：原始 {{n}} 条 → 仅生成 daily-digest，未逐条引用
  详细见 [[{{source}}-{{YYYY-MM-DD}}-bulk]]

---

<!--
使用提示：
1. 文件名约定：
   - 日报：YYYY-MM-DD.md（如 2026-05-19.md）
   - 周报：YYYY-Www.md（如 2026-W21.md）
2. 落地路径按 Phase 拆分（每个 Phase 一份独立简报，不要把 Phase 1-4 混写）：
     10-Hermes-Wiki/10-Phase1-Infra-Intel/Daily-Digest/
     10-Hermes-Wiki/20-Phase2-B2B-Platform/Daily-Digest/
     10-Hermes-Wiki/30-Phase3-Crypto-Quant/Daily-Digest/
     10-Hermes-Wiki/40-Phase4-Prediction-Market/Daily-Digest/
3. front-matter 中：
   - phase 必须是数字（1/2/3/4），不要带引号
   - status 直接写 published（简报是事实压缩，不是草稿）
   - captures_total / captures_after_dedup 必填，便于脚本观察 Inbox 健康度
4. 严禁在简报里写"该买入 / 该清仓 / 该开仓"等指令性文字。
   即使引用 KOL 喊单，也只能写"X 在 HH:MM 喊 BTC 多 / 空"，不带主观结论。
5. 周报 = 同结构，但 window=weekly，时间窗口跨 7 天；
   "P0 高优先级"建议改为"本周关键事件 5-10 条"。
6. 写完本简报后，请把所有被引用的 capture 文件 status 改为 triaged，
   并在 capture 顶部加 `> [简报已引用 - <本简报路径>]`。
-->
