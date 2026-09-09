"""影腾摄像头客服 Agent Runtime（WebServer App 模式）。

使用 AgentkitAgentServerApp 暴露标准 Agent Server 接口（/run、/run_sse、
/invoke 及 session API），以便 AgentKit 控制台可以自省模型、工具与拓扑，
消除“该 Runtime 的 Agent Server 未提供连接接口”提示。
"""

import logging
import os

from agentkit.apps import AgentkitAgentServerApp
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from veadk import Agent
from veadk.memory.short_term_memory import ShortTermMemory


logger = logging.getLogger(__name__)


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少必需环境变量 {name}")
    return value


def required_env_any(*names: str) -> str:
    """优先使用显式配置，兼容控制面关联工具集后自动注入的变量。"""
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    raise RuntimeError(f"缺少必需环境变量（任一）：{', '.join(names)}")


def requires_confirmation(tool=None, _args=None, _context=None, **kwargs) -> bool:
    """只有更新检修状态的写工具需要用户确认。"""
    return getattr(tool, "name", "") == "update_camera_maintenance_status"


INSTRUCTION = """
你是影腾摄像头客服与故障诊断助手，服务于园区安防和设备运维人员。

规则：
1. 回答设备状态、故障原因和告警信息前，必须调用摄像头 MCP 工具获取事实，禁止编造数据。
2. 诊断问题时依次完成：定位设备、查询设备详情、获取诊断指标、查询近期告警。
3. 明确区分供电、网络、存储和画面问题，并给出简短、可执行的排障步骤。
4. 当前系统使用确定性的模拟遥测数据，不要声称读取或分析了真实视频画面。
5. update_camera_maintenance_status 是写操作，只有用户明确确认后才可以执行；没有确认时只说明准备执行的变更。
6. 回答时简要列出使用的数据依据，例如设备状态、丢包率、延迟和告警。
7. 当用户咨询产品"如何使用/安装/配网/操作/配置/保养"等使用类问题时：
   - 先确认客户所用摄像头的具体型号（SKU，如 YT-IPC-4K）。若用户未说明型号，
     先调用 list_product_guides 列出候选型号（可用关键词/场景过滤），引导用户选择，
     不要在型号不明时凭空作答。
   - 确认型号后，调用 get_product_guide 检索对应型号的使用指南，依据指南内容回答，
     禁止编造型号参数或操作步骤。
   - 若已知设备编号（如 CAM-003），可先用 get_camera 查出其 model 字段确定型号，
     再检索该型号的使用指南。
""".strip()


mcp_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=required_env_any("MCP_TOOLSET_URL", "TOOL_MCP_ROUTER_URL"),
        headers={
            "Authorization": (
                "Bearer "
                f"{required_env_any('MCP_TOOLSET_API_KEY', 'TOOL_MCP_ROUTER_API_KEY')}"
            )
        },
        timeout=20,
        sse_read_timeout=300,
    ),
    require_confirmation=requires_confirmation,
)

agent = Agent(
    name="yingteng_camera_support",
    description="园区摄像头查询、告警分析与故障诊断助手",
    instruction=INSTRUCTION,
    model_name=required_env("MODEL_AGENT_NAME"),
    # Agent 的推理请求经模型网关转发；LiteLLM 自动补全 /chat/completions。
    model_api_base=required_env("MODEL_GATEWAY_BASE_URL"),
    model_api_key=required_env("MODEL_AGENT_API_KEY"),
    tools=[mcp_toolset],
)


def _build_short_term_memory() -> ShortTermMemory:
    """为 WebServer App 的 session API 提供短期记忆后端。

    默认使用本地后端即可让 session 接口启动；需要跨实例持久化时，
    通过 AGENT_SERVER_SESSION_BACKEND 或控制面关联的会话资源切换。
    """
    backend = os.getenv("AGENT_SERVER_SESSION_BACKEND", "local")
    return ShortTermMemory(backend=backend)


# AgentkitAgentServerApp 暴露标准 Agent Server 接口：/run、/run_sse、/invoke
# 以及 /apps/{app}/users/{user}/sessions/{session} 等 session API。控制台
# 通过这些接口自省 Agent 元数据（模型、工具、拓扑）。身份仍由调用方在
# session API 的 user_id / session_id 维度透传，与既有方案一致。
app = AgentkitAgentServerApp(
    agent=agent,
    short_term_memory=_build_short_term_memory(),
)


def main() -> int:
    host = os.getenv("AGENT_SERVER_HOST", "0.0.0.0")
    # AgentKit Runtime/FaaS 健康检查期望用户进程监听 8000 端口。
    port = int(os.getenv("AGENT_SERVER_PORT", "8000"))
    app.run(host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
