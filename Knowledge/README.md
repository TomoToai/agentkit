# Knowledge · 影腾摄像头产品使用指南知识库

面向"客户咨询产品如何使用"场景的型号级使用指南库。Agent 在回答使用类问题时，
先确认客户所用摄像头**型号（SKU）**，再检索对应型号的指南作答。

## 目录结构

```
Knowledge/                # 仓库根目录，与 APIG 同级
├── build_knowledge.py   # 知识库生成器（单一事实来源 SKUS，可复现）
├── catalog.json         # 型号目录：30 个 SKU 的分类/分辨率/适用场景（供检索与型号消歧）
├── guides/              # 每个型号一份结构化使用指南
│   ├── YT-IPC-4K.md
│   ├── YT-DOME-2K.md
│   └── ...（共 30 份）
└── README.md
```

## 覆盖范围（30 个 SKU）

枪机 / 半球 / 球机(PTZ) / 鱼眼全景 / 家用云台 / 热成像 / 防爆 / 太阳能 4G 等产品线。
其中 `YT-IPC-4K`、`YT-DOME-2K`、`YT-PTZ-4K` 与 `server.py` 现网 6 台设备所用型号一致。

## 如何接入 Agent（数据流）

沿用项目既有的"存量 API → OpenAPI → MCP 工具 → Agent"链路，新增两个只读接口：

- `GET /api/product-guides` → MCP 工具 `list_product_guides`：列出全部型号目录。
- `GET /api/product-guides/{sku}` → MCP 工具 `get_product_guide`：取指定型号的完整指南。

`server.py` 启动时加载本目录；两个接口纳入 `is_protected_business_api`，
与现有业务 API 一样受 `X-API-Key` / 登录会话保护。

`APIG/server.py` 通过 `_resolve_knowledge_dir()` 定位本目录：优先读环境变量
`KNOWLEDGE_DIR`，否则依次尝试仓库根目录（当前位置）和 `APIG/` 内。

> ⚠️ 部署说明：本目录已移出 `APIG/`，位于仓库根目录（与 APIG 同级）。
> APIG 的 Docker 构建上下文只 `COPY` 了 `APIG/` 目录，因此**镜像默认不再包含本目录**。
> 若要部署到 VKE 让线上生效，需在构建时把 `Knowledge/` 一并纳入镜像
> （调整构建上下文或 COPY 路径），或通过挂载 + `KNOWLEDGE_DIR` 指定路径。
> 本地源码运行不受影响。

## 维护方式

**不要手工编辑 `catalog.json` 或 `guides/*.md`**（文件头已注明自动生成）。
新增 / 修改型号：编辑 `build_knowledge.py` 中的 `SKUS` 列表后重跑：

```bash
python3 build_knowledge.py          # 重新生成
python3 build_knowledge.py --check  # 校验产物与 SKUS 是否一致（CI 用）
```

> 说明：本知识库为影腾 demo 的**虚构演示数据**，型号与参数不代表真实产品。
