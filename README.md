# 影腾摄像头售后 Agent · AgentKit 学习型 Demo

> 用一个**摄像头监控售后诊断 Agent** 的端到端 Demo，系统性地跑通并理解火山引擎
> **AgentKit** 这套高代码 Agent 开发平台、**VeADK** Agent 开发框架，以及构建生产级
> Agent 所必需的一整套 **Harness 组件**——网关、观测、评测、身份、知识、沙箱。

## 一、这个项目是什么

这不是一个"上线卖钱"的产品，而是一个**以真实业务场景为载体的学习 / 演示工程**。

我们虚构了一家安防厂商「影腾」，为它的园区摄像头做一个**售后客服与故障诊断 Agent**：
用户用自然语言问"西门那个摄像头为什么画面卡"，Agent 会自主调用工具去查设备状态、
拉诊断指标、看近期告警，按"供电 / 网络 / 存储 / 画面"归类根因并给出可执行建议；涉及
改设备状态这类**写操作**时，必须先向用户确认才执行。

选这个场景，是因为它足够"像真的"——有存量系统、有权限、有写操作红线、有幻觉风险，
因而能把构建一个可信 Agent 真正要过的每一关都串起来。**业务只是载体，真正的目的是
借它吃透 AgentKit 平台与 VeADK 框架，以及下面这套 Harness 组件如何协同。**

> 一期使用确定性的**模拟数据**，不接真实摄像头或视频流，以便结果可判定、可回归。

## 二、两条主线：平台 + 框架

| 名称 | 定位 | 在本项目中的体现 |
|---|---|---|
| **AgentKit** | 火山引擎的**高代码 Agent 开发平台**：把网关、可观测、评测、身份、知识、沙箱等能力以平台化方式提供，让开发者聚焦业务而非重复造轮子 | 贯穿全部模块——存量 API 经**网关**转 MCP、Runtime 接**模型网关**、Trace 进**可观测**、评测集跑**评测实验**、密钥走**身份**托管 |
| **VeADK**（Volcengine Agent Development Kit） | AgentKit 上的 **Agent 开发框架 / Runtime**：定义 Agent 的指令、工具、模型与运行时行为 | [`APIG/camera-agent-runtime/agent.py`](APIG/camera-agent-runtime/agent.py) 即用 VeADK 定义的摄像头诊断 Agent（角色指令、5 个 MCP 工具、取证与写操作确认规则） |

## 三、核心数据链路

```text
          Web 控制台 ──────────────► 存量 REST API（X-API-Key 鉴权）
                                              ▲
  用户提问 ──► VeADK Agent Runtime ──► MCP 工具集 ──► HTTP 转 MCP（网关）
                     │
                     └──► 模型网关（主模型 + Fallback）
                     │
                     └──► 全链路 Trace ──► 可观测 / 数据回流 ──► 评测集 ──► 评测实验
```

一句话：**存量系统 → API → 网关转 MCP → VeADK Agent → 模型网关**跑通业务，
运行时的 **Trace 沉淀到可观测**，再**回流成评测集**驱动质量闭环。

## 四、Harness 组件 × 目录映射

构建一个可信 Agent，光有"模型 + 提示词"远远不够，还需要一圈支撑性的
"脚手架（Harness）"。本仓库按组件拆成独立目录，各自可复现、可审查：

| Harness 组件 | 目录 | 承担的能力 | 关键产物 |
|---|---|---|---|
| 🌐 **网关 Gateway** | [`APIG/`](APIG/) | 存量摄像头系统（零依赖 Web/API）+ OpenAPI + **HTTP 转 MCP**，把业务 API 安全暴露给 Agent | `server.py`、`openapi.yaml`、`camera-agent-runtime/` |
| 📈 **观测 Observability** | [`APMPlus/`](APMPlus/) | 采集线上真实 Trace 并**数据回流**，把生产流量加工成评测集 | `数据回流方案.md`、`replay_traffic.py`、`process_reflow.py` |
| ✅ **评测 Evaluation** | [`eval/`](eval/) | 人工设计评测集 + 三类评估器（事实正确性 / 工具合规 / 安全边界），跑评测实验 | `camera_agent_eval_set.csv`（28 条）、评测集设计文档 |
| 🔑 **身份 Identity** | [`identity/`](identity/) | 凭证与鉴权机制说明：永久 AK/SK 与 STS 临时凭证的对比与适用场景 | `STS说明.md` |
| 📚 **知识 Knowledge** | [`Knowledge/`](Knowledge/) | 30 个 SKU 的产品使用指南知识库，供 Agent"先确认型号再检索指南"作答 | `catalog.json`、`guides/*.md`、可复现生成器 |
| 📦 **沙箱 Sandbox** | [`Sandbox/`](Sandbox/) | AgentKit 云上执行环境的全量实操与可审计资产 | 测试矩阵、验收报告、脱敏日志 |

> 另有 [`DeliveryAI/`](DeliveryAI/)：AgentKit **DeliveryAI（交付官）** 多 Agent 协作
> 交付工作空间的 Demo 素材（角色 / 流程模板、飞书项目与 CodeBase 集成），
> 展示"需求 → 代码 → 上线"的自动化交付链路。

## 五、被测 Agent 画像（硬约束）

摄像头诊断 Agent 的行为受一组明确的 Guardrail 约束——这也是评测重点考核的对象：

- **先取证再回答**：涉及设备状态 / 故障 / 告警前，必须调 MCP 工具拿事实，**禁止编造**。
- **诊断顺序**：定位设备 → 查详情 → 取诊断指标 → 查近期告警。
- **写操作需确认**：改检修状态属写操作，**用户明确确认后**才执行。
- **拒绝幻觉**：使用确定性模拟遥测，**不得声称**读取 / 分析了真实画面。
- **越权 / 越域**：无删除能力则界定范围，越域问题礼貌拒答并引导回业务。

## 六、快速上手

```bash
# 1) 启动存量系统 + Agent 演示（零第三方依赖）
cd APIG
cp .env.example .env          # 填入 BUSINESS_API_KEY 等
python3 server.py             # 打开 http://127.0.0.1:8000

# 2) 跑 API 自动化测试
python3 -m unittest discover -s tests -v

# 3) 生成 / 刷新产品知识库与合订手册
cd ../Knowledge
python3 build_knowledge.py    # 重新生成 30 份指南
python3 build_manual.py       # 合订成 Word / PDF 手册
```

各组件的详细说明见对应目录下的 `README.md`。

## 七、安全与约定

- 敏感值（AK/SK、API Key、Authorization、token 等）**绝不入库**；`.env` 已被忽略，
  仓库仅保留 `.env.example` 模板。
- 本地产物（`Knowledge/dist/` 手册、`APMPlus/*.bak`、`span-export-*.csv`）均可由脚本
  重新生成，已在 `.gitignore` 中排除。
- 知识库为**虚构演示数据**，型号与参数不代表真实产品。
