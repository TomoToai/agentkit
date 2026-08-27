#!/usr/bin/env python3
"""数据回流导出 → 评测集 CSV 的加工脚本（第二层 Noise 过滤）。

数据回流在控制台按「服务=摄像头 Agent + AI Span 类型=Agent Run + 成功」
筛出并导出真实 Trace 后，用本脚本做导出后的内容级清洗，产出可直接导入
「影腾摄像头诊断-真实回流集」的 CSV。

处理四步（与方案对齐）：
  1) 抽取：从回流导出的 JSON/JSONL 里抽 input（用户问题）与 output（Agent 回答）；
  2) 剔无效：空/超短/纯符号/探测性输入（test、123、你好、health 等）丢弃；
  3) 去重：input 归一化（去空白标点、小写）后完全重复只留最早一条；
  4) 脱敏：IP、手机号、邮箱、工号等 PII 替换为占位符。

输入兼容两种来源：
  - 回流控制台导出的 Trace 文件（JSON 数组 / JSONL，字段名做了多路兜底）；
  - 本目录 replay_traffic.py 产出的 replay_result.jsonl（造流量的自测数据）。

输出：real_reflow_eval_set.csv（UTF-8 BOM，Excel 直开不乱码），
     列 = case_id,input,reference_output,source,collected_at
     其中 reference_output 先填 Agent 真实回答，需人工审核/修正后方可作为标准答案。
"""
import argparse
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(__file__)

# 探测性 / 无意义输入（归一化后精确匹配即丢弃）
JUNK_INPUTS = {"test", "测试", "123", "你好", "hi", "hello", "ping", "health", "在吗", "。", "？"}
MIN_LEN = 4  # 少于 4 个有效字符视为无效

# PII 脱敏规则：正则 → 占位符
PII_RULES = [
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "<IP>"),
    (re.compile(r"\b1[3-9]\d{9}\b"), "<PHONE>"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "<EMAIL>"),
    (re.compile(r"\b(?:工号|员工号|工牌)\s*[:：]?\s*\w+\b"), "<STAFF_ID>"),
]


def normalize(text: str) -> str:
    """归一化用于去重/无效判定：去首尾空白、内部空白折叠、去标点、转小写。"""
    s = re.sub(r"\s+", "", text.strip().lower())
    s = re.sub(r"[，。！？、；：,.!?;:~`\"'\-—…（）()【】\[\]]", "", s)
    return s


def redact(text: str) -> str:
    for pat, repl in PII_RULES:
        text = pat.sub(repl, text)
    return text


def _first(d: dict, keys: list[str]) -> str:
    """从多个可能的字段名里取第一个非空值（兼容不同导出结构）。"""
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def extract_pair(rec: dict) -> tuple[str, str, str]:
    """从一条记录抽出 (input, output, collected_at)，兼容多种导出字段名。"""
    inp = _first(rec, ["input", "user_input", "question", "prompt", "message", "query"])
    out = _first(rec, ["answer", "output", "response", "completion", "reply", "final_output"])
    ts = _first(rec, ["collected_at", "timestamp", "start_time", "time", "created_at"])
    # 回流 Trace 常把 I/O 藏在 attributes / span 里，做一层兜底
    if not inp or not out:
        attrs = rec.get("attributes") or rec.get("span_attributes") or {}
        if isinstance(attrs, dict):
            inp = inp or _first(attrs, ["input", "gen_ai.prompt", "llm.input", "user_input"])
            out = out or _first(attrs, ["output", "gen_ai.completion", "llm.output"])
    return inp, out, ts


def load_records(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        content = f.read().strip()
    if not content:
        return []
    # 优先按 JSON 数组解析，失败再按 JSONL
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # 有的导出包一层 {"data":[...]} / {"traces":[...]}
            for k in ("data", "traces", "items", "records", "spans"):
                if isinstance(data.get(k), list):
                    return data[k]
            return [data]
    except json.JSONDecodeError:
        pass
    recs = []
    for line in content.splitlines():
        line = line.strip()
        if line:
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return recs


def main() -> None:
    ap = argparse.ArgumentParser(description="回流导出 → 评测集 CSV 加工")
    ap.add_argument("--input", "-i", default=os.path.join(HERE, "replay_result.jsonl"),
                    help="回流导出文件（JSON/JSONL），默认 replay_result.jsonl")
    ap.add_argument("--output", "-o", default=os.path.join(HERE, "real_reflow_eval_set.csv"),
                    help="输出 CSV 路径")
    ap.add_argument("--source-tag", default="reflow", help="来源标记，写入 source 列")
    ap.add_argument("--only-success", action="store_true",
                    help="仅保留 http_status==200 的记录（对 replay_result.jsonl 有效）")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"[FATAL] 找不到输入文件：{args.input}", file=sys.stderr)
        sys.exit(1)

    recs = load_records(args.input)
    print(f"[INFO] 读入 {len(recs)} 条原始记录")

    kept: list[dict] = []
    seen: set[str] = set()
    stat = {"empty": 0, "junk": 0, "short": 0, "dup": 0, "non200": 0}

    for rec in recs:
        if args.only_success and rec.get("http_status") not in (200, None):
            stat["non200"] += 1
            continue
        inp, out, ts = extract_pair(rec)
        if not inp or not out:
            stat["empty"] += 1
            continue
        norm = normalize(inp)
        if norm in JUNK_INPUTS:
            stat["junk"] += 1
            continue
        if len(norm) < MIN_LEN:
            stat["short"] += 1
            continue
        if norm in seen:
            stat["dup"] += 1
            continue
        seen.add(norm)
        kept.append({
            "input": redact(inp),
            "reference_output": redact(out),
            "collected_at": ts,
        })

    print(f"[INFO] 过滤明细：无效I/O {stat['empty']} · 探测性 {stat['junk']} · "
          f"过短 {stat['short']} · 重复 {stat['dup']} · 非成功 {stat['non200']}")
    print(f"[INFO] 去噪后保留 {len(kept)} 条")

    with open(args.output, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "input", "reference_output", "source", "collected_at"])
        for i, r in enumerate(kept, 1):
            w.writerow([f"REFLOW-{i:03d}", r["input"], r["reference_output"],
                        args.source_tag, r["collected_at"]])

    print(f"[DONE] 写出 {args.output}（{len(kept)} 条，UTF-8 BOM）")
    print("[NEXT] reference_output 目前是 Agent 真实回答，需人工审核/修正为标准答案后再导入评测集。")


if __name__ == "__main__":
    main()
