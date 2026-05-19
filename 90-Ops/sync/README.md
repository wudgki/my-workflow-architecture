# 90-Ops/sync · 多机同步配置

> 把主电脑 / 副电脑通过 **Syncthing** 实时同步；把 VPS (Hermes) 通过 **Git + SSH 拉取** 单向消费。
> 本目录是配置中心，对应规则见 [`../multi-machine-protocol.md`](../multi-machine-protocol.md)。

---

## 一、共享一览

按 **目录粒度** 划分共享，五个共享根：

| 共享 ID | 落地路径 | 主电脑 | 副电脑 | 说明 |
|---|---|---|---|---|
| `samuel-aiws-wiki` | `10-Hermes-Wiki/` | RW | R（接管才 RW） | Obsidian Vault，主写在主机 |
| `samuel-aiws-claude-code` | `20-Claude-Code/` | RW | RW | Agent / Skill / Prompt 双向同步 |
| `samuel-aiws-phases` | `30-Phases/` | RW | RW | 业务代码 |
| `samuel-aiws-inbox` | `00-Inbox/` | RW | RW | 双向：哪台机器都可能产生 capture |
| `samuel-aiws-repo-research` | `60-Repo-Research/` | RW | RW | 仓库分析报告 |

**显式不参与 Syncthing 的目录**（任何机器自治）：

- `40-Hermes-VPS/` — 只通过 Git 同步配置，运行期数据在 VPS / 本地服务节点
- `50-Intelligence/` — 同上（脚本入 Git，运行期数据走 webhook）
- `70-Sandbox/` — 实验目录，不同步
- `90-Ops/secrets/` — **永不**经 Syncthing 传输，手工 SSH + age/sops 分发
- `90-Ops/backup/` — 本机备份产物，不互传
- `.git/` — 用 Git 管理，不要让 Syncthing 也碰

---

## 二、声明文件

- [`syncthing-folders.yaml`](./syncthing-folders.yaml)：所有共享的"权威声明"，谁导入 Syncthing GUI 都按这份配置。
- [`stignore/`](./stignore/)：每个共享根对应一份 `.stignore`，由 `Init-AIWorkspace.ps1` 安装到目标位置。

---

## 三、首次配置 SOP（主电脑 → 副电脑）

### 3.1 主电脑

1. 安装 Syncthing：https://syncthing.net/downloads/
2. 启动 Web GUI（默认 `http://127.0.0.1:8384`）。
3. 把本机的 **Device ID** 抄到 `syncthing-folders.yaml` 的 `devices.primary.id`。
4. 按 `syncthing-folders.yaml` 中每个 `folder` 在 GUI **添加文件夹**：
   - Folder ID 用 `samuel-aiws-<scope>`
   - Folder Path 指向落地的实际目录
   - 暂不要"分享给设备"——等副电脑就绪
5. 确认每个共享根目录下都有 `.stignore`（由 `Init-AIWorkspace.ps1` 安装；如果你手工配置，从 `90-Ops/sync/stignore/<scope>.stignore` 复制过去）。

### 3.2 副电脑

1. 安装 Syncthing。
2. 把本机 Device ID 抄到 `syncthing-folders.yaml` 的 `devices.secondary.id`。
3. 在主电脑 GUI 把副电脑作为新 Device 添加（粘贴它的 ID）。
4. 每个 folder 上点 **Edit → Sharing**，勾选副电脑。
5. 副电脑收到弹窗"Accept new folder?"时：
   - **Folder Path**：与本机蓝图初始化时一致（如 `D:\AI-Workspace\10-Hermes-Wiki`）
   - **File Versioning**：按 `syncthing-folders.yaml` 中的 `versioning` 设置 Simple Versioning，保留 7 天
   - **Folder Type**：参见下表

### 3.3 Folder Type 选择

| 共享 | 主电脑 | 副电脑 |
|---|---|---|
| `samuel-aiws-wiki` | Send & Receive | **Receive Only**（默认；进入接管模式才改 Send & Receive） |
| `samuel-aiws-claude-code` | Send & Receive | Send & Receive |
| `samuel-aiws-phases` | Send & Receive | Send & Receive |
| `samuel-aiws-inbox` | Send & Receive | Send & Receive |
| `samuel-aiws-repo-research` | Send & Receive | Send & Receive |

> Wiki 副电脑设 Receive Only 是为了贯彻"同一文件同一时间一台机器写"的黄金法则。

---

## 四、健康检查

每周一手动确认：

- [ ] Syncthing GUI 全绿（无 Out of Sync / Failed Items）
- [ ] 没有 `*.sync-conflict-*` 文件遗留（有则按 `multi-machine-protocol.md` 第五节合并）
- [ ] `.stignore` 在每个共享根都还在
- [ ] 各 secrets 目录**没**被同步出去（在副电脑 `90-Ops/secrets/` 应保持本机自管，不应有 Syncthing 拉来的文件）

---

## 五、常见坑

1. **`.obsidian/workspace*` 同步会导致两机覆盖** → 模板里已忽略，别取消。
2. **`node_modules/` 同步会拖死磁盘** → 模板里已忽略；如果新增前端项目，确保它的 `node_modules/` 也被覆盖。
3. **大文件（>50MB）撑爆带宽** → 媒体类放 `_attachments/` 并按需归档；超过阈值的文件考虑外置存储。
4. **首次同步太慢** → 先用 USB 硬盘把 Wiki / Claude-Code 拷到副电脑相同路径，再让 Syncthing 增量校验。
5. **Cloud Drive（OneDrive / Dropbox）和 Syncthing 双层同步** → 不要叠加，会触发循环冲突。`AI-Workspace` 应放在**未被 OneDrive 接管**的盘符（如 `D:\`）。



---

## 六、syncthing-folders.yaml 字段中文释义

> `syncthing-folders.yaml` 必须保持 **纯 ASCII**（脚本卫生审计要求），所以中文说明集中放在这里。本节是字段对照表，便于回查。

### 6.1 顶层结构

| YAML 字段 | 中文释义 |
|---|---|
| `devices` | 参与 Syncthing 的机器列表（VPS 不参与） |
| `defaults` | 所有共享的默认设置（版本保留、扫描间隔） |
| `folders` | 五个 Syncthing 共享根的声明 |
| `never_share` | 显式禁止进入 Syncthing 的目录（用 Git / SSH rsync 替代） |

### 6.2 devices 字段

| 字段 | 含义 | 备注 |
|---|---|---|
| `name` | 机器主机名 | 与 `D:\AI-Workspace\.machine-id` 的 `hostname` 字段一致 |
| `id` | Syncthing Device ID | 在每台机器 Syncthing GUI 的 Settings 里复制 |
| `role` | `primary` / `secondary` | 与 `90-Ops/multi-machine-protocol.md` 第一节的角色定义对齐 |

- **primary**：主创作机。Wiki / Phases / Claude-Code / Inbox / Repo-Research 全部允许写入。
- **secondary**：备份 + 长跑任务 + 灾备接管机。Wiki 默认 Receive Only，仅当主机不可用时执行接管流程才允许写入。
- VPS（Hermes）不参与 Syncthing —— Hermes 通过 Git pull + SSH rsync 单向消费 Wiki / Phases，避免运行期数据混入同步通道。

### 6.3 defaults 字段

| 字段 | 含义 |
|---|---|
| `versioning.type: simple` | 版本策略：Simple Versioning（每次覆盖前保留旧版） |
| `versioning.keep: 7` | 保留 7 个历史版本，超出删除最旧 |
| `fs_watcher_enabled: true` | 启用文件系统监听（实时同步） |
| `rescan_interval_s: 3600` | 兜底全量扫描间隔（1 小时） |

### 6.4 folders 字段（每个共享根）

| 字段 | 含义 |
|---|---|
| `id` | Syncthing folder ID，命名 `samuel-aiws-<scope>` |
| `label` | GUI 显示名 |
| `path_relative` | 相对 `D:\AI-Workspace\` 的目录路径 |
| `devices` | 参与本共享的设备列表 |
| `type.<role>` | 该角色机器的 Folder Type：`sendreceive` 双向 / `receiveonly` 只读 |
| `ignore_perms` | 忽略 Unix 权限位（Windows 共享必须为 `true`） |
| `notes` | 一句话英文标识用途。**详细中文解释见下表 6.5** |

### 6.5 五个共享根的中文说明（原 yaml notes 移到这里）

| 共享 ID | 路径 | 中文说明 |
|---|---|---|
| `samuel-aiws-wiki` | `10-Hermes-Wiki/` | Obsidian 知识库主写在主电脑。`.obsidian/workspace*` 不同步（见 `stignore/wiki.stignore`）。**副电脑默认 Receive Only**，仅当主机不可用执行接管时才允许写入。这是为了贯彻"同一文件同一时间一台机器写"的黄金法则。 |
| `samuel-aiws-claude-code` | `20-Claude-Code/` | Agent / Skill / Prompt / MCP 配置。`logs/` 与 `memory/` 中的本机临时记忆不同步（见 `stignore/claude-code.stignore`）。 |
| `samuel-aiws-phases` | `30-Phases/` | 业务代码（Phase 1 ~ Phase 4）。`node_modules/` / `dist/` / `__pycache__/` / `.env` / `runs/` 全部忽略（见 `stignore/phases.stignore`）。 |
| `samuel-aiws-inbox` | `00-Inbox/` | 双向同步：哪台机器都可能产生 capture（桌面剪藏、手机推送、Discord/Telegram/飞书桥接器）。`_archive/auto-expired/` 不必互传（见 `stignore/inbox.stignore`）。 |
| `samuel-aiws-repo-research` | `60-Repo-Research/` | 仓库分析报告：`reports/` + `comparisons/` + `adopt-list/` + `reject-list/`。 |

### 6.6 never_share 字段

| 目录 | 不进 Syncthing 的原因 |
|---|---|
| `40-Hermes-VPS` | 通过 Git 同步配置，运行期数据在 VPS / 本地服务节点 |
| `50-Intelligence` | 同上（脚本入 Git，运行期数据走 webhook） |
| `70-Sandbox` | 实验目录，各机自治，短命数据不必互传 |
| `90-Ops/secrets` | **永不**经 Syncthing 明文传输。跨机分发用 SSH + age/sops 手动加密通道 |
| `90-Ops/backup` | 本机备份产物，不互传（避免双倍占用磁盘） |
| `.git` | 由 Git 自身管理，让 Syncthing 也碰会触发循环冲突 |
