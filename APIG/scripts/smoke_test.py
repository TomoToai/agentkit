#!/usr/bin/env python3
"""Smoke-test a deployed camera API without printing its API key."""

import json
import os
import sys
import urllib.request

base = os.environ.get("CAMERA_PUBLIC_BASE_URL", "").rstrip("/")
key = os.environ.get("RUNTIME_API_KEY", "")
if not base or not key:
    raise SystemExit("请设置 CAMERA_PUBLIC_BASE_URL 和 RUNTIME_API_KEY")


def request(path, method="GET", body=None):
    payload = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        base + path,
        data=payload,
        method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.status, json.load(response)


checks = []
status, health = request("/health")
checks.append(("health", status == 200 and health.get("status") == "ok"))
status, cameras = request("/api/cameras?status=degraded")
checks.append(("list_cameras", status == 200 and cameras["items"][0]["id"] == "CAM-003"))
status, diagnosis = request("/api/cameras/CAM-003/diagnostics")
checks.append(("diagnose_camera", status == 200 and diagnosis["packet_loss"] == 38.4))
status, update = request("/api/cameras/CAM-003/maintenance-status", "PATCH", {"status": "pending", "reason": "联调冒烟测试"})
checks.append(("update_maintenance", status == 200 and update["maintenance_status"] == "pending"))

print(json.dumps({"base_url": base, "checks": [{"name": n, "passed": p} for n, p in checks]}, ensure_ascii=False, indent=2))
sys.exit(0 if all(p for _, p in checks) else 1)
