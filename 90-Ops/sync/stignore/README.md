# stignore/ · Syncthing 忽略规则模板

每个 `.stignore` 对应一个 Syncthing 共享根。`Init-AIWorkspace.ps1` 会把它们安装到对应目录的 `.stignore`。

## 模板与共享对应

| 模板文件 | 安装位置 | 共享 ID |
|---|---|---|
| `wiki.stignore` | `10-Hermes-Wiki/.stignore` | `samuel-aiws-wiki` |
| `claude-code.stignore` | `20-Claude-Code/.stignore` | `samuel-aiws-claude-code` |
| `phases.stignore` | `30-Phases/.stignore` | `samuel-aiws-phases` |
| `inbox.stignore` | `00-Inbox/.stignore` | `samuel-aiws-inbox` |
| `repo-research.stignore` | `60-Repo-Research/.stignore` | `samuel-aiws-repo-research` |

## .stignore 语法速记

- 一行一条规则。
- `pattern`：忽略匹配的文件 / 目录。
- `!pattern`：解除忽略（白名单），优先级高于后续 ignore 规则。
- `**`：递归任意层级（如 `**/node_modules`）。
- `*`：单层通配。
- `//` 开头：注释。
- `(?d)pattern`：删除匹配项（危险，本仓不使用）。
- `(?i)pattern`：大小写不敏感（Windows 默认就是不敏感，无需此前缀）。

完整文档：https://docs.syncthing.net/users/ignoring.html

## 修改流程

1. 改本目录下对应 `.stignore` 文件。
2. 提交 Git。
3. 在每台机器上重新跑 `Init-AIWorkspace.ps1 -Force` 同步到落地目录。
4. Syncthing 会自动检测到 `.stignore` 变更并重扫。

## 不要做

- ❌ 不要直接在落地目录手改 `.stignore` —— 改完会被下次 `Init` 覆盖。
- ❌ 不要忽略 `.gitkeep` —— 那是占位文件，需要被同步。
- ❌ 不要忽略 `_about.md` / `README.md` —— 这是骨架的一部分。
