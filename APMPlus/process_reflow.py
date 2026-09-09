#!/usr/bin/env python3
"""数据回流导出 → 评测集 CSV 的加工脚本（第二层 Noise 过滤）。

数据回流在控制台按「服务=摄像头 Agent + AI Span 类型=agent」筛出并导出真实
Trace 后，用本脚本做导出后的内容级清洗，产出可直接导入「影腾摄像头诊断-真实
回流集」的 CSV。

⚠️ 只保留 `agent` 类型 span：一条 agent span = 一轮完整问答（input 为用户原话、
output 为最终回答），正是评测样本粒度。llm/tool/llm_loop/root 等中间 span 的
input/output 是 prompt、工具调用 JSON、中间结果，不能当问答样本；即便控制台过滤
时误勾了这些类型，本脚本也会在导出后兜底剔除。

处理五步（与方案对齐）：
  1) 抽取：从回流导出的 JSON/JSONL 里抽 input（用户问题）与 output（Agent 回答）；
  2) 限类型：非 agent 类型 span 丢弃（若记录带 span 类型字段）；
  3) 剔无效：空/超短/纯符号/探测性输入（test、123、你好、health 等）、
     input 是工具调用 JSON（{"name":...} 结构）的脏行丢弃；
  4) 去重：input 归一化（去空白标点、小写）后完全重复只留最早一条；
  5) 脱敏：IP、手机号、邮箱、工号等 PII 替换为占位符。

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

# 降级 / 工具失败回答标记：命中即视为坏样本丢弃（造流量并发偶发把单实例 Runtime
# 打出的工具调用失败，HTTP 仍是 200 但内容是降级话术，不能当标准答案）。
BAD_ANSWER_MARKERS = (
    "Missing tool result", "tool calls are failing", "tool call failed",
    "NoneType", "Error:", "系统暂时有些波动", "我再试一次", "稍后再试",
    "请稍后重试", "暂时无法", "出现了一些问题", "调用失败",
)

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


def _unwrap_apmplus_input(raw: str) -> str:
    """解包 APMPlus 导出的 input：{"messages":[{role,content},{role,parts:[{content,type}]}]}。

    真正的用户问题在最后一个 role=user 消息的 parts[].content（或 content 裸文本）里；
    首个 content 常是 {agent_name,session_id,...} 元数据 JSON，需跳过。
    """
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(obj, dict):
        return ""
    msgs = obj.get("messages")
    if not isinstance(msgs, list):
        return ""
    texts: list[str] = []
    for m in msgs:
        if not isinstance(m, dict) or m.get("role") != "user":
            continue
        parts = m.get("parts")
        if isinstance(parts, list):
            for p in parts:
                if isinstance(p, dict) and isinstance(p.get("content"), str):
                    texts.append(p["content"])
        else:
            c = m.get("content")
            # 跳过形如 {"agent_name":...,"session_id":...} 的元数据 content
            if isinstance(c, str) and c.strip() and not c.strip().startswith("{"):
                texts.append(c)
    return "\n".join(t for t in texts if t.strip()).strip()


def _unwrap_apmplus_output(raw: str) -> str:
    """解包 APMPlus 导出的 output：{"choices":[{"message":{parts:[{text,type}] | content}}]}。

    回答是所有 assistant 消息 parts[].text（跳过 None）按序拼接。
    """
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(obj, dict):
        return ""
    choices = obj.get("choices")
    if not isinstance(choices, list):
        return ""
    texts: list[str] = []
    for ch in choices:
        msg = ch.get("message") if isinstance(ch, dict) else None
        if not isinstance(msg, dict):
            continue
        parts = msg.get("parts")
        if isinstance(parts, list):
            for p in parts:
                if isinstance(p, dict) and isinstance(p.get("text"), str):
                    texts.append(p["text"])
        elif isinstance(msg.get("content"), str):
            texts.append(msg["content"])
    return "".join(texts).strip()


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
    # APMPlus 控制台导出的 input/output 是深层嵌套 JSON，需解包成纯文本
    if inp and (inp.startswith("{") or inp.startswith("[")):
        unwrapped = _unwrap_apmplus_input(inp)
        if unwrapped:
            inp = unwrapped
    if out and (out.startswith("{") or out.startswith("[")):
        unwrapped = _unwrap_apmplus_output(out)
        if unwrapped:
            out = unwrapped
    return inp, out, ts


def span_type(rec: dict) -> str:
    """取 AI Span 类型（兼容多种字段名），无该字段时返回空串。"""
    attrs = rec.get("attributes") or rec.get("span_attributes") or {}
    st = _first(rec, ["ai_span_type", "span_type", "spanType", "type", "kind"])
    if not st and isinstance(attrs, dict):
        st = _first(attrs, ["ai_span_type", "span_type", "gen_ai.span.kind"])
    return st.lower()


def looks_like_tool_call(text: str) -> bool:
    """判断 input 是否是工具调用 / 工具返回 JSON（如 {"name":"...","description":...}）。

    这类是 llm/tool span 的内容，不是用户问题，需剔除。仅在文本能解析成
    dict 且带工具特征键时判真，避免误伤正常的中文问句。
    """
    s = text.strip()
    if not (s.startswith("{") or s.startswith("[")):
        return False
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        return False
    if isinstance(obj, list):
        obj = obj[0] if obj and isinstance(obj[0], dict) else {}
    if not isinstance(obj, dict):
        return False
    return bool({"name", "description", "arguments", "tool_calls", "id"} & set(obj.keys()))


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
    ap.add_argument("--span-type", default="agent",
                    help="仅保留该 AI Span 类型（默认 agent；设为 '' 关闭类型过滤）")
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
    stat = {"empty": 0, "junk": 0, "short": 0, "dup": 0, "non200": 0,
            "wrong_type": 0, "toolcall": 0, "bad_answer": 0}
    want_type = args.span_type.strip().lower()

    for rec in recs:
        if args.only_success and rec.get("http_status") not in (200, None):
            stat["non200"] += 1
            continue
        # 仅保留目标 span 类型；记录没有类型字段时（如 replay 自测数据）不拦截
        st = span_type(rec)
        if want_type and st and st != want_type:
            stat["wrong_type"] += 1
            continue
        inp, out, ts = extract_pair(rec)
        if not inp or not out:
            stat["empty"] += 1
            continue
        # 回答含降级/工具失败标记的坏样本丢弃（HTTP 200 但内容不可用，不能作标准答案）
        if any(m in out for m in BAD_ANSWER_MARKERS):
            stat["bad_answer"] += 1
            continue
        # input 是工具调用/返回 JSON 的，是 llm/tool span 漏进来的脏行，剔除
        if looks_like_tool_call(inp):
            stat["toolcall"] += 1
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

    print(f"[INFO] 过滤明细：非目标类型 {stat['wrong_type']} · 工具调用JSON {stat['toolcall']} · "
          f"降级坏回答 {stat['bad_answer']} · 无效I/O {stat['empty']} · 探测性 {stat['junk']} · "
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
