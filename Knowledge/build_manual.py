#!/usr/bin/env python3
"""把 Knowledge/ 下的 30 份型号使用指南合订成一本手册。

单一事实来源：``catalog.json`` + ``guides/*.md``（均由 build_knowledge.py 生成）。
本脚本只做「合订与排版」：读取目录 → 按产品分类分章 → 生成一份完整 HTML，
再由外部工具导出 Word / PDF：

    python3 build_manual.py                # 生成 dist/影腾摄像头产品使用指南手册.html
    # Word（系统自带 textutil）:
    textutil -convert docx -output "dist/影腾摄像头产品使用指南手册.docx" \
        "dist/影腾摄像头产品使用指南手册.html"
    # PDF（Chrome 无头）:
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
        --headless --disable-gpu --no-pdf-header-footer \
        --print-to-pdf="dist/影腾摄像头产品使用指南手册.pdf" \
        "file://.../dist/影腾摄像头产品使用指南手册.html"

HTML 是 Word 与 PDF 的共同事实来源，保证两份产物内容一致、可复现。
"""
from __future__ import annotations

import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "catalog.json"
DIST = ROOT / "dist"
MANUAL_TITLE = "影腾摄像头产品使用指南手册"


# --------------------------- 轻量 Markdown → HTML ---------------------------
def _inline(text: str) -> str:
    """处理行内语法：转义 → 加粗。指南正文不含链接/行内代码。"""
    text = html.escape(text, quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def md_to_html(md: str) -> str:
    """把单份指南 Markdown 转成 HTML 片段，仅覆盖指南实际使用的语法。"""
    lines = md.splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # 分隔线
        if stripped == "---":
            out.append("<hr/>")
            i += 1
            continue

        # 标题（跳过每份指南的一级标题，改由章节统一渲染）
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # 引用块（连续 > 行合并为一段，内部换行保留）
        if stripped.startswith(">"):
            quote: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(_inline(lines[i].strip()[1:].strip()))
                i += 1
            out.append('<blockquote>' + "<br/>".join(quote) + "</blockquote>")
            continue

        # 表格（表头行 + 分隔行 + 数据行）
        if stripped.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|?$", lines[i + 1].strip()):
            header = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2  # 跳过表头与分隔行
            rows: list[list[str]] = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            thead = "".join(f"<th>{_inline(c)}</th>" for c in header)
            tbody = "".join(
                "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in row) + "</tr>" for row in rows
            )
            out.append(f"<table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>")
            continue

        # 有序列表
        if re.match(r"^\d+\.\s+", stripped):
            items: list[str] = []
            while i < n and re.match(r"^\d+\.\s+", lines[i].strip()):
                items.append(f"<li>{_inline(re.sub(r'^\\d+\\.\\s+', '', lines[i].strip()))}</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue

        # 无序列表
        if stripped.startswith("- "):
            items = []
            while i < n and lines[i].strip().startswith("- "):
                items.append(f"<li>{_inline(lines[i].strip()[2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue

        # 普通段落
        out.append(f"<p>{_inline(stripped)}</p>")
        i += 1

    return "\n".join(out)


# --------------------------- 手册组装 ---------------------------
CSS = """
:root { --ink:#1f2328; --muted:#57606a; --line:#d0d7de; --brand:#0b6bcb; --soft:#f3f6fb; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
       color: var(--ink); line-height: 1.7; margin: 0; }
.page { padding: 0 8mm; }
/* 封面 */
.cover { text-align:center; padding: 70mm 0 40mm; page-break-after: always; }
.cover .kicker { color: var(--brand); letter-spacing: 6px; font-size: 14px; }
.cover h1 { font-size: 34px; margin: 18px 0 10px; }
.cover .sub { color: var(--muted); font-size: 15px; }
.cover .meta { margin-top: 40mm; color: var(--muted); font-size: 13px; }
/* 目录 */
.toc { page-break-after: always; }
.toc h2 { border-bottom: 2px solid var(--brand); padding-bottom: 8px; }
.toc ol { list-style: none; padding-left: 0; }
.toc .cat { font-weight: 700; margin-top: 14px; color: var(--brand); }
.toc .sku { margin-left: 16px; color: var(--ink); }
.toc .sku code { color: var(--muted); }
/* 章节 */
.category { page-break-before: always; }
.category > h2 { font-size: 24px; border-left: 6px solid var(--brand); padding-left: 12px; }
.guide { page-break-before: always; padding-top: 4px; }
.guide h1 { font-size: 21px; border-bottom: 1px solid var(--line); padding-bottom: 8px; }
h2 { font-size: 17px; margin-top: 22px; }
h3 { font-size: 15px; }
blockquote { background: var(--soft); border-left: 4px solid var(--brand);
             margin: 12px 0; padding: 10px 14px; color: var(--muted); font-size: 13.5px; border-radius: 4px; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 13.5px; }
th, td { border: 1px solid var(--line); padding: 7px 10px; text-align: left; vertical-align: top; }
th { background: var(--soft); }
ul, ol { padding-left: 22px; }
li { margin: 3px 0; }
hr { border: none; border-top: 1px dashed var(--line); margin: 18px 0; }
code { font-family: "SF Mono", Menlo, Consolas, monospace; }
"""


def build_manual_html(catalog: dict) -> str:
    items = catalog.get("items", [])
    # 按分类聚合并保持 catalog 中出现的先后顺序
    categories: dict[str, list[dict]] = {}
    for it in items:
        categories.setdefault(it.get("category", "其他"), []).append(it)

    # 目录
    toc_rows: list[str] = []
    for cat, group in categories.items():
        toc_rows.append(f'<li class="cat">{html.escape(cat)}</li>')
        for it in group:
            toc_rows.append(
                f'<li class="sku">{html.escape(it["name"])} '
                f'<code>{html.escape(it["sku"])}</code></li>'
            )
    toc = "<ol>" + "".join(toc_rows) + "</ol>"

    # 正文章节
    sections: list[str] = []
    for cat, group in categories.items():
        section = [f'<section class="category"><h2>{html.escape(cat)}</h2>']
        for it in group:
            guide_md = (ROOT / it["guide"]).read_text(encoding="utf-8")
            section.append(f'<article class="guide">{md_to_html(guide_md)}</article>')
        section.append("</section>")
        sections.append("".join(section))

    today = date.today().isoformat()
    total = catalog.get("total", len(items))
    product_line = catalog.get("product_line", "影腾监控摄像头")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<title>{html.escape(MANUAL_TITLE)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="page">
  <div class="cover">
    <div class="kicker">YINGTENG · PRODUCT MANUAL</div>
    <h1>{html.escape(MANUAL_TITLE)}</h1>
    <div class="sub">{html.escape(product_line)}　·　全系 {total} 款型号使用指南合订本</div>
    <div class="meta">
      文档版本 v1.0　|　生成日期 {today}<br/>
      本手册由 build_manual.py 依据 catalog.json 自动合订，请勿手工编辑。
    </div>
  </div>

  <nav class="toc">
    <h2>目录</h2>
    {toc}
  </nav>

  {''.join(sections)}
</div>
</body>
</html>"""


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    DIST.mkdir(exist_ok=True)
    html_path = DIST / f"{MANUAL_TITLE}.html"
    html_path.write_text(build_manual_html(catalog), encoding="utf-8")
    print(f"已生成 {html_path}（合订 {catalog.get('total')} 个型号）")


if __name__ == "__main__":
    main()
