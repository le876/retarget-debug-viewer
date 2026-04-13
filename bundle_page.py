from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


PLOTLY_CDN_URL = "https://cdn.plot.ly/plotly-2.35.2.min.js"
PAGE_DATA_PLACEHOLDER = "__PAGE_DATA_JSON__"


def _find_script_block(html_text: str, *, first: bool) -> tuple[int, int]:
    finder = html_text.find if first else html_text.rfind
    start = finder("<script>")
    if start < 0:
        raise ValueError("未找到 <script> 标签")
    end = html_text.find("</script>", start)
    if end < 0:
        raise ValueError("未找到 </script> 标签")
    return start, end + len("</script>")


def _find_assignment(script_text: str, name: str) -> tuple[str, int, int]:
    match = re.search(rf"\b(?:const|let)\s+{re.escape(name)}\s*=\s*", script_text)
    if not match:
        raise ValueError(f"未找到变量赋值: {name}")
    raw_value = script_text[match.end():]
    leading_ws = len(raw_value) - len(raw_value.lstrip())
    decoder = json.JSONDecoder()
    _, consumed = decoder.raw_decode(raw_value.lstrip())
    value_start = match.end() + leading_ws
    value_end = value_start + consumed
    if value_end >= len(script_text) or script_text[value_end] != ";":
        raise ValueError(f"变量 {name} 缺少结尾分号")
    return script_text[value_start:value_end].strip(), match.start(), value_end + 1


def _clear_summary_block(html_text: str) -> str:
    pattern = r'(<pre id="summaryJson">)(.*?)(</pre>)'
    return re.sub(pattern, r"\1\3", html_text, count=1, flags=re.DOTALL)


def _replace_plotly_with_cdn(prefix_html: str) -> str:
    plotly_start, plotly_end = _find_script_block(prefix_html, first=True)
    return (
        prefix_html[:plotly_start]
        + f'  <script src="{PLOTLY_CDN_URL}"></script>\n'
        + prefix_html[plotly_end:]
    )


def extract_page_components(html_text: str) -> tuple[str, dict[str, Any]]:
    final_script_start, final_script_end = _find_script_block(html_text, first=False)
    prefix_html = html_text[:final_script_start]
    suffix_html = html_text[final_script_end:]
    script_text = html_text[final_script_start + len("<script>"): html_text.find("</script>", final_script_start)]

    figures_literal, _, _ = _find_assignment(script_text, "figures")
    summaries_literal, _, _ = _find_assignment(script_text, "summaries")
    payloads_literal, _, _ = _find_assignment(script_text, "payloads")
    variant_labels_literal, _, _ = _find_assignment(script_text, "variantLabels")
    active_variant_literal, _, active_variant_end = _find_assignment(script_text, "activeVariantKey")

    page_data = {
        "activeVariantKey": json.loads(active_variant_literal),
        "variantLabels": json.loads(variant_labels_literal),
        "figures": json.loads(figures_literal),
        "summaries": json.loads(summaries_literal),
        "payloads": json.loads(payloads_literal),
    }

    runtime_js = script_text[active_variant_end:].strip()
    normalized_prefix = _clear_summary_block(_replace_plotly_with_cdn(prefix_html))
    render_script = (
        "  <script>\n"
        f"    const PAGE_DATA = {PAGE_DATA_PLACEHOLDER};\n"
        "    const figures = PAGE_DATA.figures;\n"
        "    const summaries = PAGE_DATA.summaries;\n"
        "    const payloads = PAGE_DATA.payloads;\n"
        "    const variantLabels = PAGE_DATA.variantLabels;\n"
        "    let activeVariantKey = PAGE_DATA.activeVariantKey;\n"
        f"{runtime_js}\n"
        "  </script>\n"
    )
    template_text = normalized_prefix + render_script + suffix_html
    return template_text, page_data


def render_page(template_text: str, page_data: dict[str, Any]) -> str:
    serialized = json.dumps(page_data, ensure_ascii=False)
    return template_text.replace(PAGE_DATA_PLACEHOLDER, serialized, 1)


def write_bundle(source_html_path: Path, bundle_dir: Path) -> Path:
    html_text = source_html_path.read_text(encoding="utf-8")
    template_text, page_data = extract_page_components(html_text)

    bundle_dir.mkdir(parents=True, exist_ok=True)
    data_dir = bundle_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    template_path = bundle_dir / "page_template.html"
    data_path = data_dir / "page_data.json"
    output_html_path = bundle_dir / "retarget_debug_offline.html"

    template_path.write_text(template_text, encoding="utf-8")
    data_path.write_text(json.dumps(page_data, ensure_ascii=False, indent=2), encoding="utf-8")
    output_html_path.write_text(render_page(template_text, page_data), encoding="utf-8")
    return output_html_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="从现有离线调试页提取可分享 bundle。")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("/tmp/umireplay_retarget_debug/retarget_debug_offline.html"),
        help="现有离线 HTML 页面路径",
    )
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "current_bundle",
        help="输出 bundle 目录",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    output_path = write_bundle(args.source, args.bundle_dir)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
