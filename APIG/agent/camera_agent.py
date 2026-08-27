"""VeADK AgentKit Runtime example for the camera operations demo.

Install the current AgentKit/VeADK SDK versions before running. The concrete MCP
client import may vary by SDK release; keep gateway values in environment vars.
"""

import logging
import os

from agentkit.apps import AgentkitSimpleApp
from veadk import Agent, Runner

logger = logging.getLogger(__name__)
app = AgentkitSimpleApp()

INSTRUCTION = """
你是影腾摄像头客服与诊断助手。你必须先调用摄像头 MCP 工具取得事实，再回答设备状态和故障原因。
诊断时按设备定位、设备详情、诊断指标、近期告警的顺序收集证据，并区分供电、网络、存储和画面问题。
更新检修状态属于写操作：只有用户明确确认后才能调用 update_camera_maintenance_status。
回答中说明调用了哪些数据，并给出简短、可执行的排障步骤；不要声称分析了真实视频画面。
""".strip()

# MCP 工具集在 AgentKit Runtime 控制台关联，或按当前 VeADK 版本创建 MCP
# client 后传入 tools。模型网关使用 OpenAI-compatible endpoint 环境变量。
agent = Agent(
    name="yingteng_camera_support",
    instruction=INSTRUCTION,
    model_name=os.getenv("MODEL_AGENT_NAME", "camera-primary-route"),
)
runner = Runner(agent=agent)


@app.entrypoint
async def run(payload: dict, headers: dict) -> str:
    prompt = payload["prompt"]
    user_id = headers.get("user_id", "camera-demo-user")
    session_id = headers.get("session_id", "camera-demo-session")
    logger.info("camera agent request user=%s session=%s", user_id, session_id)
    return await runner.run(messages=prompt, user_id=user_id, session_id=session_id)


@app.ping
def ping() -> str:
    return "pong!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

