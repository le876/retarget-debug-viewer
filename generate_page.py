from __future__ import annotations

import argparse
import json
from pathlib import Path

from bundle_page import render_page


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="根据模板与数据重新生成离线调试页。")
    base_dir = Path(__file__).resolve().parent / "current_bundle"
    parser.add_argument(
        "--template",
        type=Path,
        default=base_dir / "page_template.html",
        help="页面模板路径",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=base_dir / "data" / "page_data.json",
        help="页面数据 JSON 路径",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=base_dir / "retarget_debug_offline.html",
        help="输出 HTML 路径",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    template_text = args.template.read_text(encoding="utf-8")
    page_data = json.loads(args.data.read_text(encoding="utf-8"))
    rendered = render_page(template_text, page_data)
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
