# Phase 3 · AI 驱动的量化交易

涵盖：**Crypto 合约 + Crypto Meme + A股 + 美股**。同 Phase 内子目录硬隔离，将来某条线独立成 Phase 5 时整目录搬走。

## 子目录

| 子目录 | 焦点 |
|---|---|
| `perp-contracts/` | Crypto 合约（中心化交易所：Binance / Bybit / OKX） |
| `meme-trading/` | Crypto Meme（链上 DEX 交易，参考 whogotpump 类闭环） |
| `astock-ustock/` | A股 / 美股策略（暂共置，独立账号体系） |
| `shared-lib/` | 公共：数据接入、回测引擎、风控、执行、告警 |

## 公共组件 shared-lib

```
shared-lib/
├── data/            # 行情 / 链上数据接入
├── backtest/        # 回测框架
├── execution/       # 下单执行层
├── risk/            # 风控（仓位 / 止损 / 黑名单）
├── alerting/        # 飞书 / Telegram / Discord 告警
└── utils/
```

## 与 50-Intelligence 的关系

- **输入**：`50-Intelligence/{crypto-watch,stock-watch,macro-watch}/` 把信号写进 `00-Inbox/`，由 `intel-summarizer` Agent 生成结构化信号 → 本 Phase 策略消费。
- **输出**：交易日志 / 持仓快照 → `40-Hermes-VPS/monitoring/`。

## 风控红线（Phase 级强制）

1. 任何策略上线前必须通过 `shared-lib/backtest/` 回测 + paper trading 灰度。
2. 单策略最大资金占比、单日最大回撤写进 `shared-lib/risk/limits.yaml`。
3. 全部资金不得跨子目录共享账号 —— **合约 / meme / 股票 各自独立钱包 / 账户**。
