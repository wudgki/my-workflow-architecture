# Phase 2 · 海外 B2B 包装平台

## 三件套

| 子项目 | 角色 |
|---|---|
| `overseas-platform/` | 海外版 B2B 网络印刷包装电商平台主体（参考国内 fenxiangyin.com） |
| `jinguan-site/` | Guangdong Jinguan Technology Co., Ltd. 海外独立站 |
| `integration/` | 二者融合层：共用账号体系 / CMS / 品牌背书 / SEO 主域策略 |

## 融合策略要点

- Jinguan 作为 **品牌背书** 出现在 Overseas Platform 的"工厂直供 / About"等模块。
- 共用 **统一账号体系**（OAuth / SSO），订单与询盘可在两侧互通。
- 域名策略：建议主站为 Overseas Platform，Jinguan 独立站作为子域 / 二级目录承担品牌页面。
- 详细方案见 `10-Hermes-Wiki/20-Phase2-B2B-Platform/Integration-Plan/`。

## 技术栈占位（待定）

- 前端：待定（候选 Next.js / Astro）
- 后端：待定（候选 NestJS / Django）
- AI Agent：通过 `20-Claude-Code/` 的 skills 调用
- 部署：`40-Hermes-VPS/deploy/`
