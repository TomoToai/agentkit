# CodeBase 代码仓库集成（CodeBase）

存放 **CodeBase 代码仓库** 的集成配置示例与说明。

## 需要准备
- CodeBase Personal Access Token（企业管理员在控制台「企业集成」配置）
- 绑定的代码仓库 / 组织
- 基准分支（如 `main` / `master`）
- 分支命名规范（如 `feat/demo-login-<需求ID>`）、Commit 规范、MR 模板

## 说明
- Coding Agent 基于基准分支创建 feature 分支并提交代码。
- MR 节点自动在 CodeBase 创建 MR，关联需求 ID 与测试结果。

> 敏感凭据请写入项目根目录 `.env`，勿提交到 git（参考根目录 `.gitignore`）。
