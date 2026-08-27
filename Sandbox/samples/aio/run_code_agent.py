"""Minimal VeADK Agent -> AgentKit run_code integration test.

Credentials and model settings are supplied by the process environment.
No secret is read from or written to this file.
"""

import asyncio

from veadk import Agent, Runner
from veadk.tools.builtin_tools.run_code import run_code


async def main() -> None:
    agent = Agent(
        name="lmt_aio_test_agent",
        model_name="glm-5-2-260617",
        description="AgentKit AIO sandbox integration test agent",
        instruction=(
            "必须调用 run_code 工具，用 Python 计算 1 到 100 的整数之和。"
            "完成后只输出 LMT_AIO_OK=计算结果。"
        ),
        tools=[run_code],
    )
    runner = Runner(agent=agent)
    response = await runner.run(
        messages="执行测试",
        user_id="lmt-user",
        session_id="lmt-aio-session",
    )
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
