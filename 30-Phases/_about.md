# 30-Phases · 各 Phase 的可执行项目代码

每个 Phase 一个子目录，**真实业务代码**的归属地。Wiki 只放笔记，本目录放代码。

## 子目录

```
30-Phases/
├── phase1-infra-intel/        # 基建 + 情报抓取脚本（与 50-Intelligence 协作）
├── phase2-b2b-platform/
│   ├── overseas-platform/     # 海外 B2B 包装平台
│   ├── jinguan-site/          # Guangdong Jinguan 海外独立站
│   ├── integration/           # 融合层（共用账号 / CMS / 品牌背书）
│   └── _about.md
├── phase3-crypto-quant/
│   ├── perp-contracts/        # 合约策略
│   ├── meme-trading/          # meme（含 whogotpump 类参考）
│   ├── astock-ustock/         # A股 / 美股（同 Phase 内隔离，未来可抽出）
│   ├── shared-lib/            # 公共回测 / 数据 / 风控 / 执行
│   └── _about.md
└── phase4-prediction-market/  # Polymarket / Kalshi
```

## Phase 间隔离原则

- **共享代码** 必须放在 Phase 内的 `shared-lib/`，不允许跨 Phase 引用业务代码。
- **共享工具**（HTTP 客户端、数据库 ORM 模板）放 `20-Claude-Code/skills/` 或独立维护的私有包。
- **环境变量**：每个 Phase 独立 `.env`，模板入库 `.env.example`，真值由 `90-Ops/secrets/` 注入。

## 与 Hermes-VPS 的关系

- Phase 项目可被 Hermes 调度执行，但 Hermes 配置归 `40-Hermes-VPS/services/`。
- Phase 项目中**不写**部署 yaml，部署归 `40-Hermes-VPS/deploy/`。
