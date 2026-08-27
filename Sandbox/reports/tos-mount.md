# TOS 挂载实操记录

## 资源与操作

- 新 Bucket 计划名：`lmt-sandbox-workspace-2100045928`
- 创建结果：账号返回 `TooManyBuckets`，Bucket 数量已达上限。
- 安全替代：复用已有北京地域 Bucket `lmt-dataset`，仅使用独立对象前缀 `lmt-agentkit-sandbox/`。
- Tool：`lmt-tos-sandbox`（`t-yesby5hedceuszqwvmy9`）
- Sessions：`lmt-tos-session`、`lmt-tos-session-2`
- 本地挂载点：`/home/gem/workspace`，系统显示为 `s3fs`、读写挂载。

## 验证结果

- TOS API 写入 `seed.txt` 成功，并可通过 API 回读 `LMT_TOS_SEED_OK`。
- 沙箱内可以在挂载路径创建 `roundtrip.txt`，命令返回退出码 0。
- 但 TOS API 未发现 `roundtrip.txt`，第二个 Session 也未看到 Bucket 对象。

因此工具创建与 s3fs 挂载成立，但对象持久化闭环未成立，TOS-01 标记为阻塞。可能原因是挂载角色/前缀映射与当前 Bucket 不匹配，需要控制台核查 Tool 的 TOS 授权配置。

所有资源和诊断现场均保留。
