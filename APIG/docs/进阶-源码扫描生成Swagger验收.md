# 进阶验收：从存量源码自动生成 Swagger API 文件

## 验收目标

模拟客户仅交付存量 Python 服务工程、未提供 API 文档的场景。扫描 `server.py` 的 HTTP 路由，自动生成可用于 HTTP 转 MCP 的 OpenAPI 3.0 文件，再以 Agent 的真实诊断结果证明业务 API 可被使用。

## 实现方式

新增扫描器 `scripts/generate_openapi_from_source.py`：

1. 使用 Python AST 扫描 `BaseHTTPRequestHandler` 中的 `do_GET`、`do_POST`、`do_PATCH` 等路由分支。
2. 自动识别精确路径与 `re.fullmatch` 形式的路径参数路由，并将 `CAM-\d+` 转为 `{camera_id}`。
3. 仅输出 5 个可安全转换为 MCP 工具的存量业务 API；`/api/agent/chat`、审计等 Web 管理接口不会进入工具集。
4. 由受控业务目录补充 operationId、参数、写操作请求体和基础响应描述，避免依赖人工维护的路径列表。
5. 内置 `--check`，用于检测生成文件是否与当前源码路由一致。

## 生成与校验命令

```bash
cd APIG
python3 scripts/generate_openapi_from_source.py \
  --source server.py \
  --output openapi.generated.yaml \
  --server-url https://&lt;APIG 公网地址&gt;

python3 scripts/generate_openapi_from_source.py \
  --source server.py \
  --output openapi.generated.yaml \
  --server-url https://&lt;APIG 公网地址&gt; \
  --check

python3 -m unittest discover -s tests -v
```

## 本次生成结果

生成文件：`openapi.generated.yaml`，包含以下 5 个存量业务 API：

| HTTP API | 自动生成的 operationId | MCP 用途 |
| --- | --- | --- |
| `GET /api/cameras` | `list_cameras` | 定位设备、查列表 |
| `GET /api/cameras/{camera_id}` | `get_camera` | 查询设备详情 |
| `GET /api/cameras/{camera_id}/diagnostics` | `diagnose_camera` | 获取网络、供电、存储等诊断指标 |
| `GET /api/alerts` | `list_camera_alerts` | 查询近期告警 |
| `PATCH /api/cameras/{camera_id}/maintenance-status` | `update_camera_maintenance_status` | 写入检修状态，必须二次确认 |

已验证：扫描校验通过、6 项 Python 测试通过、OpenAPI YAML 结构校验通过（5 个业务路径，HTTP 响应码为 OpenAPI 要求的字符串键）。

## 作业演示流程

1. 展示客户交付物：只有 `server.py`，没有 Swagger 文档。
2. 运行生成命令，展示新生成的 `openapi.generated.yaml` 和 5 个 operationId。
3. 运行 `--check` 及测试，证明文件来自当前源码且结构可用。
4. 将生成文件导入 HTTP 转 MCP 服务，展示工具列表。
5. 在 Agent 中提问“园区西门为什么没有画面？”，展示 MCP 返回 CAM-003 的 38.4% 丢包、486ms 延迟和 ALT-1042 / ALT-1035 告警。

## 交付材料清单

- 存量服务源码：`server.py`
- 自动扫描器：`scripts/generate_openapi_from_source.py`
- 自动生成 Swagger：`openapi.generated.yaml`
- 扫描器测试：`tests/test_openapi_source_scanner.py`
- 命令输出截图：生成、`--check`、单元测试、OpenAPI 结构校验
- Agent 诊断截图：模型网关推理 + `yingteng_test` MCP 调用结果

> 不在文档、截图或演示终端中展示模型网关密钥、Runtime Key、MCP Key 或云账号 AK/SK。
