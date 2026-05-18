# 90-Ops · 双机协作 / 同步 / 密钥

跨机协作的"控制面"。只有这里关心"哪台机器写什么、密钥怎么走、坏了怎么救"。

## 子目录

| 目录 | 内容 |
|---|---|
| `sync/` | rclone / Syncthing / Git 的同步配置 |
| `secrets/` | 密钥（**全部 .gitignore**），仅放 `README.md` 说明 |
| `backup/` | 备份策略 / 脚本 / 校验 |
| `multi-machine-protocol.md` | 主机 / 副机 / VPS 的协作约定 |

## 三机角色

| 机器 | 角色 | 主要写入域 |
|---|---|---|
| **主电脑** | Primary / 创作 | `10-Hermes-Wiki/`、`30-Phases/`、`60-Repo-Research/` |
| **副电脑** | Secondary / 备份 + 长跑任务 | 与主电脑镜像；可执行 `30-Phases/` 长任务 |
| **VPS** | Hermes 服务 + 情报 | `40-Hermes-VPS/`、`50-Intelligence/` |

详细规则见 [`multi-machine-protocol.md`](./multi-machine-protocol.md)。
