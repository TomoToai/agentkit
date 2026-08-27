# 后端集成实操记录

## 目标

验证应用后端通过稳定的 Tool ID 和 Session ID 实现 `ensure_session` 语义，并把临时 Endpoint 与 Authorization 的生命周期交给 AgentKit CLI 管理。

## 资产

- 脚本：`Sandbox/samples/backend-integration/ensure_session.sh`
- 复用 Tool：`lmt-code-sandbox`（`t-yesbuwp8n4nlc0d1q5hi`）
- Session：`lmt-backend-session`

## 安全边界

- 应用配置只保存 Tool ID、Session ID。
- Endpoint 中的临时 Authorization 不打印、不写文件、不进入飞书文档。
- AK/SK 仅由运行环境注入。
