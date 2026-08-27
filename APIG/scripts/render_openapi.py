#!/usr/bin/env python3
"""Render a deploy-specific OpenAPI document without mutating the template."""

import os
from pathlib import Path

base = os.environ.get("CAMERA_PUBLIC_BASE_URL", "").rstrip("/")
if not base.startswith("https://"):
    raise SystemExit("CAMERA_PUBLIC_BASE_URL 必须是 AgentKit 可访问的 HTTPS 地址")

template = Path(__file__).resolve().parents[1] / "openapi.yaml"
output = Path(__file__).resolve().parents[1] / "build" / "openapi.gateway.yaml"
output.parent.mkdir(exist_ok=True)
text = template.read_text()
text = text.replace("http://host.docker.internal:8000", base)
output.write_text(text)
print(output)

