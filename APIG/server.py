#!/usr/bin/env python3
"""Camera operations demo API and web console, using only Python stdlib."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import ssl
import time
import uuid
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
BUSINESS_API_KEY_ENV = "BUSINESS_API_KEY"
CAMERAS = {
    "CAM-001": {"id": "CAM-001", "name": "园区东门", "site": "上海一号园区", "zone": "东门", "model": "YT-IPC-4K", "status": "online", "maintenance_status": "normal", "ip": "10.21.8.11", "resolution": "4K", "last_seen": "刚刚", "uptime": "99.98%", "health": 98},
    "CAM-002": {"id": "CAM-002", "name": "仓库一层通道", "site": "上海一号园区", "zone": "仓库", "model": "YT-DOME-2K", "status": "online", "maintenance_status": "normal", "ip": "10.21.8.18", "resolution": "2K", "last_seen": "12 秒前", "uptime": "99.92%", "health": 93},
    "CAM-003": {"id": "CAM-003", "name": "园区西门", "site": "上海一号园区", "zone": "西门", "model": "YT-IPC-4K", "status": "degraded", "maintenance_status": "normal", "ip": "10.21.8.23", "resolution": "4K", "last_seen": "2 分钟前", "uptime": "96.41%", "health": 56},
    "CAM-004": {"id": "CAM-004", "name": "停车场北区", "site": "杭州研发中心", "zone": "停车场", "model": "YT-PTZ-4K", "status": "offline", "maintenance_status": "pending", "ip": "10.31.2.14", "resolution": "4K", "last_seen": "38 分钟前", "uptime": "91.03%", "health": 18},
    "CAM-005": {"id": "CAM-005", "name": "研发楼大厅", "site": "杭州研发中心", "zone": "大厅", "model": "YT-DOME-2K", "status": "online", "maintenance_status": "normal", "ip": "10.31.2.26", "resolution": "2K", "last_seen": "刚刚", "uptime": "99.99%", "health": 99},
    "CAM-006": {"id": "CAM-006", "name": "机房入口", "site": "杭州研发中心", "zone": "机房", "model": "YT-IPC-4K", "status": "online", "maintenance_status": "normal", "ip": "10.31.2.31", "resolution": "4K", "last_seen": "4 秒前", "uptime": "99.87%", "health": 91},
}

DIAGNOSTICS = {
    "CAM-003": {"power": "normal", "network": "critical", "packet_loss": 38.4, "latency_ms": 486, "storage": "normal", "temperature_c": 47, "image": "intermittent", "summary": "上联网络丢包过高，导致视频画面间歇中断；供电和本地存储正常。", "recommendations": ["检查西门弱电箱交换机端口和网线", "将丢包率恢复到 3% 以下后重新拉流", "若 10 分钟内未恢复，安排现场检修"]},
    "CAM-004": {"power": "unknown", "network": "offline", "packet_loss": 100, "latency_ms": None, "storage": "unknown", "temperature_c": None, "image": "unavailable", "summary": "设备已离线 38 分钟，无法获取实时诊断指标。", "recommendations": ["检查摄像头和 PoE 交换机供电", "确认设备所在 VLAN 可达", "保持待检修状态并安排现场人员"]},
}

ALERTS = [
    {"id": "ALT-1042", "camera_id": "CAM-003", "camera_name": "园区西门", "type": "network_packet_loss", "severity": "critical", "message": "网络丢包率持续高于 30%", "occurred_at": "2026-08-12 09:42", "status": "active"},
    {"id": "ALT-1041", "camera_id": "CAM-004", "camera_name": "停车场北区", "type": "device_offline", "severity": "critical", "message": "设备离线超过 30 分钟", "occurred_at": "2026-08-12 09:18", "status": "active"},
    {"id": "ALT-1039", "camera_id": "CAM-002", "camera_name": "仓库一层通道", "type": "image_occlusion", "severity": "warning", "message": "画面遮挡持续 46 秒，现已恢复", "occurred_at": "2026-08-12 08:36", "status": "resolved"},
    {"id": "ALT-1035", "camera_id": "CAM-003", "camera_name": "园区西门", "type": "stream_interrupted", "severity": "warning", "message": "视频流发生 3 次短暂中断", "occurred_at": "2026-08-11 22:14", "status": "active"},
]

AUDIT_LOGS: list[dict] = []


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_diagnostics(camera: dict) -> dict:
    return {"power": "normal", "network": "normal", "packet_loss": 0.4, "latency_ms": 22, "storage": "normal", "temperature_c": 39, "image": "normal", "summary": "设备各项指标正常，暂未发现需要处置的问题。", "recommendations": ["保持当前巡检策略", "按月检查存储和固件版本"]}


def configured_business_api_key() -> str:
    """读取存量业务 API 的唯一认证密钥。

    云上环境通过环境变量注入；本地仅在环境变量缺失时从被 Git 忽略的
    ``APIG/.env`` 或项目根目录 ``.env`` 读取该单个字段。不会加载或输出其他
    敏感配置，也不会将密钥写入审计日志。
    """
    key = os.getenv(BUSINESS_API_KEY_ENV, "").strip()
    if key:
        return key

    for env_file in (ROOT / ".env", ROOT.parent / ".env"):
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                name, separator, value = line.partition("=")
                if separator and name.strip() == BUSINESS_API_KEY_ENV:
                    return value.strip().strip("\"'")
        except OSError:
            continue
    return ""


# ---------------------------------------------------------------------------
# 控制台登录态（浏览器前门鉴权）
#
# 网关级 static key_auth 需要每个请求头带 Authorization: Bearer，浏览器加载
# 页面无法自动携带，因此改由应用自身管理登录态：多用户账号密码 → 服务端
# PBKDF2 校验 → 签发 HttpOnly + 签名的会话 Cookie。密码与密钥均不下发浏览器；
# 会话 Cookie 为无状态签名 token（无需服务端存储），兼容 FaaS 多实例。
# 该层只保护「人访问控制台」；业务 API 的 X-API-Key 与 Runtime 的 key_auth
# 两层不受影响，仍由服务端代理持有密钥。
# ---------------------------------------------------------------------------

SESSION_COOKIE_NAME = "camera_console_session"
SESSION_TTL_SECONDS = int(os.getenv("CONSOLE_SESSION_TTL_SECONDS", str(12 * 3600)))
# 勾选「记住我」时使用的长有效期登录态（默认 30 天），期间无需重新登录。
# 明文密码不落盘：这里延长的是服务端签名会话 Cookie 的有效期，而非保存口令。
SESSION_REMEMBER_TTL_SECONDS = int(os.getenv("CONSOLE_REMEMBER_TTL_SECONDS", str(30 * 24 * 3600)))
PBKDF2_ITERATIONS = 200_000
_PBKDF2_ALGO = "sha256"

# 静态 login.html 缺失时的内联兜底登录页（纯前端，仅提交到 /api/login）。
_LOGIN_PAGE_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>登录 · 影腾视界摄像头运营中心</title>
<style>
body{margin:0;font-family:system-ui,-apple-system,"PingFang SC",sans-serif;background:#0f172a;color:#e2e8f0;display:flex;min-height:100vh;align-items:center;justify-content:center}
.card{background:#1e293b;padding:36px 32px;border-radius:16px;width:320px;box-shadow:0 20px 60px rgba(0,0,0,.4)}
h1{font-size:20px;margin:0 0 4px}p.sub{margin:0 0 24px;color:#94a3b8;font-size:13px}
label{display:block;font-size:13px;margin:14px 0 6px;color:#cbd5e1}
input{width:100%;box-sizing:border-box;padding:10px 12px;border-radius:8px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:14px}
.remember{display:flex;align-items:center;gap:8px;margin:16px 0 0;font-size:13px;color:#cbd5e1;cursor:pointer}
.remember input{width:auto;margin:0}
button{width:100%;margin-top:18px;padding:11px;border:0;border-radius:8px;background:#3b82f6;color:#fff;font-size:15px;cursor:pointer}
button:disabled{opacity:.6;cursor:not-allowed}
.err{margin-top:14px;color:#f87171;font-size:13px;min-height:16px}
.brand{display:flex;align-items:center;gap:10px;margin-bottom:20px}
.brand span{display:inline-flex;width:34px;height:34px;border-radius:9px;background:#3b82f6;align-items:center;justify-content:center;font-weight:700}
</style></head><body>
<form class="card" id="f">
<div class="brand"><span>影</span><div><b>影腾视界</b><br><small style="color:#94a3b8">Camera Operations</small></div></div>
<h1>控制台登录</h1><p class="sub">请输入账号与密码以访问摄像头运营中心</p>
<label>账号</label><input id="u" autocomplete="username" autofocus/>
<label>密码</label><input id="p" type="password" autocomplete="current-password"/>
<label class="remember"><input type="checkbox" id="r"/>记住我（30 天内免登录）</label>
<button id="b" type="submit">登录</button>
<div class="err" id="e"></div>
</form>
<script>
const f=document.getElementById('f'),b=document.getElementById('b'),e=document.getElementById('e'),u=document.getElementById('u'),r=document.getElementById('r');
// 预填上次登录的账号（仅存用户名，绝不保存密码）。
try{const su=localStorage.getItem('camera_console_user');if(su){u.value=su;r.checked=true;document.getElementById('p').focus();}}catch(_){}
f.onsubmit=async ev=>{ev.preventDefault();e.textContent='';b.disabled=true;b.textContent='登录中…';
try{const r2=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:document.getElementById('p').value,remember:r.checked})});
const d=await r2.json();if(r2.ok){try{if(r.checked){localStorage.setItem('camera_console_user',u.value);}else{localStorage.removeItem('camera_console_user');}}catch(_){}location.href='/';}else{e.textContent=d.error?.message||'登录失败';}}
catch(_){e.textContent='网络异常，请重试';}finally{b.disabled=false;b.textContent='登录';}};
</script></body></html>
"""


def _session_secret() -> bytes:
    """会话 Cookie 的签名密钥。

    优先取环境变量 CONSOLE_SESSION_SECRET（云上通过 runtime_envs 注入）。
    缺失时回退到进程级随机值——仅用于本地开发；此时进程重启会使旧会话失效，
    多实例之间也无法互认，因此生产必须显式配置。
    """
    secret = os.getenv("CONSOLE_SESSION_SECRET", "").strip()
    if secret:
        return secret.encode("utf-8")
    global _EPHEMERAL_SECRET
    try:
        return _EPHEMERAL_SECRET
    except NameError:
        _EPHEMERAL_SECRET = secrets.token_bytes(32)
        return _EPHEMERAL_SECRET


def _load_console_users() -> dict[str, str]:
    """加载多用户账号 → PBKDF2 口令哈希映射。

    来源为环境变量 CONSOLE_USERS，格式为分号分隔的
    ``用户名:pbkdf2$<iter>$<salt_b64>$<hash_b64>``；``:`` 后也允许直接写明文
    口令（仅便于本地演示，会即时哈希比对）。云上通过 runtime_envs 注入，
    明文口令不落盘、不进审计日志。
    """
    raw = os.getenv("CONSOLE_USERS", "").strip()
    if not raw:
        # 未显式配置时，从被 Git 忽略的 .env 兜底读取（本地开发用）。
        for env_file in (ROOT / ".env", ROOT.parent / ".env"):
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    name, separator, value = line.partition("=")
                    if separator and name.strip() == "CONSOLE_USERS":
                        raw = value.strip().strip("\"'")
                        break
            except OSError:
                continue
            if raw:
                break
    users: dict[str, str] = {}
    for entry in raw.split(";"):
        entry = entry.strip()
        if not entry or ":" not in entry:
            continue
        username, _, credential = entry.partition(":")
        username = username.strip()
        credential = credential.strip()
        if username and credential:
            users[username] = credential
    return users


def _hash_password(password: str, *, salt: bytes | None = None, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, password.encode("utf-8"), salt, iterations)
    return "pbkdf2${}${}${}".format(
        iterations,
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    )


def _verify_password(password: str, credential: str) -> bool:
    """校验口令。credential 可为 pbkdf2$ 哈希串或明文（本地演示）。"""
    if credential.startswith("pbkdf2$"):
        try:
            _, iter_s, salt_b64, hash_b64 = credential.split("$", 3)
            iterations = int(iter_s)
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(hash_b64)
        except (ValueError, base64.binascii.Error):
            return False
        actual = hashlib.pbkdf2_hmac(_PBKDF2_ALGO, password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    # 明文兜底：常数时间比较，避免时序侧信道。
    return hmac.compare_digest(password.encode("utf-8"), credential.encode("utf-8"))


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def issue_session_token(username: str, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    """签发无状态会话 token：base64url(payload).base64url(hmac)。

    ttl_seconds 控制登录态有效期：默认短会话（12h）；勾选「记住我」时传入
    SESSION_REMEMBER_TTL_SECONDS（默认 30 天）以免频繁重新登录。
    """
    payload = json.dumps(
        {"sub": username, "exp": int(time.time()) + ttl_seconds},
        separators=(",", ":"),
    ).encode("utf-8")
    signature = hmac.new(_session_secret(), payload, hashlib.sha256).digest()
    return f"{_b64url(payload)}.{_b64url(signature)}"


def verify_session_token(token: str) -> str | None:
    """校验会话 token，返回用户名；无效或过期返回 None。"""
    if not token or token.count(".") != 1:
        return None
    payload_b64, sig_b64 = token.split(".", 1)
    try:
        payload = _b64url_decode(payload_b64)
        signature = _b64url_decode(sig_b64)
    except (ValueError, base64.binascii.Error):
        return None
    expected = hmac.new(_session_secret(), payload, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or int(data.get("exp", 0)) < int(time.time()):
        return None
    sub = data.get("sub")
    return sub if isinstance(sub, str) and sub else None


def is_protected_business_api(method: str, path: str) -> bool:
    """仅保护会被转换为 MCP 工具的五个存量业务 API。"""
    if method == "GET":
        return (
            path in {"/api/cameras", "/api/alerts"}
            or bool(re.fullmatch(r"/api/cameras/CAM-\d+", path))
            or bool(re.fullmatch(r"/api/cameras/CAM-\d+/diagnostics", path))
        )
    return method == "PATCH" and bool(re.fullmatch(r"/api/cameras/CAM-\d+/maintenance-status", path))


def extract_agent_message(payload) -> str:
    """兼容 Runtime 返回字符串或常见 JSON 包装，避免向前端暴露原始结构。"""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in ("message", "response", "content", "result", "data", "output"):
            if key in payload:
                return extract_agent_message(payload[key])
    if isinstance(payload, list):
        return "\n".join(filter(None, (extract_agent_message(item) for item in payload)))
    return str(payload or "")


def parse_sse_agent_response(raw: str) -> str | None:
    """解析 ADK Agent Server（WebServer App）的 SSE 事件流，聚合可见文本。

    Runtime 改造为 AgentkitAgentServerApp 后，/invoke·/run_sse 返回一连串
    `data: {...}` 事件而非单个 JSON：
    - content.parts[].text 是模型输出；thought=True 的部分是思考过程，需隐藏。
    - partial=True 为增量分片；partial 缺失/False 的事件携带该轮完整文本。
    未解析到任何 data 事件时返回 None，交由旧的 JSON 分支处理。
    """
    events = []
    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        chunk = line[len("data:"):].strip()
        if not chunk or chunk == "[DONE]":
            continue
        try:
            events.append(json.loads(chunk))
        except json.JSONDecodeError:
            continue
    if not events:
        return None

    def visible_text(event) -> str:
        if not isinstance(event, dict):
            return ""
        parts = (event.get("content") or {}).get("parts") or []
        texts = []
        for part in parts:
            # 跳过思考过程分片，只保留面向用户的正式回答。
            if not isinstance(part, dict) or part.get("thought"):
                continue
            text = part.get("text")
            if text:
                texts.append(text)
        return "".join(texts)

    # 优先取非增量（完整）事件文本，避免与 partial 分片重复叠加。
    final_text = "".join(visible_text(e) for e in events if not e.get("partial"))
    if final_text.strip():
        return final_text
    # 回退：拼接所有增量分片。
    aggregated = "".join(visible_text(e) for e in events)
    return aggregated or None


def _runtime_base_url(runtime_url: str) -> str:
    """从配置的 Runtime URL 推导 Agent Server 基地址。

    历史配置可能带 /invoke、/run、/run_sse 等后缀；WebServer App 的标准
    调用需要基地址来拼接 session API 与 /run_sse，故在此归一化。
    """
    base = runtime_url.strip().rstrip("/")
    for suffix in ("/run_sse", "/run", "/invoke"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base.rstrip("/")


def invoke_agent_runtime(message: str, user_id: str, session_id: str) -> str:
    """由 Web 后端代理调用 Agent Runtime，调用密钥不下发至浏览器。

    Runtime 为 WebServer App（AgentkitAgentServerApp），调用遵循 ADK Agent
    Server 约定：先创建/复用 session，再 POST /run_sse 获取 SSE 事件流。
    """
    runtime_url = os.getenv("AGENT_RUNTIME_URL", "").strip()
    runtime_key = os.getenv("AGENT_RUNTIME_API_KEY", "").strip()
    app_name = os.getenv("AGENT_RUNTIME_APP_NAME", "yingteng_camera_support").strip()
    if not runtime_url or not runtime_key:
        raise RuntimeError("AI 诊断助手尚未完成 Runtime 调用配置")

    base_url = _runtime_base_url(runtime_url)
    timeout = float(os.getenv("AGENT_RUNTIME_TIMEOUT_SECONDS", "90"))
    ca_bundle = os.getenv("AGENT_RUNTIME_CA_BUNDLE", "").strip()
    if not ca_bundle:
        # 本机 Python 默认 CA 链不包含公司网络证书时，使用 certifi 的受信任根证书包。
        # 仍保持 HTTPS 证书校验，不能用关闭校验的方式绕过该问题。
        try:
            import certifi

            ca_bundle = certifi.where()
        except ImportError:
            pass
    ssl_context = ssl.create_default_context(cafile=ca_bundle or None)
    auth_headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {runtime_key}",
    }

    def _post(path: str, payload: dict) -> str:
        body = json.dumps(payload, ensure_ascii=False).encode()
        request = urlrequest.Request(
            f"{base_url}{path}", data=body, headers=auth_headers, method="POST"
        )
        with urlrequest.urlopen(request, timeout=timeout, context=ssl_context) as response:
            return response.read().decode("utf-8")

    from urllib.parse import quote

    session_path = (
        f"/apps/{quote(app_name)}/users/{quote(user_id)}/sessions/{quote(session_id)}"
    )
    try:
        # 幂等创建 session：Runtime 对已存在的 session 返回 409，视为正常复用。
        try:
            _post(session_path, {})
        except urlerror.HTTPError as exc:
            if exc.code != 409:
                raise
        raw_response = _post(
            "/run_sse",
            {
                "appName": app_name,
                "userId": user_id,
                "sessionId": session_id,
                "newMessage": {"role": "user", "parts": [{"text": message}]},
            },
        )
    except urlerror.HTTPError as exc:
        raise RuntimeError(f"Agent Runtime 返回 HTTP {exc.code}") from exc
    except (urlerror.URLError, TimeoutError) as exc:
        raise RuntimeError("暂时无法连接 Agent Runtime，请稍后重试") from exc

    # WebServer App 返回 SSE 事件流，优先按 SSE 解析；解析不到 data 事件时
    # 回退到旧的单 JSON / 纯文本兼容逻辑。
    sse_text = parse_sse_agent_response(raw_response)
    if sse_text is not None:
        return sse_text
    try:
        return extract_agent_message(json.loads(raw_response))
    except json.JSONDecodeError:
        return raw_response


class Handler(BaseHTTPRequestHandler):
    server_version = "YingtengCameraDemo/1.0"

    def log_message(self, *_args):
        return

    def _send_json(self, status: int, payload: dict | list, request_id: str | None = None):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Request-Id", request_id or str(uuid.uuid4()))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode())

    def _is_business_api_key_valid(self) -> bool:
        expected = configured_business_api_key()
        supplied = self.headers.get("X-API-Key", "")
        return bool(expected and supplied and hmac.compare_digest(supplied, expected))

    def _current_session_user(self) -> str | None:
        """从 Cookie 解析当前登录用户名；未登录返回 None。"""
        cookie_header = self.headers.get("Cookie", "")
        if not cookie_header:
            return None
        try:
            jar = SimpleCookie()
            jar.load(cookie_header)
        except Exception:
            return None
        morsel = jar.get(SESSION_COOKIE_NAME)
        if not morsel:
            return None
        return verify_session_token(morsel.value)

    def _set_session_cookie(self, token: str, max_age: int = SESSION_TTL_SECONDS) -> str:
        """构造登录会话 Cookie：HttpOnly + SameSite=Lax + Secure。

        max_age 与 token 有效期保持一致：默认短会话；勾选「记住我」时传入
        长有效期，浏览器重开也能保留登录态（这是「记住登录」而非保存明文密码）。
        """
        attrs = [
            f"{SESSION_COOKIE_NAME}={token}",
            "Path=/",
            f"Max-Age={max_age}",
            "HttpOnly",
            "SameSite=Lax",
            "Secure",
        ]
        return "; ".join(attrs)

    def _clear_session_cookie(self) -> str:
        return f"{SESSION_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax; Secure"

    def _redirect(self, location: str):
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _require_api_authorized(self, method: str, path: str, started: float, request_id: str) -> bool:
        """/api/* 授权闸门。

        - 浏览器：凭有效登录会话（Cookie）访问任意控制台接口。
        - 机器/MCP：凭 X-API-Key 直连受保护业务 API（无需登录会话）。
        未通过时直接写 401 响应并返回 False。
        """
        if self._current_session_user():
            return True
        if is_protected_business_api(method, path) and self._is_business_api_key_valid():
            return True
        self._audit(started, 401, False, request_id)
        self._send_json(401, {
            "error": {
                "code": "login_required",
                "message": "请先登录控制台，或提供有效的 X-API-Key",
            }
        }, request_id)
        return False

    def _serve_login_page(self):
        target = STATIC / "login.html"
        if target.is_file():
            return self._send_file(target)
        # 兜底内联登录页，避免静态文件缺失时无法登录。
        body = _LOGIN_PAGE_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _audit(self, started: float, status: int, authenticated: bool, request_id: str, body: dict | None = None):
        parsed = urlparse(self.path)
        AUDIT_LOGS.insert(0, {
            "id": request_id,
            "time": utc_now(),
            "method": self.command,
            "path": parsed.path,
            "query": parse_qs(parsed.query),
            "body": body or {},
            "status": status,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            "authenticated": authenticated,
        })
        del AUDIT_LOGS[100:]

    def do_GET(self):
        started, request_id = time.perf_counter(), str(uuid.uuid4())
        parsed = urlparse(self.path)
        path = parsed.path
        # 公开路径：健康检查、登录页、OpenAPI（供机器/网关读取，非敏感数据）。
        if path == "/health":
            return self._send_json(200, {"status": "ok", "service": "yingteng-camera-demo"}, request_id)
        if path == "/openapi.yaml":
            return self._send_file(ROOT / "openapi.yaml")
        if path == "/login":
            # 已登录直接进控制台，避免重复登录。
            if self._current_session_user():
                return self._redirect("/")
            return self._serve_login_page()
        if path == "/api/session":
            # 供前端探测当前登录态。
            user = self._current_session_user()
            return self._send_json(200, {"authenticated": bool(user), "user": user}, request_id)

        if not path.startswith("/api/"):
            # 控制台页面/静态资源需登录；未登录一律跳转登录页。
            if not self._current_session_user():
                return self._redirect("/login")
            return self._serve_static(path)

        # /api/* 统一授权：浏览器登录会话，或机器侧 X-API-Key。
        if not self._require_api_authorized("GET", path, started, request_id):
            return
        query = parse_qs(parsed.query)
        status, payload = 200, {}
        if path == "/api/dashboard":
            counts = {key: sum(c["status"] == key for c in CAMERAS.values()) for key in ("online", "degraded", "offline")}
            payload = {"total": len(CAMERAS), **counts, "active_alerts": sum(a["status"] == "active" for a in ALERTS), "pending_maintenance": sum(c["maintenance_status"] == "pending" for c in CAMERAS.values())}
        elif path == "/api/cameras":
            cameras = list(CAMERAS.values())
            if query.get("status"):
                cameras = [c for c in cameras if c["status"] == query["status"][0]]
            if query.get("search"):
                term = query["search"][0].lower()
                cameras = [c for c in cameras if term in f'{c["id"]} {c["name"]} {c["site"]}'.lower()]
            payload = {"items": cameras, "total": len(cameras)}
        elif path == "/api/alerts":
            alerts = ALERTS
            if query.get("camera_id"):
                alerts = [a for a in alerts if a["camera_id"] == query["camera_id"][0]]
            payload = {"items": alerts, "total": len(alerts)}
        elif path == "/api/audit-logs":
            payload = {"items": AUDIT_LOGS[:30], "total": len(AUDIT_LOGS)}
        elif (match := re.fullmatch(r"/api/cameras/(CAM-\d+)", path)):
            camera = CAMERAS.get(match.group(1))
            if camera:
                payload = camera
            else:
                status, payload = 404, {"error": {"code": "camera_not_found", "message": "摄像头不存在"}}
        elif (match := re.fullmatch(r"/api/cameras/(CAM-\d+)/diagnostics", path)):
            camera = CAMERAS.get(match.group(1))
            if camera:
                payload = {"camera_id": camera["id"], "camera_name": camera["name"], "checked_at": utc_now(), **DIAGNOSTICS.get(camera["id"], default_diagnostics(camera))}
            else:
                status, payload = 404, {"error": {"code": "camera_not_found", "message": "摄像头不存在"}}
        else:
            status, payload = 404, {"error": {"code": "not_found", "message": "接口不存在"}}
        self._audit(started, status, True, request_id)
        self._send_json(status, payload, request_id)

    def do_PATCH(self):
        started, request_id = time.perf_counter(), str(uuid.uuid4())
        parsed = urlparse(self.path)
        path = parsed.path
        if not self._require_api_authorized("PATCH", path, started, request_id):
            return
        try:
            body = self._read_json()
        except (ValueError, UnicodeDecodeError):
            self._audit(started, 400, True, request_id)
            return self._send_json(400, {"error": {"code": "invalid_json", "message": "请求体必须是 JSON"}}, request_id)
        match = re.fullmatch(r"/api/cameras/(CAM-\d+)/maintenance-status", path)
        if not match or match.group(1) not in CAMERAS:
            status, payload = 404, {"error": {"code": "camera_not_found", "message": "摄像头不存在"}}
        elif body.get("status") not in {"normal", "pending", "in_progress", "completed"}:
            status, payload = 422, {"error": {"code": "invalid_status", "message": "检修状态不合法"}}
        else:
            camera = CAMERAS[match.group(1)]
            camera["maintenance_status"] = body["status"]
            payload, status = {"camera_id": camera["id"], "maintenance_status": camera["maintenance_status"], "updated_at": utc_now(), "message": "检修状态已更新"}, 200
        self._audit(started, status, True, request_id, body)
        self._send_json(status, payload, request_id)

    def do_POST(self):
        started, request_id = time.perf_counter(), str(uuid.uuid4())
        path = urlparse(self.path).path
        if path == "/api/login":
            return self._handle_login(started, request_id)
        if path == "/api/logout":
            return self._handle_logout(started, request_id)
        if path != "/api/agent/chat":
            self._audit(started, 404, True, request_id)
            return self._send_json(404, {"error": {"code": "not_found", "message": "接口不存在"}}, request_id)
        # 诊断助手会真实调用 Agent Runtime，仅限已登录会话访问。
        if not self._current_session_user():
            self._audit(started, 401, False, request_id)
            return self._send_json(401, {"error": {"code": "login_required", "message": "请先登录控制台"}}, request_id)
        try:
            body = self._read_json()
        except (ValueError, UnicodeDecodeError):
            self._audit(started, 400, True, request_id)
            return self._send_json(400, {"error": {"code": "invalid_json", "message": "请求体必须是 JSON"}}, request_id)

        message = str(body.get("message", "")).strip()
        if not message:
            self._audit(started, 422, True, request_id, body)
            return self._send_json(422, {"error": {"code": "message_required", "message": "请输入需要诊断的问题"}}, request_id)
        if len(message) > 2000:
            self._audit(started, 422, True, request_id, body)
            return self._send_json(422, {"error": {"code": "message_too_long", "message": "问题不能超过 2000 个字符"}}, request_id)

        user_id = str(body.get("user_id", "web-console-user")).strip()[:128] or "web-console-user"
        session_id = str(body.get("session_id", "web-console-session")).strip()[:128] or "web-console-session"
        try:
            answer = invoke_agent_runtime(message, user_id, session_id)
        except RuntimeError as exc:
            self._audit(started, 503, True, request_id, body)
            return self._send_json(503, {"error": {"code": "agent_runtime_unavailable", "message": str(exc)}}, request_id)

        self._audit(started, 200, True, request_id, body)
        self._send_json(200, {"answer": answer, "runtime": "yingteng-camera-support"}, request_id)

    def _handle_login(self, started: float, request_id: str):
        try:
            body = self._read_json()
        except (ValueError, UnicodeDecodeError):
            self._audit(started, 400, False, request_id)
            return self._send_json(400, {"error": {"code": "invalid_json", "message": "请求体必须是 JSON"}}, request_id)
        username = str(body.get("username", "")).strip()[:128]
        password = str(body.get("password", ""))
        users = _load_console_users()
        credential = users.get(username)
        # 用户名不存在也执行一次哈希，尽量抹平存在性时序差异；口令不进审计日志。
        if credential is None:
            _verify_password(password, _hash_password("__no_such_user__"))
            authed = False
        else:
            authed = _verify_password(password, credential)
        if not authed:
            self._audit(started, 401, False, request_id, {"username": username})
            return self._send_json(401, {"error": {"code": "invalid_credentials", "message": "账号或密码错误"}}, request_id)
        # 「记住我」：勾选后签发长有效期登录态（默认 30 天），期间免重复登录。
        remember = bool(body.get("remember"))
        ttl = SESSION_REMEMBER_TTL_SECONDS if remember else SESSION_TTL_SECONDS
        token = issue_session_token(username, ttl)
        body_bytes = json.dumps({"ok": True, "user": username}, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Set-Cookie", self._set_session_cookie(token, ttl))
        self.send_header("X-Request-Id", request_id)
        self.end_headers()
        self.wfile.write(body_bytes)
        self._audit(started, 200, True, request_id, {"username": username})

    def _handle_logout(self, started: float, request_id: str):
        body_bytes = json.dumps({"ok": True}, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.send_header("Set-Cookie", self._clear_session_cookie())
        self.send_header("X-Request-Id", request_id)
        self.end_headers()
        self.wfile.write(body_bytes)
        self._audit(started, 200, True, request_id)

    def _serve_static(self, path: str):
        relative = "index.html" if path in {"", "/"} else path.lstrip("/")
        target = (STATIC / relative).resolve()
        if STATIC not in target.parents and target != STATIC:
            return self._send_json(403, {"error": {"message": "Forbidden"}})
        if not target.is_file():
            target = STATIC / "index.html"
        self._send_file(target)

    def _send_file(self, path: Path):
        if not path.is_file():
            return self._send_json(404, {"error": {"message": "Not found"}})
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run():
    host = os.getenv("CAMERA_HOST", "127.0.0.1")
    port = int(os.getenv("CAMERA_PORT", "8000"))
    print(f"Yingteng Camera Demo: http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    run()
