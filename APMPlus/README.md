# APMPlus · 数据回流评测集

本目录承载**方式二：数据回流（Data Reflow）**——从 AgentKit「可观测 → 数据回流」采集
线上真实 Trace，加工成独立评测集「影腾摄像头诊断-真实回流集」。

与 `eval/`（方式一：人工设计评测集）平级、互不合并；两者最终复用同一套评估器
（事实正确性 / 工具合规 / 安全边界）跑评测实验。

> 完整落地方案（含官方字段说明、字段映射、脱敏与限制）见本目录 [`数据回流方案.md`](数据回流方案.md)。
>
> ⚠️ **关键顺序**：官方数据回流「仅回流新数据、不支持历史数据」——导出任务只捕获
> **任务创建之后**产生的 Trace。因此**必须先在控制台创建导出任务，再跑 `replay_traffic.py`
> 造流量**，否则造的流量不会被导出。

## 目录文件

| 文件 | 作用 |
|---|---|
| `replay_traffic.py` | **造流量**脚本：把 `eval/` 的评测问题逐条回放到已部署 Web 应用（登录 → POST `/api/agent/chat`），触发 `浏览器→Web→Agent Runtime→MCP` 全链路，在 APMPlus 沉淀真实 Trace |
| `replay_result.jsonl` | 回放结果明细（28 条，成功/耗时/回答），也可直接作为 `process_reflow.py` 的输入 |
| `process_reflow.py` | **去噪加工**脚本（第二层 Noise 过滤）：抽取 → 剔无效 → 去重 → PII 脱敏 → 生成评测集 CSV。兼容回放结果与控制台导出的 Trace JSON/JSONL |
| `real_reflow_eval_set.csv` | 去噪后的回流评测集（UTF-8 BOM）。`reference_output` 为 Agent 真实回答，**需人工审核/修正为标准答案后**方可导入 |

## 数据来源说明

- `replay_traffic.py` 的题库默认取平级 `../eval/camera_agent_eval_set.csv`（可用环境变量
  `REPLAY_CSV` 覆盖）；回流产物 `replay_result.jsonl` 落在本目录。
- 造流量与去噪脚本仅用 Python 标准库，直接 `python3` 运行即可，无需第三方依赖。

## 运行方式

```bash
# 1) 【先建任务】控制台 可观测 → 数据回流 → 创建导出任务
#    数据过滤：服务名称=摄像头 Agent Runtime + AI Span 类型=Agent Run + 状态码=成功
#    时间范围=回流新数据；导出平台=智能体评测平台；目标评测集=新增「影腾摄像头诊断-真实回流集」
#    导入方式=追加；数据脱敏=开启；字段映射：Span.input→input、Span.output→reference_output
#    ——务必先建任务再造流量，否则「仅回流新数据」会漏掉本次流量。

# 2) 造流量：回放评测问题，生成真实 Trace（断点续跑、失败自动重试）
set -a && source ../.env && set +a   # 载入 REPLAY_USER/REPLAY_PASS（勿硬编码）
python3 replay_traffic.py

# 3) 等任务导出到评测集后，可直接在控制台用该评测集发起实验；
#    如需本地二次清洗/自测，用去噪脚本把导出文件 → 干净 CSV：
python3 process_reflow.py -i <导出的Trace文件.jsonl>
#    自测：直接用回放结果
python3 process_reflow.py --only-success --source-tag replay

# 4) 人工审核 reference_output（回流的是 Agent 真实回答，需修正为标准答案）
#    + 补 category/difficulty 等自定义列 → 提交版本 → 复用三个评估器跑实验
```

## 可覆盖的环境变量（replay_traffic.py）

| 变量 | 默认 | 说明 |
|---|---|---|
| `REPLAY_CSV` | `../eval/camera_agent_eval_set.csv` | 题库来源 |
| `REPLAY_BASE_URL` | 已部署 APIG 公网入口 | Web 应用地址 |
| `REPLAY_USER` / `REPLAY_PASS` | 控制台账号 / **必填无默认** | 登录凭据；`REPLAY_PASS` 只从环境变量读取，运行前 `export REPLAY_PASS='...'`（绝不硬编码明文） |
| `REPLAY_INTERVAL` | `2.0` | 每条间隔秒数（护单实例 Runtime） |
| `REPLAY_TIMEOUT` | `150` | 单条超时秒数 |
