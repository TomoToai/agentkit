## 关键代码与复现入口

> 以下代码均来自本次实际验证资产，并已移除 AK、SK、模型 Key 和临时 Authorization。

### 1. Code Sandbox 创建与调用

```bash
agentkit sandbox create \
  --tool-type CodeEnv \
  --tool-name lmt-code-sandbox \
  --cpu 4 --network-public --enable-snapshot

agentkit sandbox shell \
  --tool-id t-yesbuwp8n4nlc0d1q5hi \
  --sid lmt-code-session \
  --command 'printf LMT_CODE_SANDBOX_OK'
```

### 2. 后端 ensure_session

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

应用层只保存稳定的 Tool ID 和 Session ID，临时 Endpoint/Authorization 由 AgentKit CLI 管理。

### 3. VeADK AIO 调用 Code Tool

```python
import asyncio
from veadk import Agent, Runner
from veadk.tools.builtin_tools.run_code import run_code

async def main():
    agent = Agent(
        name="lmt_aio_test_agent",
        model_name="glm-5-2-260617",
        instruction="必须调用 run_code，用 Python 计算 1 到 100 的和；只输出 LMT_AIO_OK=结果。",
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

实际返回：`LMT_AIO_OK=5050`。

### 4. TOS 挂载

```bash
agentkit sandbox create \
  --tool-type CodeEnv \
  --tool-name lmt-tos-sandbox \
  --tos-bucket lmt-dataset \
  --tos-mount /home/gem/workspace \
  --cpu 4 --network-public --enable-snapshot
```

验收必须同时检查 s3fs 挂载、沙箱读写、TOS API 回读及第二 Session 可见性。本次挂载存在，但跨 Session 持久化未成立。

### 5. 自定义镜像

```dockerfile
FROM enterprise-public-cn-beijing.cr.volces.com/vefaas-public/code-cli:0.0.7
ENV PATH="/opt/nodejs/22/bin:${PATH}"
RUN npm install -g is-even@1.0.0
```

```bash
agentkit sandbox build \
  --project-dir Sandbox/samples/custom-sandbox \
  --dockerfile Dockerfile \
  --image-name lmt-custom-sandbox-image \
  --repo lmt-custom-sandbox-image \
  --tag v1 \
  --namespace limengtao_agentkit

agentkit sandbox shell \
  --tool-id t-yesbywpurkkgnctgwj32 \
  --tool-type Private \
  --sid lmt-custom-session \
  --command 'node -e "const f=require(\"/opt/nodejs/22/lib/node_modules/is-even\"); console.log(\"LMT_CUSTOM_IMAGE_OK=\"+f(42))"'
```

实际返回：`LMT_CUSTOM_IMAGE_OK=true`。

### 6. Situla 与 VeADK Studio

```bash
situla start
```

VeADK Studio 后续统一使用飞书 SSO 线上入口：

`https://sicjgimgi9920l1mcqqdg.apigateway-cn-beijing.volceapi.com/`

旧的本地 `uvx veadk-python==1.0.10 veadk studio` 启动方式已废弃。

### 7. 本地汇总入口

- `Sandbox/SUMMARY.md`：状态、资源、关键代码和证据的统一入口。
- `Sandbox/plan/test-matrix.md`：逐项测试状态。
- `Sandbox/reports/final-acceptance.md`：最终验收结论。
