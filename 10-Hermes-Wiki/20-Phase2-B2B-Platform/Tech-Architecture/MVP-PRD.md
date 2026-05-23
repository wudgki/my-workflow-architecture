---
title: 海外 B2B 包装平台 · MVP PRD v0.1
phase: 2
status: drafting
captured_at: 2026-05-23
owner: samuel
tags: [phase-2, b2b, packaging, mvp, prd, ai-agent]
related:
  - "[[Jinguan-Brand/_index]]"
  - "[[Product-Catalog/_index]]"
  - "[[Integration-Plan/_index]]"
  - "[[Competitor-Research/_index]]"
---

# 海外 B2B 包装平台 · MVP PRD v0.1

> 本文档定义海外 B2B 网络印刷包装平台首版（12 个月）的产品需求。
> 战略定位锚点：**AI-native 跨境品牌包装供应链平台**（方案 A） + **防伪/数字化包装**（方案 C）作为差异化壁垒与 VC 故事点。

---

## 0. 文档元信息

| 字段 | 内容 |
|---|---|
| 版本 | v0.1（草案） |
| 适用阶段 | Phase 2 · Overseas B2B Platform |
| 关联战略 | 见上层战略备忘录（待补 link） |
| 关联实体 | Guangdong Jinguan（品牌背书 + 高端订单承接）、fenxiangyin.com（国内母平台 / 复用资产）、jinguanpack.com（已有 Lovable 简版独立站，将作为流量与 SEO 资产） |
| 主决策者 | Samuel |
| 评审节奏 | 每 2 周一次 |

---

## 1. 战略锚点（Recap）

- **目标客户**：欧美 / 中东 Shopify、Shopline、TikTok Shop 上 GMV \$50K–\$5M 的 DTC / 跨境电商品牌方。次级客户：海外中小型分销商。
- **核心价值主张**：
  1. AI 30 秒出 3 套包装设计稿（含刀版图）
  2. 实时报价 + 低 MOQ（100–500 起订）
  3. 中国制造 + 区域 buffer 仓
  4. 复杂 / 高端 / 防伪订单 → 金冠线下白手套通道
- **差异化壁垒**：防伪与数字化包装（NFC / 隐性二维码 / 开箱数据），把包装从"成本项"变"营销项"。
- **不做什么**：不做大宗 commodity 纸箱、不做工业级 B2B 撮合（让 1688 去做）、不做纯设计 SaaS（让 Pacdora 去做）。

---

## 2. MVP 范围

### 2.1 In Scope（首发 12 个月）

| 类别 | 范围 |
|---|---|
| **品类** | 5 个核心 SKU 大类：折叠彩盒 / 瓦楞坑盒 / 手提袋 / 标签贴纸 / 信封袋（**首批先上 2 个：折叠彩盒 + 瓦楞坑盒**） |
| **市场** | 首发**美国**单一市场（理由见 §13）；M9 起评估开放欧盟 |
| **语言** | 英文为主，配 ES / DE 作为 SEO 长尾覆盖（非完整 i18n） |
| **支付** | Stripe（卡 / ACH / Apple Pay） + PayPal |
| **物流** | 海运拼箱 + 美西海外仓 + UPS/FedEx 末端派送；DDP 报价 |
| **AI Agent** | Design / Quoting / Compliance 三个 Agent 上 MVP；Sourcing / Anti-counterfeit / Sustainability 三个进 V1.5 |
| **运营后台** | 订单分流（金冠 vs 第三方 OEM）、生产看板、QC 看板、客服工单 |

### 2.2 Out of Scope（明确不做）

- ❌ 多币种结算（首版只 USD）
- ❌ 用户自营店铺 / 多卖家 marketplace 模式（首版只做 1P + 集中分单）
- ❌ 设计师 freelancer marketplace
- ❌ 信用账期 / Net30（首版全款预付，避免坏账）
- ❌ 移动 App（响应式 Web 即可）
- ❌ 中文界面（避免被定位为"中国货平台"）

---

## 3. 用户画像

### Persona 1 · DTC Brand Founder（主力，70% 流量）
- **画像**：30–45 岁，Shopify 月 GMV \$50K–\$1M，团队 1–10 人
- **场景**：上一批包装快卖完 / 要发新品 / 想升级品牌包装
- **痛点**：找不到能做小批量定制的工厂；设计来回沟通 2 周；样品慢；质量不稳定；不懂海运报关
- **触达渠道**：Google "custom mailer box" / Reddit r/Entrepreneur / TikTok #packaginginspo / LinkedIn ABM

### Persona 2 · Cross-border Operator（25%）
- **画像**：跨境电商运营经理，管 5–20 个 SKU，亚马逊 / 独立站为主
- **场景**：要换 FBA-ready 包装 / 要做品牌升级 / 旺季备货
- **痛点**：1688 找工厂沟通成本高；缺英文报价 + 合同；FBA 合规要求复杂

### Persona 3 · Distributor / Reseller（5%，非主推但接单）
- **画像**：本地（美西 / 欧洲 / 中东）小型批发商，给区域品牌 / 烘焙坊 / 餐饮供货
- **场景**：批量囤货，对价格敏感
- **MVP 处理**：发现注册 → 转人工销售跟进，不做自助下单

---

## 4. 核心用户旅程

```
Discovery → Configure → AI-Quote → AI-Design → Sample → Order → Production → Delivery → Reorder
   │           │           │           │          │        │        │            │          │
   SEO/Ads    在线选品    实时报价    AI出稿     寄样品   下单     生产看板     物流追踪   一键复购
   (5-10min) (3-5min)   (instant)  (30s × 3)  (3-5d)  (5min)   (15-25d)     (real-time)
```

**关键转化漏斗目标（M6 末）：**
- Visit → Quote 提交：**3%**
- Quote → 寄样：**25%**
- 寄样 → 首单：**40%**
- 首单 → 6 个月内复购：**35%**

---

## 5. 功能模块

### 5.1 买家端（Web，响应式）

#### 5.1.1 公共层
- 多语言 SEO 落地页（按 SKU × 行业 × 用例 矩阵生成，目标 200+ 落地页）
- 博客 / 案例（行业内容营销）
- 注册 / 登录（邮箱 + Google + Apple）
- 多用户 Workspace（一个品牌方多个成员）

#### 5.1.2 产品配置器（Configurator）
- 选品类 → 选规格（尺寸 / 材质 / 工艺 / 印刷面 / 数量）
- **3D 实时预览**（Three.js / react-three-fiber）
- 工艺组合校验（如：可降解材料 + 烫金 = 不兼容 → 提示替代）
- 每一步实时联动报价（见 5.3.2）

#### 5.1.3 设计工作台（Design Studio）
- 上传 Logo / 品牌资料 → AI 30 秒生成 3 版设计稿（见 5.3.1）
- 在线编辑器（Fabric.js）：换字体、调色、替换元素
- 上传成稿（AI / PDF / PSD）→ 自动 prepress 检查（出血、分辨率、CMYK）
- 协作评论（多人在稿件上 pin 批注）
- 版本历史

#### 5.1.4 报价 / 询单（Quote / RFQ）
- 标准 SKU：实时秒级报价（无需人工）
- 非标 SKU / 复杂工艺：转 RFQ 工单，AI 初判 + 人工 24h 内回复
- 报价单可下载 PDF，可一键转下单

#### 5.1.5 样品订购
- 5 美元 / 套样品（首单冲抵）
- 3–5 天到达美国地址
- 可寄已上传设计稿的实物样

#### 5.1.6 下单 & 支付
- Stripe Checkout（卡 / ACH / Apple Pay / Google Pay）
- PayPal
- DDP 全包价（含关税 / 物流 / 末端派送）
- 订单确认 PDF + 数字签署生产授权（DocuSign 嵌入）

#### 5.1.7 订单管理
- 生产进度时间轴（10–15 步骤可视化：审稿 → 制版 → 印刷 → 模切 → 糊盒 → QC → 装箱 → 海运 → 入仓 → 派送）
- 关键节点照片 / 视频回传（与 OEM 工厂 ERP 对接）
- 物流追踪（UPS / FedEx / DHL API）
- 一键复购（保留所有规格与设计）

### 5.2 运营端（Internal Ops Console）

#### 5.2.1 订单中央调度（Order Routing）
- 自动判定订单类型：
  - **标品 / 常规** → 路由给第三方 OEM 工厂网络（按价格、产能、地理位置打分）
  - **高端 / 防伪 / 复杂工艺 / 大客户** → 路由给金冠自有产线
  - **MVP 阶段**：可手动覆盖路由结果
- 与各工厂 ERP 对接（首版只对接金冠 ERP 和 fenxiangyin 的合作工厂池，复用国内资源）

#### 5.2.2 生产看板
- 工厂端 / 我方运营端双视图
- 异常告警（延期、QC fail、设计返工）

#### 5.2.3 QC 看板
- 关键节点强制照片 / 视频上传
- AI 视觉初筛（颜色偏差、毛刺、字体错位）→ 人工二审

#### 5.2.4 客服工单
- 邮件 + Web Chat（Intercom）+ WhatsApp Business
- AI 客服 Agent 兜底常见问题，复杂问题 escalate
- 每个工单与订单 / 设计稿强关联

#### 5.2.5 销售 CRM 简版
- 注册用户分层（自助下单 / 销售跟进）
- 询盘自动分配
- 复购预测（基于上一订单的耗材周期）

### 5.3 AI Agent 层（核心壁垒）

> 设计原则：每个 Agent **既能在产品里独立调用，又能组合成端到端工作流**。Agent 之间通过结构化消息传递（建议用 MCP 协议或自研事件总线）。

#### 5.3.1 Design Agent（MVP，月 1–4）
- **输入**：Logo + 品牌资料（颜色 / 调性 / 行业）+ 产品类型 + 目标受众
- **流程**：
  1. 调 Vision LLM 解析 Logo 风格
  2. 检索同行业优质包装案例（向量库）
  3. 调图像生成（建议 Imagen / Flux Pro 商用许可，避开 Midjourney 的商用模糊地带）
  4. 套用刀版图模板，输出可印刷 PDF + 3D 预览
- **输出**：3 版方向不同的设计稿（minimalist / bold / illustrated）
- **关键指标**：用户接受率 ≥ 30%（即每 10 次生成至少 3 次进入下一步）

#### 5.3.2 Quoting Agent（MVP，月 1–3）
- **输入**：自然语言或结构化参数（SKU / 尺寸 / 材质 / 工艺 / 数量 / 交期 / 目的地）
- **流程**：
  1. NLU 解析参数（可补问澄清）
  2. 调内部价格引擎（成本 + 物流 + 关税 + 毛利）
  3. 给出 3 档报价（标准 / 加急 / 经济）+ 报价依据明细
- **关键指标**：
  - 标品报价 P95 延迟 < 2s
  - 报价准确率（最终结算偏差）≤ 3%

#### 5.3.3 Compliance Agent（MVP，月 4–6）
- **输入**：目标市场 + 产品用途（食品 / 美妆 / 医药 / 一般消费品）
- **能力**：
  - 食品接触合规（FDA 21 CFR、EU 10/2011）
  - 加州 65 号警告标签
  - EU PPWR（2025 生效）可回收要求
  - 儿童产品 CPSIA / EN 71
  - 大麻类产品州法（如适用）
- **输出**：合规清单 + 必需标签元素 + 风险点
- **关键指标**：合规建议被采纳率 ≥ 60%

#### 5.3.4 Sourcing Agent（V1.5，月 5–8，先内部 ops 用）
- **输入**：订单参数 + 目标交期 + 价格上限
- **流程**：从工厂池打分 → 推荐 Top 3 → ops 确认
- **MVP 简化版**：只做金冠 + fenxiangyin 现有工厂池的二选一逻辑

#### 5.3.5 Anti-counterfeit Agent（V1.5，月 7–10，差异化重点）
- **能力**：
  - 自动叠加多层防伪元素（凹版凸版 / 微缩文字 / 隐性图案 / 一物一码）
  - 生成"开箱→扫码→品牌私域"的数据闭环 SaaS（**这是 VC 故事的核心增量**）
- **关联产品**：开箱数据看板（卖给品牌方做用户运营）

#### 5.3.6 Sustainability Agent（V1.5，月 8–10）
- **能力**：实时算碳足迹 + 替代材料推荐 + 出 ESG 报告 PDF
- **价值**：欧盟 PPWR 强制后，是品牌方刚需

#### 5.3.7 Buyer Concierge Agent（贯穿，月 3 起）
- **场景**：注册用户的 24/7 多语言销售助理
- **能力**：把上面所有 Agent 编排起来回答跨域问题（"我做猫粮 8oz 罐头的彩盒外箱，加州合规要注意什么，能不能 14 天到 LA？给我报价"）
- **底层**：建议用 LangGraph 或自研 orchestrator 做 multi-agent

---

## 6. 技术架构概览

```
┌──────────────────────────────────────────────────────────┐
│  Frontend (Next.js 14 App Router + React + Tailwind)     │
│  · Buyer Web    · Ops Console    · Design Studio (Fabric)│
│  · 3D Preview (Three.js / R3F)                            │
└──────────────────┬───────────────────────────────────────┘
                   │ tRPC / REST
┌──────────────────▼───────────────────────────────────────┐
│  Backend (Node.js + Fastify  或  Python + FastAPI)        │
│  · Auth (Clerk)                                           │
│  · Order / Quote / Catalog Service                        │
│  · Pricing Engine                                         │
│  · Agent Orchestrator (LangGraph / 自研)                  │
└──┬────────────┬───────────────┬────────────┬────────────┘
   │            │               │            │
┌──▼──┐    ┌────▼────┐    ┌─────▼─────┐ ┌────▼─────┐
│ DB  │    │ Vector  │    │ Object    │ │ Queue    │
│ PG  │    │ Qdrant  │    │ S3/R2     │ │ Redis    │
└─────┘    └─────────┘    └───────────┘ └──────────┘

外部：
· LLM: GPT-4o / Claude Sonnet 4 / Gemini 2.5 Pro（按场景路由）
· Image Gen: Imagen 3 / Flux 1.1 Pro（商用授权）
· Stripe / PayPal / DocuSign / Klaviyo / Intercom
· UPS / FedEx / DHL APIs
· 金冠 ERP / fenxiangyin 工厂池 API（需新建对接层）
```

**部署**：
- 前端：Vercel
- 后端：AWS（us-east-1，靠近主市场）/ Cloudflare Workers 边缘加速
- DB：Neon Postgres / Supabase
- 向量库：Qdrant Cloud
- 监控：Sentry + Posthog + Datadog

**安全 / 合规**：
- PCI DSS：通过 Stripe Elements，不直接接触卡号
- GDPR：欧盟用户数据落欧盟节点（M9 启用）
- CCPA：默认开启 Do-Not-Sell
- SOC2：M12 起备 Type 1（融资准备）

---

## 7. 数据模型核心实体

```
User ──< Workspace ──< Member
                  │
                  └──< Address (shipping/billing)
                  └──< PaymentMethod

Catalog: Category ──< ProductTemplate ──< Variant ──< OptionGroup

Quote ──< QuoteItem ──> ProductTemplate
   │
   └─ pricing_breakdown (jsonb)
   └─ quoted_by_agent_id

Design ──> DesignVersion ──> DesignAsset (S3)
        └─ generated_by_agent_id

Order ──< OrderItem ──> Variant + DesignVersion
   │
   ├─ routing: factory_id (Jinguan / OEM)
   ├─ production_steps (jsonb timeline)
   ├─ qc_records
   └─ shipment ──< ShipmentLeg

Factory ──< FactoryCapability ──< CapabilityScore
       └─ erp_integration_config

AgentRun: id, agent_type, input, output, latency, cost, user_id
```

---

## 8. 非功能需求

| 维度 | 目标 |
|---|---|
| 性能 | 落地页 LCP < 2s（核心市场）；报价 API P95 < 2s；3D 预览 60fps |
| 可用性 | 99.5% / 月（MVP），99.9%（M9 后） |
| i18n | 文案 i18next 全部抽出；首版 EN 完整、ES/DE 关键页 |
| 安全 | OWASP Top10 自检；所有 Agent 调用审计留痕；密钥 Vault 管理 |
| 数据 | 用户数据加密静态存储；30 天异地冷备份 |
| 可观测 | 每个 Agent 调用必须记录 input/output/cost；订单全链路 trace |
| 成本 | Agent 单订单 LLM 成本 < \$2（毛利保护线） |

---

## 9. 第三方集成清单

| 类别 | 选型 | 备注 |
|---|---|---|
| Auth | Clerk | 支持 SSO / 多 workspace 原生 |
| Payment | Stripe + PayPal | Stripe 为主 |
| 合同签署 | DocuSign Click API | 嵌入下单流程 |
| 物流 | EasyPost（聚合 UPS/FedEx/DHL） | 节省单独对接成本 |
| Email / Marketing | Klaviyo | DTC 行业事实标准 |
| Chat / 客服 | Intercom + WhatsApp Business | |
| Analytics | Posthog（自托管选项保数据） + GA4 | |
| 错误监控 | Sentry | |
| 设计 AI | Imagen 3 / Flux Pro / GPT-Image-1 | 多家 fallback |
| LLM | OpenRouter（路由 GPT/Claude/Gemini） | 避免单一厂商 |
| 向量库 | Qdrant Cloud | |
| 内部 ERP | 金冠 ERP + fenxiangyin 工厂池 | **关键对接，需新建 adapter 层** |

---

## 10. 商业逻辑

### 10.1 定价
- 标品：成本（材料 + 工艺 + 人工）× 1.4–1.8（毛利率 30–45%）
- 高端 / 防伪：金冠承接，毛利率 40–60%
- 物流 / 关税：DDP 全包透明显示

### 10.2 抽佣 / 分成
- 路由到金冠：**0%**（自家产能）
- 路由到合作 OEM：**12–18%** 平台费（已含订单管理 + QC + 物流协调）

### 10.3 订单分流规则（首版硬编码）
```
if order.is_anti_counterfeit OR order.has_complex_finishing OR order.value > $20K:
    route_to(Jinguan)
elif order.qty > 10K AND order.lead_time > 21d:
    route_to(OEM_pool, score_by=[price, capacity])
else:
    route_to(default_OEM_or_Jinguan)
```
（M9 后改为可学习的策略，喂订单结算偏差数据迭代）

---

## 11. 12 个月分阶段交付

| 月份 | 里程碑 | 关键交付 |
|---|---|---|
| **M1** | Kickoff | 团队成型、技术选型确认、设计系统 v0、域名 / 品牌 |
| **M2** | 平台骨架 | 产品目录、配置器、3D 预览、Auth、基础后台 |
| **M3** | 报价 + 下单闭环 | Quoting Agent v1、Stripe、DocuSign、Klaviyo |
| **M4** | Design Agent + 样品 | Design Agent v1、样品订购、首批 200 落地页 SEO |
| **M5** | 订单履约链路打通 | 金冠 ERP 对接、生产看板、物流 EasyPost |
| **M6** | **首批付费用户上线** | Compliance Agent v1、客服 Concierge Agent、Posthog 漏斗 |
| **M7** | 复购 & 留存 | 一键复购、Klaviyo 自动化、复购预测 |
| **M8** | OEM 池接入 + Sourcing Agent | OEM Adapter、Sourcing Agent 内部版、订单分流 v2 |
| **M9** | **防伪差异化上线** | Anti-counterfeit Agent v1、开箱数据看板 SaaS β |
| **M10** | Sustainability + 欧盟开放 | Sustainability Agent、欧盟落地页、PPWR 合规模式 |
| **M11** | 性能 + SOC2 准备 | 性能调优、安全审计、数据合规 |
| **M12** | **Pre-A 融资材料 + GMV \$1M 累计** | 数据/产品 deck、客户案例、产品 Demo Day |

---

## 12. 北极星指标 & KPI

**北极星**：**月度复购买家数（Monthly Reorder Buyers, MRB）**
> 选它而不是 GMV：复购才能验证产品价值，GMV 容易被首单冲动拉高。

**辅助 KPI**：

| 维度 | 指标 | M6 目标 | M12 目标 |
|---|---|---|---|
| 流量 | 月活买家（MAB） | 5K | 30K |
| 转化 | 询单转化 | 2% | 4% |
| 转化 | 询单 → 首单 | 30% | 45% |
| 价值 | 累计 GMV | \$150K | \$1.0M |
| 价值 | 平均订单价值 AOV | \$1,200 | \$1,800 |
| 留存 | 6 个月复购率 | — | 35% |
| AI | Design Agent 接受率 | 25% | 35% |
| AI | 单订单 AI 成本 | < \$3 | < \$2 |
| 履约 | 准时交付率 OTD | 85% | 95% |
| 履约 | QC 一次通过率 | 92% | 97% |

---

## 13. 风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| 美国对华关税升级 | 价格优势消失 | 海外仓 buffer + DDP 报价稳定锁定客户预期；评估墨西哥 / 越南补充产能（M9） |
| 跨境物流延迟 | 用户流失 | 海外仓常备 SKU + 公开履约 SLA + 延期赔付条款 |
| Pacdora / Packhelp 进 China + AI | 差异化被吃 | 把防伪 + 数字化包装作为护城河（他们做不了） |
| 首发市场选错 | 流量贵转化低 | 选**美国单一**而非多国铺开；SEO + Reddit + LinkedIn ABM 三路打透；3 个月不见数据立刻复盘 |
| Agent 成本失控 | 毛利被吃 | 每个 Agent 设 token 上限；缓存高频请求；非付费用户用更便宜模型 |
| 金冠 ERP 对接慢 | M5 履约链路推迟 | 提前 M2 启动；准备纯人工 fallback 流程 |
| 海外团队 / 客服时差 | NPS 低 | M6 起雇美西 1 人 + 远程 24/7 排班；Concierge Agent 兜底 |
| 数据合规（GDPR/CCPA） | 罚款 / 信誉 | 默认最严标准设计；M9 前完成 GDPR 合规审计 |

---

## 14. 待决议事项（Open Questions）

- [ ] **品牌名**：用 Jinguan 派生（如 jinguanpack 二级品牌）还是独立品牌？倾向独立品牌 + "Powered by Jinguan" 背书。
- [ ] **首发市场**：美国 vs 欧盟 vs 中东。当前倾向**美国**（DTC 密度最高、Shopify 渗透最深、关税虽高但客单价能扛）。需独立做一份首发市场决策备忘。
- [ ] **fenxiangyin 国内技术栈复用比例**：建议复用产品配置器 + 价格引擎核心代码，抛弃中文 UI / 国内支付 / 微信生态。
- [ ] **AI Agent 编排框架**：LangGraph vs 自研。建议先 LangGraph 起步，降低开发成本，M9 后视情况自研替换。
- [ ] **境内外双主体架构**：境外 SaaS 实体在哪里注册（开曼 / 新加坡 / 香港）？关系到融资节奏。
- [ ] **设计 IP 归属**：用户用 AI 生成的稿件 IP 归谁？需法律意见书。
- [ ] **样品成本**：5 美元 / 套是否覆盖物流？是否对低意向流量限免单数？

---

## 15. 关联文档（Backlinks）

- 战略备忘录（待补）：[[../_strategy-memo]]
- 竞品对标：[[../Competitor-Research/_index]]
- 金冠品牌资产：[[../Jinguan-Brand/_index]]
- 产品目录与 SKU 工艺库：[[../Product-Catalog/_index]]
- 与 jinguanpack.com 融合方案：[[../Integration-Plan/_index]]
- 外贸获客打法：[[../Marketing-Playbook/_index]]

---

## 16. 变更日志

| 日期 | 版本 | 变更 | 作者 |
|---|---|---|---|
| 2026-05-23 | v0.1 | 首版草案 | Samuel + Kiro |
