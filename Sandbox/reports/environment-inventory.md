# 环境盘点报告

盘点时间：2026-08-07（Asia/Shanghai）

## 工作区

- 项目根目录：`/Users/bytedance/Documents/trae_projects/AgentKit`
- 实操资产目录：`Sandbox/`
- `Sandbox/` 在盘点前为空。
- 项目存在与本任务无关的历史删除改动；本任务不恢复、不覆盖这些改动。

## 已安装工具

| 工具 | 版本/状态 |
|---|---|
| agentkit | 0.50.9 |
| lark-cli | 1.0.84 |
| situla | 0.1.0 |
| veadk | 0.2.22 |
| Python | 3.13.3 |
| Node.js | v24.11.1 |
| npm | 11.6.2 |
| uv | 0.12.0 |
| Docker Client | 29.4.3 |
| Docker Server | 未返回版本，需后续确认 daemon 状态 |
| Codex | 已安装 |
| OpenCode | 已安装 |
| Claude | 已安装 |

## AgentKit 状态

- SSO：未登录，`agentkit whoami` 提示执行登录。
- 本地缓存 Session：空。
- 默认 Tool 类型：`CodeEnv`。
- 默认 CPU：4。
- 默认公共网络：开启。
- 默认快照：关闭；创建测试 Tool 时将显式开启。
- 默认 Session TTL：28800 秒。
- 默认模型：`glm-5-2-260617`。
- 默认模型 API Base：`https://ark.cn-beijing.volces.com/api/v3`。

## 凭证状态

仅检查是否存在，未读取或记录任何值：

| 变量 | 状态 |
|---|---|
| `VOLCENGINE_ACCESS_KEY` | 未设置 |
| `VOLCENGINE_SECRET_KEY` | 未设置 |
| `ARK_API_KEY` | 已设置 |
| `MODEL_API_KEY` | 未设置 |
| `SANDBOX_CHAT_CODEX` | 未设置 |
| `SANDBOX_OPENCLAW_TOOL` | 未设置 |
| `SANDBOX_HERMES_TOOL` | 未设置 |

## 当前阻塞

`agentkit whoami` 仅识别 SSO Profile，因此在 AK/SK 模式下仍显示未登录；这不代表 AK/SK 无效。

桃哥已明确授权读取并使用项目根目录 `.env` 中的 AK/SK。实测将 `.env` 仅注入当前进程后，`agentkit runtime list` 能成功读取 `cn-beijing/default` 的云端 Runtime 列表，证明账号、区域与基础 OpenAPI 权限有效。

当前不再受 SSO 阻塞。后续命令仅在进程内加载 `.env`，不复制或输出凭证值。
