# 60-Repo-Research · 仓库分析中文产物

由 `20-Claude-Code/agents/repo-researcher` 主要产出，Wiki 在 `10-Hermes-Wiki/50-Repo-Research/` 引用本目录。

## 子目录

| 目录 | 内容 |
|---|---|
| `reports/` | 单仓库分析报告，文件名 `YYYY-MM-DD-<owner>-<repo>.md` |
| `comparisons/` | 多仓库横向对比（"哪个适合我"） |
| `adopt-list/` | 已选用仓库 + 选用理由 + 集成点 |
| `reject-list/` | 已淘汰仓库 + 淘汰理由（避免重复评估） |

## 报告必填字段（中文）

1. **仓库定位**：一句话 + 适用场景。
2. **核心价值**：3-5 条 bullet。
3. **架构速览**：关键模块 / 数据流。
4. **对我适配度**：在哪个 Phase 用、需要改造的地方。
5. **风险与坑**：依赖、许可证、维护活跃度。
6. **结论**：采纳 / 观望 / 淘汰。

模板见 `10-Hermes-Wiki/99-Templates/`。
