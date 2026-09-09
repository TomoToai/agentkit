# Agent 角色模板（Agent Templates）

存放 5 类研发角色的 **Agent 模板配置**（系统提示词 + 模型 + Skill/MCP 绑定说明），供空间管理员在「Agent 配置」中创建或微调。

## 建议内容
| 文件 | 角色 | 职责 |
|---|---|---|
| `requirement-analyst.md` | 需求分析师 | 读取代码上下文，产出结构化需求澄清确认卡片 |
| `spec-designer.md` | Spec 设计师 | 基于澄清结果产出设计文档、API 契约、测试用例清单 |
| `coding-agent.md` | Coding Agent | 创建分支、按 Spec 编码提交、触发构建与单测 |
| `test-agent.md` | 测试 Agent | 生成并执行自动化测试、截图、产出测试报告 |
| `release-agent.md` | 发布 Agent | 合并 MR、触发 CI/CD、健康检查、产出发布报告 |

> 每个模板文件建议包含：角色定义、职责边界、输出规范、绑定模型、绑定 Skill/MCP。真实配置在控制台完成后可在此归档备份。
