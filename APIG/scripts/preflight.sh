#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[1/5] 本地 API 测试"
python3 -m unittest discover -s tests -v

echo "[2/5] Python 语法检查"
python3 -m py_compile server.py agent/camera_agent.py scripts/smoke_test.py scripts/render_openapi.py

echo "[3/5] AgentKit 登录状态"
agentkit whoami || true

echo "[4/5] 公网后端"
if [[ -n "${CAMERA_PUBLIC_BASE_URL:-}" ]]; then
  python3 scripts/render_openapi.py
  python3 scripts/smoke_test.py
else
  echo "未配置 CAMERA_PUBLIC_BASE_URL，跳过公网冒烟测试"
fi

echo "[5/5] 云端必需变量"
for name in RUNTIME_API_KEY CAMERA_PUBLIC_BASE_URL MODEL_AGENT_NAME MODEL_AGENT_API_KEY MODEL_ENDPOINT AGENTKIT_MCP_SERVER_URL AGENTKIT_MCP_API_KEY; do
  if [[ -n "${!name:-}" ]]; then echo "$name=已配置"; else echo "$name=未配置"; fi
done
