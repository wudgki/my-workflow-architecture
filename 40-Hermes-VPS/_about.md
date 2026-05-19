# 40-Hermes-VPS · Hermes 服务运行时

Hermes 当前部署在 **VPS**，未来可能迁回 **本地副电脑**。所有 VPS / 部署相关物料统一收敛在本目录，迁移时只动这一个目录。

## 子目录

| 目录 | 内容 |
|---|---|
| `deploy/` | docker compose 模板 + 部署 SOP，含 [`docker-compose.example.yml`](./deploy/docker-compose.example.yml) 和 [`README.md`](./deploy/README.md) |
| `services/` | Hermes 各子服务的配置（Wiki 索引、Agent 调度、Webhook 等） |
| `env/` | `.env.example`（真值在 `90-Ops/secrets/hermes/`，永不入 git） |
| `monitoring/` | 日志收集 / 告警规则 / 健康检查 |
| `runbook/` | 运维 SOP，含 [`migration-vps-to-local.md`](./runbook/migration-vps-to-local.md) |

## 与其他角色的关系

- **读 Wiki**：Hermes 以只读方式挂载 / 同步 `10-Hermes-Wiki/`。
- **被 Agent 调用**：`20-Claude-Code/agents/` 中的 Agent 通过 Hermes 暴露的 HTTP / Webhook 接口触发任务。
- **吃情报**：`50-Intelligence/` 的 pipelines 把信号推给 Hermes 的 webhook。
- **驱动交易**：Phase 3 / 4 的策略可由 Hermes 调度。

## 不要做的事

- 不要在本目录写业务策略代码（应在 `30-Phases/`）。
- 不要把真实密钥提交到本目录（用 `90-Ops/secrets/`）。
