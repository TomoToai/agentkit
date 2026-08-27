# 影腾摄像头客服 Agent Demo

这是一个面向 AgentKit Gateway 演示的监控摄像头“存量应用系统”。一期使用模拟数据，不连接真实摄像头或视频流。

## 一键启动

```bash
cd APIG
cp .env.example .env
python3 server.py
```

打开 <http://127.0.0.1:8000>。将 `.env.example` 中的 `BUSINESS_API_KEY` 替换为随机强密钥后，5 个存量业务 API 均要求 `X-API-Key`。健康检查和 Agent 对话入口不属于本项 API Key 鉴权范围。

## 核心链路

```text
Web 控制台 → 存量 REST API（X-API-Key）
                         ↑
AgentKit Agent → MCP 工具集 → HTTP 转 MCP
        ↓
模型网关（主模型 + Fallback 备用模型）
```

## 目录

- `server.py`：零第三方依赖的 Web/API 服务
- `static/`：摄像头管理控制台
- `openapi.yaml`：供 HTTP 转 MCP 上传的 API 文件
- `agent/`：VeADK/AgentKit Runtime 接入样例
- `docs/`：完整方案、配置与演示说明
- `tests/`：API 自动化测试

## 测试

```bash
python3 -m unittest discover -s tests -v
```

完整联调预检：

```bash
set -a
. ./.env
set +a
bash scripts/preflight.sh
```

将后端部署到公网 HTTPS 地址后，脚本会生成 `build/openapi.gateway.yaml`，该文件的 `servers.url` 已替换成真实地址，可直接上传到 HTTP 转 MCP。

## 演示账号与安全

五个存量业务 API 使用 `X-API-Key` 校验，密钥由部署环境的 `BUSINESS_API_KEY` 注入；缺失或错误 Key 均返回 `401`。审计日志只记录认证结果，不记录 Key 原文。下一项作业再将同一 Key 托管为 MCP 出站凭据；在此之前，MCP 调用这些受保护接口预期返回 `401`。
