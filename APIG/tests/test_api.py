import json
import os
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

from server import Handler


class ApiTest(unittest.TestCase):
    API_KEY = "test-business-api-key"
    CONSOLE_USER = "tester"
    CONSOLE_PASS = "S3cret-pass!"

    @classmethod
    def setUpClass(cls):
        cls.environment = mock.patch.dict(
            os.environ,
            {
                "BUSINESS_API_KEY": cls.API_KEY,
                # 控制台登录态：多用户账号密码 + 固定签名密钥（便于测试可复现）。
                "CONSOLE_USERS": f"{cls.CONSOLE_USER}:{cls.CONSOLE_PASS}",
                "CONSOLE_SESSION_SECRET": "unit-test-session-secret",
            },
            clear=False,
        )
        cls.environment.start()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.environment.stop()

    def request(self, path, method="GET", body=None, api_key=API_KEY, cookie=None):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if api_key is not None:
            headers["X-API-Key"] = api_key
        if cookie is not None:
            headers["Cookie"] = cookie
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)

    def login(self, username=None, password=None):
        """执行登录，返回可用于后续请求的会话 Cookie 字符串。"""
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/api/login",
            data=json.dumps(
                {"username": username or self.CONSOLE_USER, "password": password or self.CONSOLE_PASS}
            ).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as response:
            set_cookie = response.headers.get("Set-Cookie", "")
        # 仅保留 name=value 主体，去掉属性段。
        return set_cookie.split(";", 1)[0]

    # ---- 机器/MCP 侧：X-API-Key 仍保护 5 个存量业务 API ----

    def test_missing_credentials_is_rejected(self):
        status, payload = self.request("/api/cameras", api_key=None)
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "login_required")

    def test_missing_business_api_key_configuration_fails_closed(self):
        with mock.patch.dict(os.environ, {"BUSINESS_API_KEY": ""}, clear=False):
            status, payload = self.request("/api/cameras", api_key=self.API_KEY)
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "login_required")

    def test_invalid_business_api_key_is_rejected(self):
        status, payload = self.request("/api/cameras", api_key="not-the-business-api-key")
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "login_required")

    def test_write_business_api_without_credentials_is_rejected(self):
        status, payload = self.request(
            "/api/cameras/CAM-003/maintenance-status",
            "PATCH",
            {"status": "pending"},
            api_key=None,
        )
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "login_required")

    def test_valid_business_api_key_is_accepted(self):
        status, payload = self.request("/api/cameras")
        self.assertEqual(status, 200)
        self.assertEqual(payload["total"], 6)

    def test_lists_and_diagnoses_camera_via_api_key(self):
        status, payload = self.request("/api/cameras?status=degraded")
        self.assertEqual(status, 200)
        self.assertEqual(payload["items"][0]["id"], "CAM-003")
        _, diagnosis = self.request("/api/cameras/CAM-003/diagnostics")
        self.assertEqual(diagnosis["network"], "critical")
        self.assertGreater(diagnosis["packet_loss"], 30)

    def test_updates_maintenance_status_via_api_key(self):
        status, payload = self.request("/api/cameras/CAM-003/maintenance-status", "PATCH", {"status": "pending", "reason": "test"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["maintenance_status"], "pending")

    # ---- 产品使用指南知识库：型号目录与型号级指南检索 ----

    def test_lists_product_guides(self):
        status, payload = self.request("/api/product-guides")
        self.assertEqual(status, 200)
        self.assertEqual(payload["total"], 30)
        skus = {item["sku"] for item in payload["items"]}
        # 必须包含现网 6 台设备使用的 3 个型号。
        self.assertTrue({"YT-IPC-4K", "YT-DOME-2K", "YT-PTZ-4K"}.issubset(skus))

    def test_searches_product_guides_by_keyword(self):
        status, payload = self.request("/api/product-guides?search=" + urllib.parse.quote("球机"))
        self.assertEqual(status, 200)
        self.assertGreater(payload["total"], 0)
        self.assertTrue(all("YT-" in item["sku"] for item in payload["items"]))

    def test_gets_product_guide_by_sku(self):
        status, payload = self.request("/api/product-guides/YT-IPC-4K")
        self.assertEqual(status, 200)
        self.assertEqual(payload["sku"], "YT-IPC-4K")
        self.assertIn("使用指南", payload["guide"])

    def test_unknown_sku_returns_404_with_available_list(self):
        status, payload = self.request("/api/product-guides/YT-NOT-EXIST")
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"]["code"], "guide_not_found")
        self.assertIn("YT-IPC-4K", payload["error"]["available_skus"])

    def test_product_guides_require_credentials(self):
        status, payload = self.request("/api/product-guides", api_key=None)
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "login_required")

    def test_product_guides_readable_via_session(self):
        cookie = self.login()
        status, payload = self.request("/api/product-guides/YT-DOME-2K", api_key=None, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(payload["sku"], "YT-DOME-2K")

    # ---- 浏览器侧：登录会话取代 ui=1 BFF，密钥不下发浏览器 ----

    def test_login_rejects_wrong_password(self):
        status, payload = self.request(
            "/api/login", "POST", {"username": self.CONSOLE_USER, "password": "wrong"}, api_key=None
        )
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "invalid_credentials")

    def test_session_reads_protected_data_without_api_key(self):
        cookie = self.login()
        status, payload = self.request("/api/cameras", api_key=None, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(payload["total"], 6)

    def test_session_supports_camera_diagnosis(self):
        cookie = self.login()
        status, payload = self.request("/api/cameras/CAM-003/diagnostics", api_key=None, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertEqual(payload["camera_id"], "CAM-003")

    def test_session_endpoint_reports_authentication(self):
        cookie = self.login()
        status, payload = self.request("/api/session", api_key=None, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertTrue(payload["authenticated"])
        self.assertEqual(payload["user"], self.CONSOLE_USER)

    def test_health_remains_public(self):
        status, payload = self.request("/health", api_key=None)
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

    def test_agent_chat_requires_login(self):
        status, payload = self.request(
            "/api/agent/chat", "POST", {"message": "园区西门为什么没有画面？"}, api_key=None
        )
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "login_required")

    def test_agent_chat_reports_missing_runtime_configuration_when_logged_in(self):
        cookie = self.login()
        with mock.patch.dict(os.environ, {"AGENT_RUNTIME_URL": "", "AGENT_RUNTIME_API_KEY": ""}, clear=False):
            status, payload = self.request(
                "/api/agent/chat",
                "POST",
                {"message": "园区西门为什么没有画面？"},
                api_key=None,
                cookie=cookie,
            )
        self.assertEqual(status, 503)
        self.assertEqual(payload["error"]["code"], "agent_runtime_unavailable")


if __name__ == "__main__":
    unittest.main()
