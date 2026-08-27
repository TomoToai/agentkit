# Dev Sandbox 实操记录

## 资源

- Tool 名称：`lmt-dev-sandbox`
- Tool 类型：`DevEnv`
- Tool ID：`t-yesbxj34e8nlc0d1o68e`
- Session ID：`lmt-dev-session`
- 配置：4 vCPU、公共网络、启用快照
- 处置：保留资源，供后续检查

## 验证结果

通过 AgentKit CLI 创建 DevEnv，并启动独立 Session 执行 Shell 冒烟测试：

```text
LMT_DEV_SANDBOX_OK
Linux
x86_64
```

命令返回 `success: true`、`status: completed`、`exit_code: 0`，DEV-01 判定通过。

## 说明

- 首次创建命令在非交互输出中未返回资源 JSON；再次创建提示名称已存在。
- 随后从 AgentKit 沙箱有效配置确认 Tool ID，并以该 ID 成功创建 Session 和执行验证。
- 未在本文件中保存任何 AK、SK、模型密钥或临时访问参数。
