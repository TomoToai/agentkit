# VeADK Studio 验证报告

## 2026-08-10：切换到飞书 SSO Studio

### 推荐入口

- 地址：`https://sicjgimgi9920l1mcqqdg.apigateway-cn-beijing.volceapi.com/`
- 页面标题：`AgentKit Studio`
- 认证：飞书账号 SSO
- 实际身份：李孟桃，管理员

### 最新验证结果

1. 入口可正常打开，无需本地启动 VeADK。
2. 飞书 SSO 自动登录成功，页面展示管理员身份及企业邮箱。
3. 通用智能体列表加载成功，可浏览北京地域 Runtime。
4. Codex 智能体列表当前为空。
5. OpenClaw 接口 `/web/openclaw/sessions` 返回 HTTP 503：管理员未配置。
6. Hermes 接口 `/web/hermes/sessions` 返回 HTTP 503：管理员未配置。

最新截图：`Sandbox/screenshots/veadk-studio-sso.png`。

结论：此 SSO 地址是后续唯一推荐入口。Studio 基础访问、SSO 和通用智能体通过；Codex、OpenClaw、Hermes 仍需管理员配置后复验。

## 历史验证（已废弃）

以下本地 `uvx veadk-python==1.0.10` 方案仅保留为历史实操证据，不再作为启动或访问方式。

执行时间：2026-08-07（Asia/Shanghai）

## 版本差异

- 全局 VeADK：0.2.22，不提供 `frontend` 或 `studio` 命令。
- 原文要求：`veadk-python==1.0.10`。
- 使用 uv 隔离运行 1.0.10 后，确认同时提供 `frontend` 与 `studio`。
- 未修改或覆盖全局 VeADK。

## 启动参数

- 本地地址：`http://127.0.0.1:8000`
- Code Tool：`t-yesbuwp8n4nlc0d1q5hi`
- ArkClaw Tool：`t-yesbw1xywwkgnctgyqfy`
- Hermes Tool：`t-yesbw3te68kgnctgvcvj`
- Skill Creator Tool：复用 Code Tool
- 本地测试用户：`lmttest`

## 验证结果

1. Studio 首页与本地用户名登录通过。
2. 通用智能体列表可读取 AgentKit Runtime。
3. Codex 分类显示本次 Code Sandbox 的两个 Session，状态就绪。
4. OpenClaw 分类显示本次 ArkClaw Session，状态就绪。
5. Hermes 分类显示本次 Hermes Session，状态就绪。
6. 后端 `/web/sandbox/sessions`、`/web/openclaw/sessions`、`/web/hermes/sessions` 均返回 200。

## 截图

- `Sandbox/screenshots/veadk-studio-agents.png`

历史结论：隔离版 VeADK 1.0.10 曾完成本地集成验证，但该入口现已废弃，后续统一使用飞书 SSO Studio。
