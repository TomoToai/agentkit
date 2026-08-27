# 自定义 Sandbox 构建前检查

执行时间：2026-08-07（Asia/Shanghai）

## 已完成

- 使用 `agentkit sandbox init --template code` 生成 Dockerfile。
- 文件：`Sandbox/samples/custom-sandbox/Dockerfile`
- 基础镜像：`enterprise-public-cn-beijing.cr.volces.com/vefaas-public/code-cli:0.0.7`
- 模板示例包：`is-even@1.0.0`

## 待确认

当前仅完成本地初始化，尚未执行云端 Code Pipeline 构建。正式构建前需要：

1. 将示例 npm 包替换为有验证价值且版本固定的依赖。
2. 确认镜像仓库名称 `lmt-custom-sandbox-image`。
3. 单独确认云端流水线、CR 仓库与构建费用影响。
