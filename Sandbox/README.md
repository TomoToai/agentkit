# AgentKit Sandbox 全量实操工作区

本目录用于复现《AgentKit沙箱：从云上执行环境到个人智能助手》中的实操，并保存可审计、可复现、已脱敏的过程资产。

## 约定

- 所有新建火山引擎资源名称必须以 `lmt-` 开头。
- 云资源在验收完成后保留，未经桃哥明确确认不删除。
- AK、SK、API Key、Authorization、authToken 等敏感值不得写入本目录、Git 或飞书文档。
- 原始日志写入前必须脱敏；资源 ID、Session ID 和不含凭证的控制台链接可以保留。
- 每项实操必须记录命令、前置条件、结果、证据和结论。

## 目录

- `SUMMARY.md`：状态、资源、关键代码和全部资产的统一入口。
- `plan/`：测试矩阵、执行顺序和验收口径。
- `configs/`：仅含变量名和占位符的配置模板。
- `reports/`：环境盘点、资源清单与阶段报告。
- `scripts/`：后续沉淀的可复现脚本。
- `logs/`：执行日志，落盘前脱敏。
- `screenshots/`：关键步骤截图。
- `samples/`：后端集成、A2A、Situla、VeADK 等样例。

## 当前状态

全量实操与总体验收已完成。详见 `reports/final-acceptance.md` 和 `plan/test-matrix.md`；Hermes、TOS 持久化、快照恢复的外部阻塞条件已单独记录，Janus 按用户要求跳过。

## 飞书实操记录

- 文档：[AgentKit Sandbox 全量实操记录｜lmt](https://bytedance.larkoffice.com/docx/Nlbxdx3gRoKz1KxdfvlcWyy9nwg)
- 文档 ID：`Nlbxdx3gRoKz1KxdfvlcWyy9nwg`
