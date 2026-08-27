# AIO、ArkClaw 与 Hermes 阶段报告

执行时间：2026-08-07（Asia/Shanghai）

## AIO / run_code

- 样例：`Sandbox/samples/aio/run_code_agent.py`
- Agent 名称：`lmt_aio_test_agent`
- Agent Session：`lmt-aio-session`
- 复用 Tool：`lmt-code-sandbox`（`t-yesbuwp8n4nlc0d1q5hi`）
- 工具：`veadk.tools.builtin_tools.run_code`
- 任务：使用远端 Python 计算 1 到 100 的整数之和
- 结果：`LMT_AIO_OK=5050`

结论：VeADK Agent → 模型工具调用 → AgentKit RunCode → 远端 Python → Agent 最终回复的完整链路通过。

## ArkClaw

- Tool 名称：`lmt-arkclaw-sandbox`
- Tool ID：`t-yesbw1xywwkgnctgyqfy`
- Session：`lmt-arkclaw-session`
- Instance：`s-yesbw5x8u8kgnctgyjjq`
- A2A 结果：`LMT_ARKCLAW_OK`

结论：资源创建、Session 与 A2A 调用通过。

## Hermes

- Tool 名称：`lmt-hermes-sandbox`
- Tool ID：`t-yesbw3te68kgnctgvcvj`
- Session：`lmt-hermes-session`
- Instance：`s-yesbw9ih34nlc0d1p4cb`
- A2A 结果：两次调用均以退出码 0 完成，但没有返回 Agent 内容

结论：资源与 Session 创建通过，A2A 返回内容异常，状态为“部分通过/待诊断”。

## 安全说明

上述调用返回的完整 Endpoint 含临时 Authorization，未写入本报告。
