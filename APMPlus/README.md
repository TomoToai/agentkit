xxx# APMPlus · 数据回流评测集

本目录承载**方式二：数据回流（Data Reflow）**——从 AgentKit「可观测 → 数据回流」采集
线上真实 Trace，加工成独立评测集「影腾摄像头诊断-真实回流集」。

与 `eval/`（方式一：人工设计评测集）平级、互不合并；两者最终复用同一套评估器
（事实正确性 / 工具合规 / 安全边界）跑评测实验。

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
# 1) 造流量：回放评测问题，生成真实 Trace（断点续跑、失败自动重试）
export REPLAY_PASS='<控制台登录密码>'   # 凭据勿写进脚本
python3 replay_traffic.py

# 2) 控制台「数据回流」按 服务=摄像头 Agent + AI Span 类型=Agent Run + 成功 导出 Trace

# 3) 去噪加工：导出文件 → 干净 CSV
python3 process_reflow.py -i <导出的Trace文件.jsonl>
#   自测：直接用回放结果
python3 process_reflow.py --only-success --source-tag replay

# 4) 新建评测集「影腾摄像头诊断-真实回流集」导入 CSV，人工审核 reference_output
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
