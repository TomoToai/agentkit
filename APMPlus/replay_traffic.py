#!/usr/bin/env python3
"""回放评测问题到已部署的摄像头诊断 Web 应用，产生真实全链路 Trace。

用途：为「数据回流」方式的评测集造流量。逐条 POST /api/agent/chat，
触发 浏览器→Web→Agent Runtime(yingteng_camera_support)→MCP 全链路，
从而在 APMPlus 可观测里沉淀真实 Trace，供后续回流导出。

设计要点：
- 每条问题独立 session_id，保证每轮是完整独立的 Agent Run（回流不会串题）。
- user_id 统一为 eval-replay，便于回流时按维度圈出这批造的流量。
- 顺序执行 + 间隔，避免打爆单实例 Runtime（min=max=1）。
- 仅读取平级 eval/ 目录的 camera_agent_eval_set.csv 的 case_id/input 两列
  （题库来源，可用 REPLAY_CSV 覆盖）。
"""
import csv
import json
import os
import sys
import time
import urllib.request as urlrequest
import urllib.error as urlerror
from http.cookiejar import CookieJar

BASE = os.getenv("REPLAY_BASE_URL", "https://scnmblp2s7ph3h8mvvspf.apigateway-cn-beijing.volceapi.com")
USERNAME = os.getenv("REPLAY_USER", "admin")
# 登录密码只从环境变量读取，绝不硬编码明文（遵守项目硬约束）。
# 运行前：export REPLAY_PASS='...'（凭据存项目根 .env，已被 git 忽略）。
PASSWORD = os.getenv("REPLAY_PASS", "")
# 题库来源：方式一的设计评测集在平级的 eval/ 目录；可用 REPLAY_CSV 覆盖。
CSV_PATH = os.getenv("REPLAY_CSV", os.path.join(
    os.path.dirname(__file__), "..", "eval", "camera_agent_eval_set.csv"))
# 回流产物落在 APMPlus 本目录。
OUT_PATH = os.path.join(os.path.dirname(__file__), "replay_result.jsonl")
INTERVAL = float(os.getenv("REPLAY_INTERVAL", "2.0"))
TIMEOUT = float(os.getenv("REPLAY_TIMEOUT", "150"))

jar = CookieJar()
opener = urlrequest.build_opener(urlrequest.HTTPCookieProcessor(jar))


def _post(path: str, payload: dict, retries: int = 3) -> tuple[int, str]:
    body = json.dumps(payload, ensure_ascii=False).encode()
    last_err = ""
    for attempt in range(1, retries + 1):
        req = urlrequest.Request(
            f"{BASE}{path}", data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with opener.open(req, timeout=TIMEOUT) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urlerror.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", "replace")
        except (urlerror.URLError, ConnectionError, TimeoutError, OSError) as exc:
            # 单实例 Runtime 偶发断连/超时：退避后重试，避免整批中断。
            last_err = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                back = 3 * attempt
                print(f"      ↻ 连接异常({last_err})，{back}s 后第 {attempt+1} 次重试", file=sys.stderr)
                time.sleep(back)
    return 0, last_err


def login() -> None:
    if not PASSWORD:
        print("[FATAL] 未设置登录密码，请先 export REPLAY_PASS='...' 再运行", file=sys.stderr)
        sys.exit(1)
    status, text = _post("/api/login", {"username": USERNAME, "password": PASSWORD, "remember": False})
    if status != 200:
        print(f"[FATAL] 登录失败 HTTP {status}: {text}", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] 登录成功：{text}")


def load_cases() -> list[dict]:
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        return [{"case_id": r["case_id"], "input": r["input"]} for r in csv.DictReader(f)]


def already_done() -> set[str]:
    """读取已有结果，收集 HTTP 200 成功的 case_id，用于断点续跑。"""
    done: set[str] = set()
    if not os.path.exists(OUT_PATH):
        return done
    with open(OUT_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("http_status") == 200 and rec.get("answer"):
                done.add(rec["case_id"])
    return done


def main() -> None:
    login()
    cases = load_cases()
    done = already_done()
    pending = [c for c in cases if c["case_id"] not in done]
    print(f"[INFO] 共 {len(cases)} 条；已成功 {len(done)} 条，待回放 {len(pending)} 条（间隔 {INTERVAL}s）\n")
    ok = fail = 0
    with open(OUT_PATH, "a", encoding="utf-8") as out:
        for i, c in enumerate(pending, 1):
            cid, msg = c["case_id"], c["input"]
            sid = f"eval-replay-{cid.lower()}"
            t0 = time.perf_counter()
            status, text = _post("/api/agent/chat", {
                "message": msg, "user_id": "eval-replay", "session_id": sid,
            })
            dt = time.perf_counter() - t0
            answer = ""
            if status == 200:
                try:
                    answer = json.loads(text).get("answer", "")
                except json.JSONDecodeError:
                    answer = text
                ok += 1
                flag = "OK"
            else:
                answer = text
                fail += 1
                flag = f"ERR{status}"
            out.write(json.dumps({
                "case_id": cid, "session_id": sid, "input": msg,
                "http_status": status, "answer": answer, "elapsed_s": round(dt, 2),
            }, ensure_ascii=False) + "\n")
            out.flush()
            print(f"[{i:>2}/{len(pending)}] {cid} {flag} {dt:5.1f}s  {msg[:24]}")
            if i < len(pending):
                time.sleep(INTERVAL)
    print(f"\n[DONE] 本轮成功 {ok} / 失败 {fail}，明细写入 {OUT_PATH}")


if __name__ == "__main__":
    main()
