# bridge-ingress Telegram 本地 smoke test

> **范围**：仅本地开发机。**禁止在 VPS 跑本 runbook**——它会构建镜像、
> 暴露 `:8080`、并用 `fake-secret-*` 启动容器。VPS 的部署流程见
> `40-Hermes-VPS/deploy/README.md`，PR #15 阶段 VPS 上**继续**只跑
> `cloudflared` 单服务，不接 bridge-ingress。

PR #15 引入了 `50-Intelligence/community-bridges/bridge-ingress/`——第一台
真业务容器，只接 Telegram。本 runbook 是**人读流程**，机器执行用
`50-Intelligence/community-bridges/bridge-ingress/tests/smoke-test.sh`，
两份**不重复命令**。

---

## 1. 前置条件

- [ ] PR #12（compose 模板）、#13（tunnel runbook）、#14（SPEC）已合并到 `main`
- [ ] 本地装了 Docker（`docker --version` 任意 24+）
- [ ] 本地装了 `bash` + `curl`（macOS / Linux / WSL 默认就有）
- [ ] 蓝图仓库已 clone（脚本会从仓库根读 `50-Intelligence/pipelines/keywords.yaml`）
- [ ] 本地 `:8080` 端口空闲（被占的话用 `PORT=18080 tests/smoke-test.sh`）

**不需要**：

- ❌ 真实 Telegram Bot Token
- ❌ 真实 `TELEGRAM_WEBHOOK_SECRET`（脚本用 `fake-secret-*`）
- ❌ 公网域名 / Cloudflare Tunnel
- ❌ VPS 任何资源

---

## 2. 执行

```
cd <repo-root>/50-Intelligence/community-bridges/bridge-ingress
./tests/smoke-test.sh
```

脚本会按 7 步顺序跑完：build → run → healthz → 错 secret → 对 secret →
落盘验证 → front-matter 字段验证。失败任意一步会打印失败原因 + 容器日志，
退出码非 0。

---

## 3. 预期输出（成功路径）

```
[1/7] docker build -> bridge-ingress:smoke
[2/7] docker run bridge-ingress-smoke on :8080 (inbox=/tmp/bridge-inbox-XXXXXX)
[3/7] GET /healthz -> expect 200
[4/7] POST /webhook/telegram with WRONG secret -> expect 401
[5/7] POST /webhook/telegram with CORRECT secret + valid update -> expect 200
[6/7] verify inbox file landed in /tmp/bridge-inbox-XXXXXX/Telegram-Captures/
    -> /tmp/bridge-inbox-XXXXXX/Telegram-Captures/2026-05-19_telegram_-100199988877_4242.md
[7/7] verify front-matter contains chat_id, message_id, phase

SMOKE TEST PASSED
```

末行必须是 `SMOKE TEST PASSED`。日期前缀（`2026-05-19_`）反映**当前 UTC 日期**，
随机 tmp 目录后缀逐次不同。

---

## 4. 验收标准

| 项 | 期望 | 检查方式 |
|---|---|---|
| 镜像构建成功 | 退出 0，最终 `<image>` < 100 MB | `docker images bridge-ingress:smoke` |
| `/healthz` | 200 + `{"status":"ok"}` | 步骤 3 已自动校验 |
| 错 secret | 401 | 步骤 4 |
| 对 secret + 合法 payload | 200 | 步骤 5 |
| 落盘 | `<inbox>/Telegram-Captures/YYYY-MM-DD_telegram_<chat>_<msg>.md` 出现且唯一 | 步骤 6 |
| front-matter | 含 `chat_id` / `message_id` / `phase` / `source: telegram` | 步骤 7 |
| 0 真实 secret | 容器日志 / 文件内容 / 进程环境无 `REPLACE_ME` 之外的真 token | `docker exec bridge-ingress-smoke env` 手工核 |
| 容器自清理 | 脚本结束后 `docker ps -a` 看不到 `bridge-ingress-smoke` | EXIT trap 已处理 |

---

## 5. 故障排查

| 现象 | 可能原因 | 处置 |
|---|---|---|
| `[1/7]` 卡在 `pip install` | 本地没拉到 PyPI / musl wheel 不全 | 检查代理；或 `--build-arg` 加 `PIP_INDEX_URL` |
| `[2/7]` 后 `/healthz` 一直拿不到 200 | uvicorn 起不来 | `docker logs bridge-ingress-smoke` 看 traceback；多半是某个环境变量没传 |
| `[3/7]` 拿到 502 / 连不上 | 端口 8080 已被占 | 用 `PORT=18080 tests/smoke-test.sh` 换端口 |
| `[5/7]` 拿到 401 | secret 字符串里混了不可见字符 / 大小写不一致 | 重新 `cat` 脚本，对照 `tests/fixtures/telegram_btc_signal.json` 的 SECRET 字面量 |
| `[6/7]` 没生成文件 | `/data/inbox` 挂载权限问题（macOS Docker Desktop 偶尔抽风） | `docker exec bridge-ingress-smoke ls -la /data/inbox`；必要时清掉 `~/Library/Containers/com.docker.docker` 重建 |
| `[7/7]` `phase missing` | front-matter 写盘了但缺字段 | 看 `inbox_writer.py::front_matter` 是否被改坏；`pytest tests/test_routing_and_writer.py -k frontmatter` |
| 镜像 > 100 MB | 多了 build-base 残留 / venv 没拷干净 | `docker history bridge-ingress:smoke` 找最大层；多半是 `requirements.txt` 加了非预期依赖 |

---

## 6. 单元测试（独立于 docker）

不需要 docker 时，直接装依赖跑 pytest：

```
cd <repo-root>/50-Intelligence/community-bridges/bridge-ingress
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest httpx
pytest -q
```

期望：3 个测试文件全 PASS，无 warning，退出 0。

---

## 7. 严格禁止

- ❌ 在 VPS 上执行本脚本
- ❌ 把 `fake-secret-*` 字面量改成真实 secret 后提交
- ❌ 把 `tests/fixtures/telegram_btc_signal.json` 改成真实 chat_id / message_id
- ❌ 跳过 `[4/7]` 错 secret 一步（这是验证 401 行为，不能"反正能 200 就好"）
- ❌ 用 `docker compose up -d` 在本地启动整套 stack——本 runbook 只覆盖单容器
- ❌ 把容器日志贴到 PR / Issue / 公开 chat 里（即便日志已脱敏，也按"零拷贝"对待）

---

## 8. 验收记录

| 日期 | 执行人 | 主电脑 / 副电脑 | 结果 | 备注 |
|---|---|---|---|---|
| YYYY-MM-DD | _ | _ | PASS / FAIL | _ |

---

## 相关文档

- 接口契约：`50-Intelligence/community-bridges/SPEC-bridge-ingress.md`（PR #14）
- 镜像与代码：`50-Intelligence/community-bridges/bridge-ingress/`（PR #15）
- 自动化脚本：`50-Intelligence/community-bridges/bridge-ingress/tests/smoke-test.sh`
- VPS 部署模板：`40-Hermes-VPS/deploy/README.md`（PR #12）
- VPS 隧道 runbook：`40-Hermes-VPS/runbook/cloudflare-tunnel-smoke-test.md`（PR #13）
- Inbox 落盘约定：`00-Inbox/Inbox-Processing-Rules.md`
  （注：bridge 文件名**有意偏离**该规则，详见 `bridge-ingress/README.md`）
