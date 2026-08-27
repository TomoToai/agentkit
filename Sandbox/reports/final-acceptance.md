# AgentKit Sandbox 全量实操验收报告

## 结论

原文档涉及的可用能力已完成实操。Janus 按用户要求跳过；Hermes、TOS 持久化和快照恢复存在可复核的外部条件阻塞，其余核心链路均通过。

## 已通过

- Code Sandbox：Shell、Codex、OpenCode、SCP、Web 预览。
- AIO：VeADK Agent 调用 Code Tool，返回 `LMT_AIO_OK=5050`。
- Skills：列出并执行 xlsx Skill，产物已下载。
- ArkClaw：A2A 返回 `LMT_ARKCLAW_OK`。
- Situla：资源、Session、工作区与聊天验证通过。
- VeADK Studio：历史本地方案曾完成资源识别；现已切换飞书 SSO 入口，SSO/通用智能体通过，专项 Sandbox 集成待配置。
- DevEnv：返回 `LMT_DEV_SANDBOX_OK`。
- 后端集成：`ensure_session` 样例返回 `LMT_BACKEND_SESSION_OK`。
- 自定义镜像：Code Pipeline + CR + Private Tool 完成，返回 `LMT_CUSTOM_IMAGE_OK=true`。

## 阻塞或不适用

- Hermes：Tool/Session Ready，但三次 A2A 调用无 Agent 内容。
- TOS：账号 Bucket 配额已满；复用 `lmt-dataset` 后 s3fs 挂载存在，但对象未跨 Session 持久化，需核查 Tool 的 TOS 角色或前缀映射。
- 快照恢复：创建时已启用快照；因 Session 尚未到期且用户要求保留资源，当前无法验证到期恢复阶段。
- Janus：用户明确要求跳过。

## 保留的主要资源

| 类型 | 名称 | 标识 |
|---|---|---|
| CodeEnv | `lmt-code-sandbox` | `t-yesbuwp8n4nlc0d1q5hi` |
| ArkClawEnv | `lmt-arkclaw-sandbox` | `t-yesbw1xywwkgnctgyqfy` |
| HermesEnv | `lmt-hermes-sandbox` | `t-yesbw3te68kgnctgvcvj` |
| SkillEnv | `lmt-skills-sandbox` | `t-yesbwpgzcweuszqwt14h` |
| DevEnv | `lmt-dev-sandbox` | `t-yesbxj34e8nlc0d1o68e` |
| TOS CodeEnv | `lmt-tos-sandbox` | `t-yesby5hedceuszqwvmy9` |
| Private | `lmt-custom-sandbox` | `t-yesbywpurkkgnctgwj32` |
| Image | `lmt-custom-sandbox-image:v1` | CR namespace `limengtao_agentkit` |
| Pipeline | 镜像构建流水线 | `1a999d9f449f4ee49f216f80df06b4d0` |

所有云端资源均按要求保留。临时 Authorization、AK、SK、模型密钥未写入报告或飞书文档。
