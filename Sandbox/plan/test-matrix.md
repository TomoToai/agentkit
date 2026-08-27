# AgentKit Sandbox 全量实操测试矩阵

状态说明：`待执行`、`进行中`、`通过`、`失败`、`阻塞`、`不适用`。

| ID | 场景 | 主要验证项 | 计划资源名 | 当前状态 | 关键前置条件 |
|---|---|---|---|---|---|
| ENV-01 | 本机环境 | CLI、运行时、Docker、凭证、默认配置 | 无 | 通过 | 无 |
| CODE-01 | Code Sandbox 创建 | CodeEnv、4 vCPU、公共网络、快照 | `lmt-code-sandbox` | 通过 | Tool `t-yesbuwp8n4nlc0d1q5hi` |
| CODE-02 | Session 与 Codex | 创建/复用 Session，运行 Codex | `lmt-code-session` | 通过 | Codex 与 OpenCode 均完成模型调用 |
| CODE-03 | 文件上传下载 | `sandbox scp` 双向传输与内容校验 | 复用 CODE-02 | 通过 | SHA-256 一致，cmp=0 |
| CODE-04 | Web 预览 | `sandbox web --no-open` 返回可访问地址 | 复用 CODE-02 | 通过 | 地址生成成功，认证参数不落盘 |
| CODE-05 | 快照恢复 | Session 到期或重建后恢复工作区 | 复用 CODE-01 | 阻塞 | 已启用快照；资源需保留且 Session 尚未到期，无法执行恢复阶段 |
| TOS-01 | TOS 挂载 | 指定 Bucket、挂载 `/home/gem/workspace`、持久化文件 | `lmt-tos-sandbox` | 阻塞 | Bucket 配额已满；复用 `lmt-dataset` 后 s3fs 已挂载，但对象未跨 Session 可见 |
| INT-01 | 后端接口集成 | ensure_session、Endpoint 生命周期与安全边界 | 复用 CODE-01 | 通过 | `lmt-backend-session` 返回 `LMT_BACKEND_SESSION_OK` |
| SITULA-01 | Situla 集成 | 启动、选择 Tool/Session、对话与工作空间 | 复用 CODE-01 | 通过 | 返回 `LMT_SITULA_OK`，截图已保存 |
| AIO-01 | AIO Sandbox | Agent 调用 `run_code` 执行 Python/Shell | `lmt-aio-test-agent` | 通过 | 返回 `LMT_AIO_OK=5050` |
| SKILL-01 | Skills Sandbox | VeADK Agent 加载并执行 Skill | `lmt-skills-sandbox` | 通过 | xlsx Skill 产物已下载验证 |
| SKILL-02 | Skills A2A | `sandbox invoke` 或样例脚本完成 A2A 调用 | 复用 SKILL-01 | 通过 | OpenAI 兼容 provider Session 成功 |
| CUSTOM-01 | 自定义镜像初始化 | 生成并审查 Dockerfile | `lmt-custom-sandbox` | 通过 | Dockerfile 已生成，待定制依赖 |
| CUSTOM-02 | 云端镜像构建 | Code Pipeline 构建并产出镜像 | `lmt-custom-sandbox-image:v1` | 通过 | Pipeline `1a999d9f449f4ee49f216f80df06b4d0`；镜像已被 Private Tool 接受 |
| CUSTOM-03 | Private Sandbox | 使用自定义镜像创建并验证 Tool | `lmt-custom-sandbox` | 通过 | Tool `t-yesbywpurkkgnctgwj32`；返回 `LMT_CUSTOM_IMAGE_OK=true` |
| ARKCLAW-01 | ArkClaw Sandbox | 创建、Session、基础助手能力 | `lmt-arkclaw-sandbox` | 通过 | A2A 返回 `LMT_ARKCLAW_OK` |
| HERMES-01 | Hermes Sandbox | 创建、Session、基础助手能力 | `lmt-hermes-sandbox` | 阻塞 | 资源/Session Ready；三次 A2A 均退出 0 但无 Agent 内容 |
| JANUS-01 | Janus Sandbox | 浏览器协同可用性与入口验证 | `lmt-janus-sandbox` | 不适用 | 用户明确要求跳过 |
| DEV-01 | Dev Sandbox | DevEnv 创建、Session 启动、Shell 基础能力 | `lmt-dev-sandbox` | 通过 | Tool `t-yesbxj34e8nlc0d1o68e`；Session `lmt-dev-session` |
| STUDIO-01 | VeADK Studio（历史） | 本地启动、识别 Code/ArkClaw/Hermes | 复用已有 Tool | 不适用 | 隔离版 1.0.10 历史验证通过，现已废弃 |
| STUDIO-02 | VeADK Studio SSO | 飞书 SSO、通用/Codex/OpenClaw/Hermes | 线上 SSO 入口 | 阻塞 | SSO/通用通过；Codex 为空，OpenClaw/Hermes HTTP 503 未配置 |
| DOC-01 | 飞书记录文档 | 创建并持续记录全部实操 | 无 | 通过 | 文档 `Nlbxdx3gRoKz1KxdfvlcWyy9nwg` |
| FINAL-01 | 总体验收 | 覆盖率、资源清单、问题与差异 | 无 | 通过 | 已生成 `reports/final-acceptance.md`，阻塞项已单列 |

## 执行顺序

1. 环境与认证。
2. Code Sandbox 基础闭环。
3. 文件、Web、快照与集成调用。
4. AIO、Skills、A2A。
5. ArkClaw、Hermes、Studio。
6. TOS、自定义镜像等高成本资源。
7. Janus、Dev 等 WIP 能力核验。
8. 汇总验收并保留资源。

## 验收规则

- 仅命令退出码为 0 不足以判定通过，必须检查返回对象和实际行为。
- 每项至少保留一种证据：脱敏日志、文件校验、截图、资源链接或 API 返回摘要。
- WIP、权限不足或产品未开放必须记录可复核证据，并标记为“阻塞”，不得伪造通过。
