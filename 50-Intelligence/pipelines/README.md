# 50-Intelligence/pipelines/ - 情报管道配置

本目录存放情报管道的共享配置文件，供 `intel-summarizer` agent 和 `community-bridges` 桥接器消费。

---

## keywords.yaml 用途

`keywords.yaml` 是 **Phase 路由关键词字典**，决定一条新入箱的 capture 应被打上哪个 Phase 标签。

核心场景：

1. `50-Intelligence/community-bridges/` 桥接器把消息写入 `00-Inbox/` 时，预打 `phase` 标签。
2. `intel-summarizer` agent 做 Triage 时，匹配正文关键词，自动填 front-matter `phase` 字段。
3. `00-Inbox/Inbox-Processing-Rules.md` 第五节引用本字典作为路由标准。

---

## Phase 1/2/3/4 分别代表什么

| Phase | 代号 | 业务范围 |
|---|---|---|
| Phase 1 | Infra and Intel | 基建 + 情报监控系统（MCP、Claude Code、Hermes、Obsidian、VPS、CI/CD、LLM/RAG） |
| Phase 2 | B2B Packaging Platform | 海外 B2B 网络印刷包装平台（Jinguan 海外独立站融合、外贸获客、SEO/SEM、跨境物流） |
| Phase 3 | Crypto Quant and Trading | AI 驱动的量化交易系统（Crypto 合约 + meme + 链上 + A股/美股 + 宏观） |
| Phase 4 | Prediction Market | Polymarket / Kalshi 预测市场自动化交易 |

---

## 路由规则：first-match-wins

```
新 capture 进入 00-Inbox/
    |
逐个 Phase 按顺序（phase_1 -> phase_2 -> phase_3 -> phase_4）匹配 include 列表
    |
命中 -> 检查该 Phase 的 exclude 列表
    |
如果不在 exclude -> phase 确定，标签打上
如果在 exclude -> 跳过本 Phase，继续匹配下一个
    |
全部 Phase 都不命中 -> phase = null -> 进入 00-Inbox/To-Process/ 等人工分诊
    |
命中 global_exclude -> 无论是否匹配到 Phase，强制进 To-Process/
```

关键设计：

- **大小写不敏感**：`"BTC"` 和 `"btc"` 都能命中。
- **纯子串匹配**：不支持正则，简单粗暴但可预测。
- **一条 capture 只归一个 Phase**：避免重复处理。
- **有歧义时先匹配到的 Phase 赢**：所以 Phase 1 排最前面（infra 型关键词容易和其它 Phase 冲突）。

---

## global_exclude 的用途

有些关键词即使命中了某个 Phase，也明显是垃圾或测试。放进 `global_exclude` 后，匹配到这些词的 capture 会被强制打 `phase: null`，进入 `To-Process/` 等人工处理。

当前 global_exclude：

- `test` / `testing only`：测试消息
- `ignore`：明确标记不处理
- `spam` / `unsubscribe`：垃圾消息

---

## 如何新增关键词

1. 打开 `keywords.yaml`，找到对应 Phase 的 `include` 列表。
2. 在列表末尾追加新关键词（用双引号包裹）。
3. **只用 ASCII 字符**（见下方"为什么保持 ASCII-only"）。
4. 提交 Git，CI 自动审计，PR 合并。
5. 桥接器和 agent 下次运行时自动加载新关键词。

命名约定：

- 优先用英文全称：`"Polymarket"` 而非 `"PM"`（太短容易误触发）
- 如果一个术语有多种拼写：加多行（如 `"DeFi"` + `"defi"`）
- 如果一个术语太通用（如 `"call"`）：观察误判率，必要时移到 exclude

---

## 如何处理误判

| 场景 | 处理方式 |
|---|---|
| 某关键词导致大量 capture 被错误归到 Phase X | 从 `phase_X.include` 移到 `phase_X.exclude`，或加到其它 Phase 的 exclude |
| 某 capture 明显属于 Phase Y 但被归到 Phase X | 检查 Phase X 的 include 列表里是否有太宽泛的词命中 |
| 某 capture 啥都没命中（`phase: null`） | 字典覆盖不够，在对应 Phase 加上新关键词 |
| 某来源频繁产生垃圾 | 把垃圾特征词加入 `global_exclude` |

误判修正流程：

1. 发现误判 -> 在 `00-Inbox/To-Process/` 看到被错标的 capture
2. 手动改正 capture 的 `phase` 字段
3. 回到 `keywords.yaml` 修正规则（加 exclude 或调整 include）
4. 提交 Git + PR

---

## 为什么 YAML 保持 ASCII-only，中文说明放 README

1. **CI 审计要求**：`Audit-ScriptHygiene.ps1` 会扫描所有 `.yaml` 文件，非 ASCII 字符会触发 WARNING 或 CRITICAL。保持纯 ASCII 确保 CI 永远绿。
2. **GitHub 渲染安全**：含非 ASCII 的 YAML 在 GitHub "Files changed" 页面可能触发 "hidden Unicode" 警告横幅，干扰代码审查。
3. **跨平台一致性**：YAML 解析器在不同系统对 BOM 和编码的处理不一致；纯 ASCII 是唯一不会出错的选择。
4. **中文说明的需求仍然存在**：所以放在本 `README.md`（Markdown 文件不受 CI 审计约束，中文自由使用）。

---

## 季度审查提醒

`keywords.yaml` 的 `_meta.next_review` 字段记录了下次审查日期。每季度做一次：

- [ ] 移除已死项目 / 已退市币种 / 已下线平台
- [ ] 补充新发现的来源 / 术语 / KOL 名字
- [ ] 检查 `global_exclude` 是否需要扩展
- [ ] 查看过去 3 个月的 `To-Process/` 积压，看是否有大量同类 capture 在等人工
- [ ] 更新 `_meta.last_reviewed` 和 `_meta.next_review`

---

## 文件清单

| 文件 | 用途 | 约束 |
|---|---|---|
| `keywords.yaml` | Phase 路由关键词字典 | 纯 ASCII，CI 审计通过 |
| `README.md` | 本文件（中文说明） | 无编码约束 |
