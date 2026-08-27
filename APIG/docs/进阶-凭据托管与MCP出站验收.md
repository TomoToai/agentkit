# 进阶：凭据托管 API Key + MCP 出站凭据验收

> 本记录只保存非敏感证据。不得记录 API Key 值、请求头原文、模型网关 Key、Runtime Key 或云账号 AK/SK。

## 目标

让 Agent 通过 `yingteng_test` MCP 工具集访问受 `X-API-Key` 保护的存量业务 API，同时保证 API Key 只存在于凭据托管和服务端环境，不进入 Agent 代码、镜像、浏览器或普通日志。

## 配置结果

| 项目 | 结果 |
| --- | --- |
| 凭据名称 | `yingteng_business_api_key` |
| 凭据类型 | API Key 凭据托管 |
| 出站参数位置 | Header |
| 出站参数名称 | `X-API-Key` |
| MCP 工具集 | `yingteng_test` |
| 关联 MCP 服务 | `yingteng_camera_v3` |
| MCP 服务状态 | `Ready`（控制面只读清单） |
| 绑定完成时间 | 2026-08-16（以控制台操作记录为准） |

## 密钥一致性

存量应用代码读取环境变量 `BUSINESS_API_KEY`；本地同名值保存在被 Git 忽略的 `.env` 中。凭据托管中保存同一值，MCP 出站请求注入 `X-API-Key`。密钥值不写入仓库或本文档。

## 待补充的端到端证据

完成云上应用滚动部署后，需要分别保存：

1. 无 `X-API-Key` 请求返回 `401`；
2. 错误 Key 请求返回 `401`；
3. 通过 MCP 出站托管凭据访问返回 `200`，并能完成 CAM-003 诊断；
4. 应用审计日志仅记录认证结果，不记录请求头原文。

VKE Deployment 已完成保密字典注入并恢复 `就绪 1/1`；在上述三组请求和 CAM-003 诊断证据完成前，本项状态为“凭据托管与 MCP 出站配置完成，端到端验收待补”。

补充证据：已推送 `yingteng-camera-web:20260816-2331`，刷新 VKE 镜像拉取凭据并完成滚动更新，公网 `openapi.yaml` 已显示 `ApiKeyAuth`。2026-08-16 23:49 对受保护的 `/api/cameras` 实测为无 Key `401`、错误 Key `401`、正确 Key `200`；MCP 出站凭据与 Agent 端到端诊断仍需单独补充。

## CAM-003 触发结果（2026-08-16）

已通过公网 `/api/agent/chat` 触发一次真实 CAM-003 诊断。Runtime `yingteng-camera-support` 可正常响应，但 `yingteng_test` 的 `get_camera`、`diagnose_camera`、`list_camera_alerts`、`list_cameras` 均返回 `401 缺少或无效的 X-API-Key`。这证明请求链路已触发，剩余阻塞在 MCP 出站凭据实际注入/绑定；详细非敏感记录见 `docs/evidence/CAM-003诊断-20260816-235x.md`。

## 修复与成功证据（2026-08-17）

### 根因

控制面页面曾显示已选择 `yingteng_business_api_key`，但 MCP 服务实际运行配置未携带该凭据；调试工具调用返回 `401 api_key_invalid`。通过 AgentKit SDK 只读核验，服务此前的出站授权为空；重新保存页面配置后，仍需同步校准凭据托管中的密钥值。

### 修复

已使用项目根 `.env` 中的 `BUSINESS_API_KEY` 更新凭据托管对象 `yingteng_business_api_key`，并保留 Header 位置 `X-API-Key`。未将密钥值写入仓库、日志或本记录。

### 验收结果

- MCP 控制台调试 `diagnose_camera(camera_id=CAM-003)`：成功返回设备诊断数据。
- 诊断数据包含：网络 `critical`、丢包率 `38.4%`、延迟 `486ms`、供电正常、存储正常、温度 `47°C`、画面间歇中断。
- 公网 `/api/agent/chat` 再次触发 CAM-003：Agent 成功获取设备详情、诊断指标和 2 条活跃告警，并给出网络排障建议。
- 业务链路现已恢复：`Agent Runtime → yingteng_test → yingteng_camera_v3 → 托管 X-API-Key → APIG 存量 API`。
