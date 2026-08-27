# Code Sandbox 基础闭环报告

执行时间：2026-08-07（Asia/Shanghai）

## 资源

- Tool 名称：`lmt-code-sandbox`
- Tool ID：`t-yesbuwp8n4nlc0d1q5hi`
- Tool 类型：`CodeEnv`
- CPU：4 vCPU
- 公共网络：开启
- 快照：创建时显式开启，恢复验证待执行
- Session ID：`lmt-code-session`
- Instance ID：`s-yesbv0oikgnlc0d1o6bv`

完整 Endpoint 含临时 Authorization，不落盘。

## 冒烟测试

远端环境：

- 工作目录：`/home/gem`
- 内核：Linux 6.6.95.bck.1-rc6-amd64
- 架构：x86_64

远端文件 `/home/gem/lmt-smoke.txt` 创建成功，SHA-256：

```text
cfe972d4b2cf35b8641fd5b5bebc5a38614757293772bc1dca84faaefacfc5d9
```

## 文件传输

- 上传：`Sandbox/samples/file-transfer/lmt-upload.txt` → `/home/gem/lmt-upload.txt`
- 下载：`/home/gem/lmt-upload.txt` → `Sandbox/logs/lmt-download.txt`
- 两端 SHA-256：`b4ef93d0eba4a81cc1311816560c71e75de32e178b1e31852e5abd3ca584443f`
- `cmp_exit=0`

结论：双向 SCP 与内容一致性验证通过。

## Web 预览

- `sandbox web --no-open` 成功返回地址。
- Session 被复用，`is_new=false`。
- 地址中的 Authorization 已排除出过程资产。

结论：Web 预览链路通过，人工视觉检查待后续截图阶段完成。

## AI 工具

| 工具 | 版本/状态 | 模型调用 |
|---|---|---|
| Codex | 0.139.0 | 通过，返回 `LMT_CODE_SANDBOX_OK` |
| OpenCode | 1.4.6 | 通过，返回 `LMT_OPENCODE_OK` |
| Claude | 镜像内未安装 | 不通过，记录为文档描述差异 |

Codex 使用 `glm-5-2-260617`、read-only sandbox。PATH 中缺少 bubblewrap，但自动使用内置版本，未阻塞执行。

## 阶段结论

Code Sandbox 创建、Session、Shell、文件写入、SCP、Web 地址生成、Codex 与 OpenCode 模型调用均通过。快照恢复和人工 Web 视觉检查尚待执行。
