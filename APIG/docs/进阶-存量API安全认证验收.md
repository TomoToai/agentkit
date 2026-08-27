# 进阶：存量应用系统 API Key 安全认证验收

> 本记录只保存非敏感证据；不得记录 `BUSINESS_API_KEY` 的值、请求头原文、模型网关 Key、Runtime Key 或云账号 AK/SK。

## 目标与边界

为可转换为 MCP 工具的 5 个存量业务 API 增加 API Key 鉴权：

| 方法 | 路径 |
| --- | --- |
| `GET` | `/api/cameras` |
| `GET` | `/api/cameras/{camera_id}` |
| `GET` | `/api/cameras/{camera_id}/diagnostics` |
| `GET` | `/api/alerts` |
| `PATCH` | `/api/cameras/{camera_id}/maintenance-status` |

鉴权头固定为 `X-API-Key`。`/health` 保持免鉴权供探针使用；`/api/agent/chat` 不属于本项存量业务 API 鉴权范围。

## 实现

1. `server.py` 仅读取 `BUSINESS_API_KEY`：云上优先从进程环境变量注入；本地在环境变量缺失时仅从被 Git 忽略的 `APIG/.env` 或项目根 `.env` 读取这一字段。
2. 使用 `hmac.compare_digest` 比较请求头与配置值，避免普通字符串比较的时序差异；密钥未配置、缺失或错误时均以通用错误返回 `401`，实现 fail-closed。
3. 审计日志只记录 `authenticated: true/false`，不记录 `X-API-Key` 或其他请求头。
4. 源码扫描生成的 `openapi.generated.yaml` 与供 MCP 使用的 `openapi.yaml` 都声明全局 `ApiKeyAuth`：`type: apiKey`、`in: header`、`name: X-API-Key`。

本地配置示例见 `APIG/.env.example`；其中只是占位值，部署前必须由随机强密钥替换，禁止提交真实值。

## 已保存验证证据

| 证据编号 | 时间（Asia/Shanghai） | 命令 / 场景 | 结果 |
| --- | --- | --- | --- |
| A-01 | 2026-08-16 20:24:28 | `python3 scripts/generate_openapi_from_source.py …` | 成功生成含 5 个业务 API、`ApiKeyAuth` 与 `X-API-Key` 的 OpenAPI。 |
| A-02 | 2026-08-16 20:24:28 | 生成器 `--check` | 通过，证明 `openapi.generated.yaml` 未与源码漂移。 |
| A-03 | 2026-08-16 20:25:11 | `python3 -m unittest discover -s tests -v` | 11/11 通过：未配置 Key fail-closed `401`、无 Key `401`、错误 Key `401`、正确 Key `200`、写接口无 Key `401`、健康检查 `200`，以及 API / OpenAPI 回归测试。 |

## 当前状态

第一步（应用代码、OpenAPI、自动化验收）已完成并保存证据；云上 Deployment 已完成保密字典注入并恢复就绪，**端到端三组请求尚未完成**。

2026-08-16 23:31 首次误测了不受保护的 `/api/dashboard`，结果为 `200/200/200`，不作为鉴权证据。随后已推送新镜像 `yingteng-camera-web:20260816-2331`，刷新 VKE 拉取凭据并完成滚动更新；公网 `openapi.yaml` 已切换为 `ApiKeyAuth`。2026-08-16 23:49 对受保护的 `/api/cameras` 实测：无 Key `401`、错误 Key `401`、正确 Key `200`，响应分别为 `api_key_invalid`、`api_key_invalid` 和摄像头列表。

云上现有存量系统已注入 `BUSINESS_API_KEY` 并重新部署；仍不要提前将云端 MCP/Agent 的结果当作本项认证验证，需完成 APIG 入口三组请求并保存响应证据。

当前 Web 页面会从浏览器直连受保护的业务 API，因而云上启用 Key 后其数据页会暂时无法加载。这是已确认的简化范围：本项只演示存量 API 鉴权；不在浏览器保存密钥，也不把 Key 写入前端。后续如需恢复 Web 数据页，应另行实现用户登录态 / 服务端 BFF。

## 后续验收顺序

1. 已在云上存量应用的部署环境以 Secret / 环境变量注入 `BUSINESS_API_KEY`，VKE Deployment 已恢复 `就绪 1/1`；保留控制台配置截图（密钥值打码）。
2. 经 APIG 分别发起无 Key、错误 Key、正确 Key 的请求，保存 `401`、`401`、`200` 及请求 ID。
3. 已在凭据托管中创建 `yingteng_business_api_key`，并完成 MCP 出站头 `X-API-Key` 配置；该凭据值不记录在本文档中。
4. 重新验证 `yingteng_test` MCP 和 CAM-003 Agent 诊断，证明 Key 不进入 Agent 代码、镜像、浏览器或普通日志。

## 页面数据恢复（2026-08-17）

API Key 加固后，页面原先直接请求受保护的 `/api/cameras`、`/api/alerts` 等接口，浏览器未携带密钥，导致数据渲染 401。已改为同源服务端 BFF：页面请求携带非敏感的 `X-UI-Proxy: 1` 标记，由后端在认证边界内处理业务数据；密钥仍只存在服务端环境，不下发浏览器。为复用现有 APIG 路由，同时保留 `ui=1` 查询标记。

已发布 `yingteng-camera-web:20260817-0030` 并完成滚动更新（Deployment revision 9，`1/1` Ready）。公网验证结果：摄像头列表 200/6 台、告警列表 200/4 条、CAM-003 诊断 200；直接不带 Key 访问原 `/api/cameras` 仍为 401，原安全边界未被移除。
