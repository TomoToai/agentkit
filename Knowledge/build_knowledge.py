#!/usr/bin/env python3
"""生成影腾摄像头产品使用指南知识库（可复现）。

设计目标：
- 单一事实来源 ``SKUS``：定义 30 个型号（SKU）的产品档案与差异化能力。
- 由脚本渲染出 ``catalog.json``（型号目录，供检索/列表）与 ``guides/<SKU>.md``
  （每个型号一份结构化使用指南）。
- 结构化、模板化生成，避免手工维护 30 份文档产生的口径漂移；新增型号只需
  在 ``SKUS`` 追加一条记录后重跑本脚本。

命令：
    python3 build_knowledge.py            # 生成 catalog.json 和 guides/*.md
    python3 build_knowledge.py --check    # 校验产物与 SKUS 是否一致（CI 用）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

KNOWLEDGE_DIR = Path(__file__).resolve().parent
GUIDES_DIR = KNOWLEDGE_DIR / "guides"
CATALOG_PATH = KNOWLEDGE_DIR / "catalog.json"

# 产品形态的共性说明：按 form_factor 归类，注入到每份指南，保证同系列口径一致。
FORM_FACTORS: dict[str, dict[str, Any]] = {
    "bullet": {
        "label": "枪机（Bullet）",
        "mount": "墙面/立杆横装，随附 L 型支架，建议安装高度 3–5 米。",
        "scene": "园区周界、道路、出入口等需要远距离定向监控的室外场景。",
    },
    "dome": {
        "label": "半球（Dome）",
        "mount": "吸顶或壁装，半球罩防拆卸，适合 2.5–4 米层高。",
        "scene": "大厅、走廊、电梯厅、仓库通道等室内近距离场景。",
    },
    "ptz": {
        "label": "球机（PTZ）",
        "mount": "立杆/墙面吊装，支持水平 360° 连续旋转与光学变倍。",
        "scene": "停车场、广场、港口等需要大范围巡航与变焦追踪的场景。",
    },
    "fisheye": {
        "label": "鱼眼全景（Fisheye）",
        "mount": "吸顶安装，单镜头 180°/360° 全景，无监控死角。",
        "scene": "开放式办公区、零售卖场、会议室的无盲区俯拍。",
    },
    "home": {
        "label": "家用/商用云台机（Home）",
        "mount": "桌面免打孔或壁装，随附 Type-C 供电，配 App 快速配网。",
        "scene": "家庭、小微门店、前台等即插即用的轻量看护场景。",
    },
    "thermal": {
        "label": "热成像（Thermal）",
        "mount": "立杆/墙面横装，双光谱（热成像+可见光）需水平校准。",
        "scene": "森林防火、变电站测温、周界防入侵等需要温度感知的场景。",
    },
    "explosion": {
        "label": "防爆（Explosion-proof）",
        "mount": "不锈钢防爆壳体，需由持证电工按防爆规范接线并可靠接地。",
        "scene": "石化、油库、加油站、粉尘车间等易燃易爆危险区域。",
    },
    "solar": {
        "label": "太阳能 4G（Solar/4G）",
        "mount": "抱杆安装，太阳能板朝正南、倾角约等于当地纬度，插入 4G 流量卡。",
        "scene": "工地、农田、鱼塘、边远无网无电点位的独立布控。",
    },
}

# 30 个 SKU 的单一事实来源。前 3 个型号与 server.py 现网 6 台设备一致，务必保留。
SKUS: list[dict[str, Any]] = [
    # —— 现网在用的 3 个型号（必须与 server.py 对齐）——
    {"sku": "YT-IPC-4K", "name": "星光级 4K 枪机", "form": "bullet", "resolution": "4K (3840×2160)",
     "lens": "2.8–12mm 电动变焦", "features": ["星光级全彩夜视", "智能移动侦测", "IP67 防护", "PoE 供电"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC12V 或 PoE(802.3af)"},
    {"sku": "YT-DOME-2K", "name": "室内半球 2K", "form": "dome", "resolution": "2K (2560×1440)",
     "lens": "2.8mm 定焦", "features": ["红外夜视 30m", "宽动态 WDR", "防拆报警", "内置麦克风"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC12V 或 PoE(802.3af)"},
    {"sku": "YT-PTZ-4K", "name": "室外高速球机 4K", "form": "ptz", "resolution": "4K (3840×2160)",
     "lens": "25 倍光学变焦", "features": ["水平 360° 连续旋转", "自动巡航与预置位", "透雾增强", "IP66 防护"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC24V 或 HiPoE(802.3bt)"},
    # —— 枪机系列 ——
    {"sku": "YT-IPC-2K", "name": "红外 2K 枪机", "form": "bullet", "resolution": "2K (2560×1440)",
     "lens": "4mm 定焦", "features": ["红外夜视 50m", "移动侦测", "IP67 防护", "PoE 供电"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC12V 或 PoE(802.3af)"},
    {"sku": "YT-IPC-8K", "name": "超高清 8K 枪机", "form": "bullet", "resolution": "8K (7680×4320)",
     "lens": "8–32mm 电动变焦", "features": ["8K 超高清", "深度学习人车检测", "IP67 防护", "HiPoE 供电"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC24V 或 HiPoE(802.3bt)"},
    {"sku": "YT-IPC-PRO", "name": "AI 全彩枪机 Pro", "form": "bullet", "resolution": "4K (3840×2160)",
     "lens": "3.6mm 定焦", "features": ["全彩夜视", "周界入侵/绊线检测", "声光警戒", "IP67 防护"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC12V 或 PoE(802.3af)"},
    {"sku": "YT-IPC-LITE", "name": "经济型高清枪机", "form": "bullet", "resolution": "1080P (1920×1080)",
     "lens": "4mm 定焦", "features": ["红外夜视 30m", "移动侦测", "IP66 防护", "PoE 供电"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC12V 或 PoE(802.3af)"},
    {"sku": "YT-IPC-LPR", "name": "车牌识别枪机", "form": "bullet", "resolution": "4K (3840×2160)",
     "lens": "8–32mm 电动变焦", "features": ["车牌识别 LPR", "补光灯联动", "宽动态 WDR", "IP67 防护"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC24V 或 HiPoE(802.3bt)"},
    # —— 半球系列 ——
    {"sku": "YT-DOME-4K", "name": "室内半球 4K", "form": "dome", "resolution": "4K (3840×2160)",
     "lens": "2.8mm 定焦", "features": ["红外夜视 30m", "宽动态 WDR", "防拆报警", "内置拾音"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC12V 或 PoE(802.3af)"},
    {"sku": "YT-DOME-AI", "name": "AI 人形半球", "form": "dome", "resolution": "4K (3840×2160)",
     "lens": "2.8mm 定焦", "features": ["人形侦测", "越界报警", "隐私遮蔽", "内置扬声器"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC12V 或 PoE(802.3af)"},
    {"sku": "YT-DOME-VF", "name": "变焦半球", "form": "dome", "resolution": "2K (2560×1440)",
     "lens": "2.8–12mm 电动变焦", "features": ["电动变焦对焦", "红外夜视 40m", "宽动态 WDR", "防拆报警"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC12V 或 PoE(802.3af)"},
    {"sku": "YT-DOME-MINI", "name": "迷你隐蔽半球", "form": "dome", "resolution": "1080P (1920×1080)",
     "lens": "2.8mm 定焦", "features": ["超小体积", "红外夜视 20m", "内置麦克风", "PoE 供电"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC12V 或 PoE(802.3af)"},
    # —— 球机系列 ——
    {"sku": "YT-PTZ-2K", "name": "室外球机 2K", "form": "ptz", "resolution": "2K (2560×1440)",
     "lens": "20 倍光学变焦", "features": ["水平 360° 旋转", "预置位巡航", "红外夜视 150m", "IP66 防护"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC24V 或 HiPoE(802.3bt)"},
    {"sku": "YT-PTZ-AI", "name": "AI 自动追踪球机", "form": "ptz", "resolution": "4K (3840×2160)",
     "lens": "30 倍光学变焦", "features": ["目标自动追踪", "人车分类", "透雾增强", "IP66 防护"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC24V 或 HiPoE(802.3bt)"},
    {"sku": "YT-PTZ-MINI", "name": "迷你云台球机", "form": "ptz", "resolution": "2K (2560×1440)",
     "lens": "4 倍光学变焦", "features": ["水平 355° 旋转", "红外夜视 50m", "移动追踪", "IP66 防护"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC12V 或 PoE(802.3af)"},
    {"sku": "YT-PTZ-LASER", "name": "激光夜视球机", "form": "ptz", "resolution": "4K (3840×2160)",
     "lens": "40 倍光学变焦", "features": ["激光夜视 500m", "水平 360° 旋转", "透雾增强", "IP66 防护"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC24V 或 HiPoE(802.3bt)"},
    # —— 鱼眼全景 ——
    {"sku": "YT-FISH-6M", "name": "600 万鱼眼全景", "form": "fisheye", "resolution": "6MP (3072×2048)",
     "lens": "1.29mm 全景", "features": ["360° 全景", "多种畸变校正", "红外夜视 15m", "内置拾音"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC12V 或 PoE(802.3af)"},
    {"sku": "YT-FISH-12M", "name": "1200 万鱼眼全景", "form": "fisheye", "resolution": "12MP (4000×3000)",
     "lens": "1.29mm 全景", "features": ["360° 全景", "热力图统计", "客流统计", "PoE 供电"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC12V 或 PoE(802.3af)"},
    {"sku": "YT-PANO-180", "name": "180° 双目全景机", "form": "fisheye", "resolution": "8MP (双目 2×4MP)",
     "lens": "双目拼接", "features": ["180° 无缝拼接", "人形侦测", "宽动态 WDR", "IP66 防护"],
     "app": "影腾运维台 / 影腾眼 App", "power": "DC12V 或 PoE(802.3af)"},
    # —— 家用/商用 ——
    {"sku": "YT-HOME-2K", "name": "家用云台机 2K", "form": "home", "resolution": "2K (2560×1440)",
     "lens": "4mm 定焦", "features": ["水平 355° 云台", "双向语音对讲", "移动追踪", "Wi-Fi 6 连接"],
     "app": "影腾眼 App", "power": "Type-C DC5V"},
    {"sku": "YT-HOME-3K", "name": "家用云台机 3K", "form": "home", "resolution": "3K (2880×1620)",
     "lens": "4mm 定焦", "features": ["全彩夜视", "AI 哭声侦测", "隐私模式", "Wi-Fi 6 连接"],
     "app": "影腾眼 App", "power": "Type-C DC5V"},
    {"sku": "YT-HOME-BAT", "name": "低功耗电池机", "form": "home", "resolution": "2K (2560×1440)",
     "lens": "2.8mm 定焦", "features": ["内置大容量电池", "PIR 人体感应唤醒", "磁吸底座", "Wi-Fi 连接"],
     "app": "影腾眼 App", "power": "内置锂电池 / Type-C 充电"},
    {"sku": "YT-DOORBELL", "name": "智能可视门铃", "form": "home", "resolution": "2K (1600×1200)",
     "lens": "广角 162°", "features": ["按铃即推送", "双向对讲", "PIR 人体感应", "低功耗电池"],
     "app": "影腾眼 App", "power": "内置锂电池 / 门铃线供电"},
    # —— 热成像 ——
    {"sku": "YT-THERMAL-B", "name": "双光谱测温枪机", "form": "thermal", "resolution": "可见光 4K + 热成像 384×288",
     "lens": "可见光 8mm + 热成像 9.7mm", "features": ["精准测温 ±0.5℃", "火点检测", "双光谱融合", "IP66 防护"],
     "app": "影腾运维台", "power": "DC24V 或 HiPoE(802.3bt)"},
    {"sku": "YT-THERMAL-P", "name": "热成像云台机", "form": "thermal", "resolution": "可见光 2K + 热成像 640×512",
     "lens": "可见光 25 倍变焦 + 热成像 定焦", "features": ["森林防火巡检", "水平 360° 旋转", "温度报警", "IP66 防护"],
     "app": "影腾运维台", "power": "DC24V 或 HiPoE(802.3bt)"},
    # —— 防爆 ——
    {"sku": "YT-EX-BULLET", "name": "防爆枪机", "form": "explosion", "resolution": "4K (3840×2160)",
     "lens": "4mm 定焦", "features": ["Ex d IIC T6 防爆认证", "316L 不锈钢壳体", "红外夜视 50m", "IP68 防护"],
     "app": "影腾运维台", "power": "DC24V（防爆接线）"},
    {"sku": "YT-EX-PTZ", "name": "防爆球机", "form": "explosion", "resolution": "4K (3840×2160)",
     "lens": "30 倍光学变焦", "features": ["Ex d IIC T6 防爆认证", "不锈钢云台", "雨刷除污", "IP68 防护"],
     "app": "影腾运维台", "power": "DC24V（防爆接线）"},
    # —— 太阳能 4G ——
    {"sku": "YT-SOLAR-4G", "name": "太阳能 4G 球机", "form": "solar", "resolution": "2K (2560×1440)",
     "lens": "4 倍光学变焦", "features": ["太阳能供电", "4G 全网通", "PIR 唤醒录制", "IP66 防护"],
     "app": "影腾眼 App", "power": "太阳能板 + 内置锂电池"},
    {"sku": "YT-SOLAR-BULLET", "name": "太阳能 4G 枪机", "form": "solar", "resolution": "2K (2560×1440)",
     "lens": "4mm 定焦", "features": ["太阳能供电", "4G 全网通", "全彩夜视", "IP66 防护"],
     "app": "影腾眼 App", "power": "太阳能板 + 内置锂电池"},
    {"sku": "YT-4G-MINI", "name": "4G 便携布控球", "form": "solar", "resolution": "2K (2560×1440)",
     "lens": "4mm 定焦", "features": ["免布线 4G 传输", "磁吸/三脚架", "内置电池", "IP66 防护"],
     "app": "影腾眼 App", "power": "内置锂电池 / Type-C 充电"},
]


def form_meta(sku: dict[str, Any]) -> dict[str, Any]:
    return FORM_FACTORS[sku["form"]]


def build_catalog() -> dict[str, Any]:
    """生成型号目录：供 list 工具与 Agent 做型号消歧使用。"""
    items = []
    for sku in SKUS:
        meta = form_meta(sku)
        items.append({
            "sku": sku["sku"],
            "name": sku["name"],
            "category": meta["label"],
            "resolution": sku["resolution"],
            "scene": meta["scene"],
            "guide": f"guides/{sku['sku']}.md",
        })
    return {
        "product_line": "影腾（YingTeng）监控摄像头",
        "total": len(items),
        "note": "本目录为演示知识库，型号与参数为影腾 demo 虚构数据，仅用于产品使用指南检索。",
        "items": items,
    }


def render_guide(sku: dict[str, Any]) -> str:
    """按统一模板渲染单个型号的使用指南 Markdown。"""
    meta = form_meta(sku)
    features = "\n".join(f"- {f}" for f in sku["features"])
    return f"""# {sku['sku']} · {sku['name']} 使用指南

> 产品形态：{meta['label']}　|　分辨率：{sku['resolution']}　|　镜头：{sku['lens']}
> 适用 App：{sku['app']}　|　供电方式：{sku['power']}

## 一、产品简介

{sku['name']}（型号 **{sku['sku']}**）属于影腾 {meta['label']} 产品线，
主要面向{meta['scene']}

**核心能力**

{features}

## 二、开箱与安装

1. 核对配件：摄像头主机 ×1、安装支架 ×1、防水配件包 ×1、快速指南 ×1。
2. 选点定位：{meta['mount']}
3. 固定机身：用随附膨胀螺丝固定支架，装好后调整镜头朝向并锁紧云台/万向节。
4. 连接线缆：按"供电方式（{sku['power']}）"接通电源；网络型号用网线接入交换机或 NVR 的 PoE 口。

## 三、首次配网与激活

1. 手机安装 **{sku['app']}**，注册并登录账号。
2. 设备上电后等待指示灯进入待配网状态（蓝灯慢闪）。
3. 在 App 点击"添加设备"，扫描机身二维码或局域网自动搜索。
4. 按提示设置设备密码（首次激活必须设置强密码），完成时间校准与固件检查。
5. 激活成功后，可在"影腾运维台"中按型号 **{sku['sku']}** 纳管，统一查看在线状态与告警。

## 四、日常使用

- **实时预览**：App 首页选择该设备即可查看实时画面；支持画质切换（高清/流畅）。
- **录像回放**：插入 microSD 卡或绑定 NVR / 云存储后，按时间轴回放历史录像。
- **告警推送**：开启移动侦测 / AI 事件后，触发时通过 App 推送并在运维台生成告警。
- **参数调节**：在设置中可调整分辨率、码率、夜视模式、OSD 水印与隐私遮蔽区域。

## 五、常见问题（FAQ）

| 现象 | 可能原因 | 处理建议 |
| --- | --- | --- |
| 设备离线 | 供电中断 / 网络不通 | 检查{sku['power']}供电与网线，重启设备后在 App 重新连接 |
| 画面模糊 | 镜头脏污 / 未对焦 | 清洁镜头，电动变焦型号在 App 重新执行一键对焦 |
| 夜视发黑 | 夜视模式异常 | 确认红外/全彩夜视开关，检查是否有遮挡或强反光 |
| 录像缺失 | 存储异常 | 检查 microSD 卡或 NVR/云存储容量与读写状态 |

## 六、维护与保养

- 每季度清洁一次镜头与防护罩，室外型号雨季后检查密封圈。
- 定期在 App / 运维台检查固件版本，及时升级以获得安全与功能更新。
- 出现持续告警或无法自愈的故障时，联系影腾客服并提供型号 **{sku['sku']}** 与设备编号。

---
*本指南由 build_knowledge.py 依据 catalog 数据自动生成，请勿手工编辑；如需修改，请更新 SKUS 后重跑脚本。*
"""


def generate() -> None:
    GUIDES_DIR.mkdir(parents=True, exist_ok=True)
    catalog = build_catalog()
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for sku in SKUS:
        (GUIDES_DIR / f"{sku['sku']}.md").write_text(render_guide(sku), encoding="utf-8")
    print(f"已生成 catalog.json 和 {len(SKUS)} 份型号指南到 {GUIDES_DIR}")


def check() -> int:
    if not CATALOG_PATH.exists():
        print("校验失败：catalog.json 不存在，请先运行生成。", file=sys.stderr)
        return 1
    expected = json.dumps(build_catalog(), ensure_ascii=False, indent=2) + "\n"
    if CATALOG_PATH.read_text(encoding="utf-8") != expected:
        print("校验失败：catalog.json 与 SKUS 不一致，请重跑生成。", file=sys.stderr)
        return 1
    for sku in SKUS:
        path = GUIDES_DIR / f"{sku['sku']}.md"
        if not path.exists() or path.read_text(encoding="utf-8") != render_guide(sku):
            print(f"校验失败：{path.name} 与 SKUS 不一致，请重跑生成。", file=sys.stderr)
            return 1
    print(f"校验通过：catalog.json 和 {len(SKUS)} 份型号指南均为最新。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="生成影腾摄像头产品使用指南知识库")
    parser.add_argument("--check", action="store_true", help="仅校验产物是否与 SKUS 一致")
    args = parser.parse_args()
    if args.check:
        return check()
    generate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
