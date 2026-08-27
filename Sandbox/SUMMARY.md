# AgentKit Sandbox 实操汇总

> 对应飞书文档：[AgentKit Sandbox 全量实操记录｜lmt](https://bytedance.larkoffice.com/docx/Nlbxdx3gRoKz1KxdfvlcWyy9nwg)

## 1. 总体结论

本工作区完成了原文档中可用的 AgentKit Sandbox 核心链路实操。Code、AIO、Skills、ArkClaw、Situla、DevEnv、后端集成以及自定义镜像与 Private Sandbox 均通过验证。VeADK Studio 已切换到飞书 SSO 线上入口；基础访问和通用智能体通过，专项 Sandbox 集成待管理员配置。

当前保留三个有证据的外部阻塞：Hermes A2A 无 Agent 内容、TOS 对象未跨 Session 持久化、快照需等待 Session 到期后才能验证恢复。Janus 按要求跳过。

## 2. 状态总览

| 能力 | 状态 | 验证信号 |
|---|---|---|
| Code Sandbox | 通过 | Shell、Codex、OpenCode、SCP、Web |
| AIO | 通过 | `LMT_AIO_OK=5050` |
| Skills | 通过 | xlsx Skill 产物下载并检查 |
| ArkClaw | 通过 | `LMT_ARKCLAW_OK` |
| Situla | 通过 | `LMT_SITULA_OK` |
| VeADK Studio | 部分通过 | SSO 与通用智能体通过；Codex 为空，OpenClaw/Hermes 未配置 |
| DevEnv | 通过 | `LMT_DEV_SANDBOX_OK` |
| 后端集成 | 通过 | `LMT_BACKEND_SESSION_OK` |
| 自定义镜像 | 通过 | `LMT_CUSTOM_IMAGE_OK=true` |
| Hermes | 阻塞 | Tool/Session Ready，三次 A2A 无内容 |
| TOS 持久化 | 阻塞 | s3fs 已挂载，写入未跨 Session 可见 |
| 快照恢复 | 阻塞 | 已启用快照，等待 Session 到期窗口 |
| Janus | 不适用 | 按要求跳过 |

## 3. 保留的云端资源

| 类型 | 名称 | Tool/资源 ID | 主要 Session |
|---|---|---|---|
| CodeEnv | `lmt-code-sandbox` | `t-yesbuwp8n4nlc0d1q5hi` | `lmt-code-session`、`lmt-backend-session` |
| ArkClawEnv | `lmt-arkclaw-sandbox` | `t-yesbw1xywwkgnctgyqfy` | `lmt-arkclaw-session` |
| HermesEnv | `lmt-hermes-sandbox` | `t-yesbw3te68kgnctgvcvj` | `lmt-hermes-session` |
| SkillEnv | `lmt-skills-sandbox` | `t-yesbwpgzcweuszqwt14h` | `lmt-skills-openai-session` |
| DevEnv | `lmt-dev-sandbox` | `t-yesbxj34e8nlc0d1o68e` | `lmt-dev-session` |
| TOS CodeEnv | `lmt-tos-sandbox` | `t-yesby5hedceuszqwvmy9` | `lmt-tos-session`、`lmt-tos-session-2` |
| Private | `lmt-custom-sandbox` | `t-yesbywpurkkgnctgwj32` | `lmt-custom-session` |
| CR Image | `lmt-custom-sandbox-image:v1` | namespace `limengtao_agentkit` | — |
| Code Pipeline | 镜像构建流水线 | `1a999d9f449f4ee49f216f80df06b4d0` | — |

所有资源均按要求保留。AK、SK、模型密钥和临时 Authorization 不在本目录落盘。

## 4. 关键代码与命令

### 4.1 创建并调用 Code Sandbox

```bash
agentkit sandbox create \
  --tool-type CodeEnv \
  --tool-name lmt-code-sandbox \
  --cpu 4 \
  --network-public \
  --enable-snapshot

agentkit sandbox shell \
  --tool-id t-yesbuwp8n4nlc0d1q5hi \
  --sid lmt-code-session \
  --command 'printf LMT_CODE_SANDBOX_OK'
```

### 4.2 后端 `ensure_session` 入口

实际文件：`samples/backend-integration/ensure_session.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${LMT_TOOL_ID:?set LMT_TOOL_ID}"
: "${LMT_SESSION_ID:=lmt-backend-session}"

agentkit sandbox shell \
  --tool-id "$LMT_TOOL_ID" \
  --tool-type CodeEnv \
  --sid "$LMT_SESSION_ID" \
  --command 'printf LMT_BACKEND_SESSION_OK'
```

应用层只保存稳定的 Tool ID 和 Session ID；临时 Endpoint/Authorization 交给 AgentKit CLI 管理。

### 4.3 VeADK AIO 调用 Code Tool

实际文件：`samples/aio/run_code_agent.py`

```python
import asyncio
from veadk import Agent, Runner
from veadk.tools.builtin_tools.run_code import run_code

async def main() -> None:
    agent = Agent(
        name="lmt_aio_test_agent",
        model_name="glm-5-2-260617",
        instruction=(
            "必须调用 run_code 工具，用 Python 计算 1 到 100 的整数之和。"
            "完成后只输出 LMT_AIO_OK=计算结果。"
        ),
        tools=[run_code],
    )
    runner = Runner(agent=agent)
    print(await runner.run(
        messages="执行测试",
        user_id="lmt-user",
        session_id="lmt-aio-session",
    ))

asyncio.run(main())
```

### 4.4 Skills 与助手型 Sandbox

```bash
agentkit sandbox invoke \
  --tool-id '<skill-or-assistant-tool-id>' \
  --sid '<lmt-session-id>' \
  --tool-type SkillEnv \
  --prompt '执行指定 Skill，并返回验证结果' \
  --timeout 300
```

ArkClaw 和 Hermes 使用相同的 A2A 入口，将 `--tool-type` 分别替换为 `ArkClawEnv`、`HermesEnv`。实际密钥只从环境变量注入。

### 4.5 TOS 挂载

```bash
agentkit sandbox create \
  --tool-type CodeEnv \
  --tool-name lmt-tos-sandbox \
  --tos-bucket lmt-dataset \
  --tos-mount /home/gem/workspace \
  --cpu 4 \
  --network-public \
  --enable-snapshot
```

验证时必须同时检查挂载类型、沙箱内读写、TOS API 回读和第二 Session 可见性，不能只以 Shell 退出码判定持久化成功。

### 4.6 自定义镜像 Dockerfile

实际文件：`samples/custom-sandbox/Dockerfile`

```dockerfile
FROM enterprise-public-cn-beijing.cr.volces.com/vefaas-public/code-cli:0.0.7

ENV PATH="/opt/nodejs/22/bin:${PATH}"

RUN npm install -g \
        is-even@1.0.0
```

构建、创建和验证：

```bash
agentkit sandbox build \
  --project-dir Sandbox/samples/custom-sandbox \
  --dockerfile Dockerfile \
  --image-name lmt-custom-sandbox-image \
  --repo lmt-custom-sandbox-image \
  --tag v1 \
  --namespace limengtao_agentkit

agentkit sandbox create \
  --tool-type Private \
  --tool-name lmt-custom-sandbox \
  --image-url '<registry>/limengtao_agentkit/lmt-custom-sandbox-image:v1' \
  --cpu 4 \
  --network-public \
  --enable-snapshot

agentkit sandbox shell \
  --tool-id t-yesbywpurkkgnctgwj32 \
  --tool-type Private \
  --sid lmt-custom-session \
  --command 'node -e "const f=require(\"/opt/nodejs/22/lib/node_modules/is-even\"); console.log(\"LMT_CUSTOM_IMAGE_OK=\"+f(42))"'
```

### 4.7 Situla 与 VeADK Studio

```bash
situla start
```

VeADK Studio 后续统一使用飞书 SSO 入口：

`https://sicjgimgi9920l1mcqqdg.apigateway-cn-beijing.volceapi.com/`

旧的 `uvx veadk-python==1.0.10 veadk studio` 本地启动方式已废弃。当前线上入口已验证 SSO 和通用智能体；Codex 列表为空，OpenClaw/Hermes 仍需管理员配置。

## 5. 本地资产索引

- 总验收：`reports/final-acceptance.md`
- 完整矩阵：`plan/test-matrix.md`
- Code：`reports/code-sandbox-smoke.md`
- AIO/ArkClaw/Hermes：`reports/assistant-sandboxes.md`
- Skills：`reports/skills-sandbox.md`
- Situla：`reports/situla.md`
- Studio：`reports/veadk-studio.md`
- DevEnv：`reports/dev-sandbox.md`
- 后端集成：`reports/backend-integration.md`
- TOS：`reports/tos-mount.md`
- 自定义镜像：`reports/custom-sandbox.md`
- 截图：`screenshots/`
- 下载产物：`logs/lmt-skills-output.xlsx`

## 6. 后续可直接执行

1. Session 到期后复验快照恢复。
2. 在控制台核查 `lmt-tos-sandbox` 的 TOS 角色和对象前缀映射，再做 API/跨 Session 回读。
3. 检查 Hermes 服务端模型和 A2A 输出日志，定位“成功退出但正文为空”。
