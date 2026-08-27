#!/usr/bin/env python3
"""从无 API 文档的 Python 存量服务源码中扫描业务路由并生成 OpenAPI 3.0 文件。

扫描器以 ``server.py`` 中的 HTTP Handler 路由为接口事实来源；业务语义、参数
和响应结构由受控目录补全。这样既能避免手工维护路径清单，也不会把 Web 聊天、
审计等非业务接口错误暴露给 MCP。
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


BUSINESS_OPERATIONS: dict[tuple[str, str], dict[str, Any]] = {
    ("GET", "/api/cameras"): {
        "operationId": "list_cameras",
        "summary": "查询摄像头列表",
        "description": "按状态或关键词定位设备和发现离线设备。",
        "parameters": [
            {"name": "status", "in": "query", "required": False,
             "schema": {"type": "string", "enum": ["online", "degraded", "offline"]}},
            {"name": "search", "in": "query", "required": False, "schema": {"type": "string"}},
        ],
        "responses": {"200": {"description": "摄像头列表"}},
    },
    ("GET", "/api/cameras/{camera_id}"): {
        "operationId": "get_camera",
        "summary": "查询单个摄像头详情",
        "parameters": [{"$ref": "#/components/parameters/CameraId"}],
        "responses": {"200": {"description": "摄像头详情"}, "404": {"description": "摄像头不存在"}},
    },
    ("GET", "/api/cameras/{camera_id}/diagnostics"): {
        "operationId": "diagnose_camera",
        "summary": "获取摄像头诊断指标",
        "description": "返回供电、网络、丢包、延迟、存储、温度和画面状态。",
        "parameters": [{"$ref": "#/components/parameters/CameraId"}],
        "responses": {"200": {"description": "诊断结果"}, "404": {"description": "摄像头不存在"}},
    },
    ("GET", "/api/alerts"): {
        "operationId": "list_camera_alerts",
        "summary": "查询摄像头近期告警",
        "parameters": [{"name": "camera_id", "in": "query", "required": False,
                        "description": "不传则返回所有告警", "schema": {"type": "string"}}],
        "responses": {"200": {"description": "告警列表"}},
    },
    ("PATCH", "/api/cameras/{camera_id}/maintenance-status"): {
        "operationId": "update_camera_maintenance_status",
        "summary": "更新摄像头检修状态",
        "description": "写操作；仅在用户明确确认后执行。",
        "parameters": [{"$ref": "#/components/parameters/CameraId"}],
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": {
                "type": "object",
                "required": ["status"],
                "properties": {
                    "status": {"type": "string", "enum": ["normal", "pending", "in_progress", "completed"]},
                    "reason": {"type": "string"},
                },
            }}},
        },
        "responses": {"200": {"description": "更新成功"}, "404": {"description": "摄像头不存在"}},
    },
}

REGEX_ROUTE_TEMPLATES = {
    r"/api/cameras/(CAM-\d+)": "/api/cameras/{camera_id}",
    r"/api/cameras/(CAM-\d+)/diagnostics": "/api/cameras/{camera_id}/diagnostics",
    r"/api/cameras/(CAM-\d+)/maintenance-status": "/api/cameras/{camera_id}/maintenance-status",
}


def string_literal(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def route_from_regex(pattern: str) -> str | None:
    return REGEX_ROUTE_TEMPLATES.get(pattern)


class RouteScanner(ast.NodeVisitor):
    """扫描 BaseHTTPRequestHandler 的 do_GET/do_POST/do_PATCH 方法。"""

    def __init__(self) -> None:
        self.routes: set[tuple[str, str]] = set()
        self.method = ""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        methods = {"do_GET": "GET", "do_POST": "POST", "do_PATCH": "PATCH", "do_PUT": "PUT", "do_DELETE": "DELETE"}
        if node.name not in methods:
            return
        previous, self.method = self.method, methods[node.name]
        self.generic_visit(node)
        self.method = previous

    def visit_Compare(self, node: ast.Compare) -> None:
        for candidate in [node.left, *node.comparators]:
            route = string_literal(candidate)
            if route and route.startswith("/api/"):
                self.routes.add((self.method, route))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if (isinstance(node.func, ast.Attribute) and node.func.attr == "fullmatch" and
                len(node.args) >= 1):
            pattern = string_literal(node.args[0])
            if pattern and (route := route_from_regex(pattern)):
                self.routes.add((self.method, route))
        self.generic_visit(node)


def scan_routes(source: Path) -> set[tuple[str, str]]:
    scanner = RouteScanner()
    scanner.visit(ast.parse(source.read_text(encoding="utf-8"), filename=str(source)))
    return scanner.routes


def build_spec(source: Path, server_url: str) -> dict[str, Any]:
    discovered = scan_routes(source)
    expected = set(BUSINESS_OPERATIONS)
    missing = expected - discovered
    if missing:
        names = ", ".join(f"{method} {path}" for method, path in sorted(missing))
        raise ValueError(f"源码中未扫描到预期业务路由：{names}")

    paths: dict[str, dict[str, Any]] = {}
    for (method, path), operation in BUSINESS_OPERATIONS.items():
        if (method, path) in discovered:
            paths.setdefault(path, {})[method.lower()] = operation

    return {
        "openapi": "3.0.3",
        "info": {
            "title": "影腾摄像头管理 API（源码自动生成）",
            "version": "1.0.0",
            "description": "由 server.py 路由扫描生成；仅包含可安全转换为 MCP 工具的存量业务 API。",
        },
        "servers": [{"url": server_url}],
        "security": [{"ApiKeyAuth": []}],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "存量业务 API 的访问密钥；由 MCP 出站凭据托管并注入。",
                }
            },
            "parameters": {
                "CameraId": {
                    "name": "camera_id", "in": "path", "required": True,
                    "schema": {"type": "string", "example": "CAM-003"},
                }
            }
        },
    }


def scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def yaml_key(key: Any) -> str:
    """OpenAPI 的响应码必须是字符串键，不能被 YAML 解释为整数。"""
    text = str(key)
    return json.dumps(text, ensure_ascii=False) if text.isdigit() else text


def yaml_lines(value: Any, indent: int = 0) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                if not child:
                    lines.append(f"{pad}{yaml_key(key)}: {'{}' if isinstance(child, dict) else '[]'}")
                else:
                    lines.append(f"{pad}{yaml_key(key)}:")
                    lines.extend(yaml_lines(child, indent + 2))
            else:
                lines.append(f"{pad}{yaml_key(key)}: {scalar(child)}")
        return lines
    if isinstance(value, list):
        lines = []
        for child in value:
            if isinstance(child, dict):
                if not child:
                    lines.append(f"{pad}- {{}}")
                else:
                    first, *rest = yaml_lines(child, indent + 2)
                    lines.append(f"{pad}- {first.lstrip()}")
                    lines.extend(rest)
            elif isinstance(child, list):
                if not child:
                    lines.append(f"{pad}- []")
                else:
                    lines.append(f"{pad}-")
                    lines.extend(yaml_lines(child, indent + 2))
            else:
                lines.append(f"{pad}- {scalar(child)}")
        return lines
    return [f"{pad}{scalar(value)}"]


def render_yaml(spec: dict[str, Any]) -> str:
    header = [
        "# 自动生成：请勿手工编辑。",
        "# 来源：APIG/server.py；命令：python3 scripts/generate_openapi_from_source.py",
        "",
    ]
    return "\n".join([*header, *yaml_lines(spec), ""])


def main() -> int:
    parser = argparse.ArgumentParser(description="从 Python 存量服务源码生成 OpenAPI 3.0 YAML")
    parser.add_argument("--source", type=Path, default=Path("server.py"), help="存量服务源码路径")
    parser.add_argument("--output", type=Path, default=Path("openapi.generated.yaml"), help="生成文件路径")
    parser.add_argument("--server-url", default="http://localhost:8000", help="存量服务访问基地址")
    parser.add_argument("--check", action="store_true", help="仅校验生成文件是否与当前源码一致")
    args = parser.parse_args()

    try:
        content = render_yaml(build_spec(args.source, args.server_url))
    except (OSError, SyntaxError, ValueError) as exc:
        print(f"生成失败：{exc}", file=sys.stderr)
        return 1

    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != content:
            print(f"校验失败：{args.output} 与当前源码扫描结果不一致", file=sys.stderr)
            return 1
        print(f"校验通过：{args.output}（5 个存量业务 API）")
        return 0

    args.output.write_text(content, encoding="utf-8")
    print(f"已生成 {args.output}（5 个存量业务 API）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
