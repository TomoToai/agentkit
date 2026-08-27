#!/usr/bin/env python3
"""刷新火山引擎 CR (容器镜像仓库) 临时登录 token。

CR 登录凭据是 12h 临时票据，过期会同时导致 docker push 401 和 Pod ImagePullBackOff。
本脚本用根目录 .env 的 AK/SK 调用 cr:GetAuthorizationToken，打印临时 Username/Password，
供 docker login 与刷新 K8s docker-registry Secret 复用。

用法：python3 scripts/refresh_cr_token.py [Registry]
默认 Registry = limengtao-cr-demo（cn-beijing）。
"""
import json
import os
import sys

from volcengine.ApiInfo import ApiInfo
from volcengine.Credentials import Credentials
from volcengine.ServiceInfo import ServiceInfo
from volcengine.base.Service import Service


def load_env(env_path):
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())


class CrService(Service):
    def __init__(self, region, ak, sk):
        service_info = ServiceInfo(
            "open.volcengineapi.com",
            {"Accept": "application/json"},
            Credentials(ak, sk, "cr", region),
            10,
            10,
            "https",
        )
        api_info = {
            "GetAuthorizationToken": ApiInfo(
                "POST", "/",
                {"Action": "GetAuthorizationToken", "Version": "2022-05-12"},
                {}, {},
            )
        }
        super().__init__(service_info, api_info)


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    load_env(os.path.join(root, ".env"))
    ak = os.environ.get("VOLCENGINE_ACCESS_KEY")
    sk = os.environ.get("VOLCENGINE_SECRET_KEY")
    if not ak or not sk:
        print("missing VOLCENGINE_ACCESS_KEY/SECRET_KEY in .env", file=sys.stderr)
        sys.exit(1)

    region = os.environ.get("CR_REGION", "cn-beijing")
    registry = sys.argv[1] if len(sys.argv) > 1 else "limengtao-cr-demo"

    svc = CrService(region, ak, sk)
    body = json.dumps({"Registry": registry})
    resp = svc.json("GetAuthorizationToken", {}, body)
    data = json.loads(resp)
    result = data.get("Result", {})
    token = result.get("Token")
    username = result.get("Username")
    if not token or not username:
        print("unexpected response: " + resp, file=sys.stderr)
        sys.exit(1)
    # 单行输出，便于 shell 解析：USERNAME<TAB>PASSWORD
    print(f"{username}\t{token}")


if __name__ == "__main__":
    main()
