# Multi-Machine Protocol · 多机协作协议

> 三方角色：**主电脑 (Primary)** / **副电脑 (Secondary)** / **VPS (Hermes)**
> 目标：保证数据一致、避免冲突、明确"谁能写谁只读"。

---

## 一、角色与职责

| 机器 | 别名 | 主要职责 | 可写域 | 只读域 |
|---|---|---|---|---|
| 主电脑 | `primary` | 创作 / 决策 / Wiki 主写 | 所有 | — |
| 副电脑 | `secondary` | 备份 / 长跑任务 / 灾备接管 | 与主电脑镜像 + `30-Phases/` 长任务输出 | `10-Hermes-Wiki/` 默认只读，进入"接管模式"才可写 |
| VPS | `hermes` | Hermes 服务 + 情报抓取 | `40-Hermes-VPS/`、`50-Intelligence/`、`00-Inbox/<source>-Captures/` | 其余目录全部只读 |

> **黄金法则：同一文件同一时间只允许一台机器写。**

---

## 二、目录写入权矩阵

| 目录 | primary | secondary | hermes |
|---|:---:|:---:|:---:|
| `00-Inbox/Discord-Captures/` | RW | R | **W**（写入） |
| `00-Inbox/Telegram-Captures/` | RW | R | **W** |
| `00-Inbox/Feishu-Captures/` | RW | R | **W** |
| `00-Inbox/Web-Clips/` | RW | RW | **W** |
| `00-Inbox/Repo-Captures/` | RW | RW | **W** |
| `00-Inbox/To-Process/` | RW | RW | R |
| `00-Inbox/Wiki-Drafts/` | RW | RW | R |
| `10-Hermes-Wiki/` | **RW** | R（接管才 RW） | R |
| `20-Claude-Code/` | RW | RW | R |
| `30-Phases/` | RW | RW（仅运行期产物） | R |
| `40-Hermes-VPS/` | RW（配置） | R | **RW**（运行期） |
| `50-Intelligence/` | RW（脚本） | R | **RW**（运行期） |
| `60-Repo-Research/` | RW | RW | R |
| `70-Sandbox/` | RW（不同步） | RW（不同步） | — |
| `90-Ops/sync/` | RW | RW | R |
| `90-Ops/secrets/` | **RW**（本地） | RW（本地） | RW（本地） |
| `90-Ops/backup/` | RW | RW | R |

> **`secrets/` 永不通过任何同步通道传输**，每台机器本地各自维护，必要时通过 SSH + age/sops 手动分发。

---

## 三、同步通道

```
                  ┌─ Syncthing ──┐
   primary <─────>│              │<─────> secondary
                  └──────────────┘
       │                                  │
       │  Git push (Wiki + 文档骨架)       │  Git push
       │                                  │
       ▼                                  ▼
            ┌────  GitHub (本仓库 + Wiki 仓) ────┐
            └──────────────────────────────────┘
                            │
                            │ SSH + rsync（只拉，不推）
                            ▼
                          hermes (VPS)
```

- **主 ↔ 副**：Syncthing（实时） + Git（带审计的快照）。
- **主/副 → GitHub**：Git push，Wiki 用单独的 private repo（结构在本蓝图仓）。
- **VPS ← GitHub**：拉取 Wiki / Phase 项目（**只拉不推**），定时 `git pull` + 触发 Hermes 索引重建。
- **VPS → 主**：仅通过 `00-Inbox/` 写入回流（Syncthing 单向：VPS → primary）。

---

## 四、Syncthing 配置规范

- **共享 ID 命名**：`samuel-aiws-<scope>`，如 `samuel-aiws-wiki`、`samuel-aiws-claude-code`。
- **忽略文件**：每个共享根目录放 `.stignore`，至少包含：
  ```
  .git
  .obsidian/workspace*
  .obsidian/cache
  *.env
  *.env.*
  !*.env.example
  secrets/
  70-Sandbox/
  logs/
  *.log
  __pycache__/
  node_modules/
  ```
- **冲突处理**：保留 `<filename>.sync-conflict-*` 文件，**不自动合并**，每周一人工检查清理。
- **版本保留**：开启 Simple Versioning，保留 7 天。

---

## 五、写入冲突预防

1. **以目录为锁的粗粒度规则**：
   - Wiki 同一笔记 24 小时内只允许一台机器编辑。约定：日常默认 primary，primary 不可用时 secondary "接管"（在 `90-Ops/sync/handover.md` 加一行 `YYYY-MM-DD takeover by secondary`）。
2. **Hermes 永远不写 Wiki**：所有 Hermes 想"写回 Wiki"的需求必须通过 `00-Inbox/Wiki-Drafts/` 走草稿流程。
3. **长跑任务**：副电脑跑回测 / 抓取时，输出落 `30-Phases/<phase>/runs/<YYYY-MM-DD>-secondary/`，避免和主电脑产物碰撞。
4. **commit 约定**：跨机修改同一文件 → 必须先 `git pull --rebase`，禁止 `git push --force`。

---

## 六、灾备接管流程

### Primary 不可用 → Secondary 接管

1. 在 `90-Ops/sync/handover.md` 写入接管时间戳与原因。
2. Secondary 关闭 Syncthing 的 receive-only 限制（如有）。
3. Secondary 解除 `10-Hermes-Wiki/` 的只读，开始正常写入。
4. Primary 恢复后**先**：拉取 Secondary 的最新内容 → 检查冲突 → 合并 → 写回 handover.md 标记接管结束。

### VPS 不可用

- Phase 1 / 情报：副电脑暂时承担，启动本地版 `50-Intelligence/pipelines/`。
- Hermes 服务：参照 `40-Hermes-VPS/runbook/migration-vps-to-local.md` 临时迁回本地。

---

## 七、备份策略

| 数据 | 频率 | 介质 | 保留 |
|---|---|---|---|
| `10-Hermes-Wiki/` | 每日 02:00 | `90-Ops/backup/wiki/`（本地）+ B2/S3 加密 | 90 天滚动 |
| `30-Phases/`（不含 `node_modules` / `runs`） | 每周日 | 同上 | 90 天 |
| `90-Ops/secrets/` | 手动每月 | **离线**加密硬盘 + 1Password Vault 双备 | 永久 |
| `40-Hermes-VPS/services/` 配置 | 变更触发 | Git | 永久 |

校验：每月 1 号执行 `90-Ops/backup/verify.sh`，输出报告到 `backup/reports/YYYY-MM.md`。

---

## 八、机器身份标记

每台机器的根目录放 `.machine-id`（不入库）：

```yaml
# .machine-id
hostname: samuel-primary
role: primary           # primary | secondary | hermes
last_handover: null
notes: 主创作机
```

脚本启动时检查 `role`，决定是否允许写入受限目录。

---

## 九、待补全（TODO）

- [ ] `90-Ops/sync/syncthing-folders.yaml`：所有 Syncthing 共享的声明
- [ ] `90-Ops/sync/handover.md`：接管日志（首行写规范）
- [ ] `90-Ops/backup/verify.sh`：备份校验脚本
- [ ] 在主电脑落地 `.machine-id` 模板
