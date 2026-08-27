# Situla 集成验证报告

执行时间：2026-08-07（Asia/Shanghai）

## 环境

- Situla：0.1.0
- 本地地址：`http://127.0.0.1:8787`
- 测试 Tool：`lmt-code-sandbox`
- 测试 Session：`lmt-code-session`

## 验证结果

1. Situla 本地服务启动成功。
2. Tool 列表显示本次创建的 Code、ArkClaw、Hermes、Skills 资源，状态均为 Ready。
3. 进入 `lmt-code-sandbox` 后可见 `lmt-code-session` 与 AIO run_code Session。
4. 成功打开 Codex Workspace。
5. 发送“只回复 LMT_SITULA_OK”，Codex 返回 `LMT_SITULA_OK`。
6. Thread 数量从 0 变为 1，历史对话可见。

## 截图

- `Sandbox/screenshots/situla-tools.png`
- `Sandbox/screenshots/situla-workspace.png`
- `Sandbox/screenshots/situla-chat-ok.png`

结论：Situla 的 Tool 查询、Session 选择、工作区打开、Thread 与 Codex 消息链路完整通过。
