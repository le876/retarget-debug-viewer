from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bundle_page import extract_page_components, render_page, write_bundle  # noqa: E402


SAMPLE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>Sample</title>
  <script>window.Plotly = {version: 'inline'};</script>
</head>
<body>
  <div class="wrap">
    <pre id="summaryJson">{"stale": true}</pre>
  </div>
  <script>
    const figures = {"main_default": {"data": [], "layout": {"title": "Demo"}}};
    const summaries = {"main_default": {"episode": "demo"}};
    const payloads = {"main_default": {"datasets": []}};
    const variantLabels = [{"key": "main_default", "label": "Demo"}];
    let activeVariantKey = "main_default";
    let userRotationMatrix = [
      [1, 0, 0],
      [0, 1, 0],
      [0, 0, 1],
    ];
    function updateSummary() {
      const summaryEl = document.getElementById('summaryJson');
      summaryEl.textContent = JSON.stringify(summaries[activeVariantKey], null, 2);
    }
    updateSummary();
  </script>
</body>
</html>
"""


def test_extract_page_components_replaces_inline_plotly_and_clears_summary():
    template_text, page_data = extract_page_components(SAMPLE_HTML)

    assert "https://cdn.plot.ly/plotly-2.35.2.min.js" in template_text
    assert "window.Plotly = {version: 'inline'}" not in template_text
    assert "__PAGE_DATA_JSON__" in template_text
    assert '<pre id="summaryJson"></pre>' in template_text
    assert page_data["activeVariantKey"] == "main_default"
    assert page_data["variantLabels"][0]["label"] == "Demo"
    assert page_data["figures"]["main_default"]["layout"]["title"] == "Demo"


def test_render_page_injects_serialized_page_data():
    template_text, page_data = extract_page_components(SAMPLE_HTML)

    rendered = render_page(template_text, page_data)

    assert "__PAGE_DATA_JSON__" not in rendered
    assert 'const PAGE_DATA = {"activeVariantKey": "main_default"' in rendered
    assert '"episode": "demo"' in rendered
    assert "let activeVariantKey = PAGE_DATA.activeVariantKey;" in rendered


def test_write_bundle_outputs_expected_files(tmp_path: Path):
    source = tmp_path / "source.html"
    source.write_text(SAMPLE_HTML, encoding="utf-8")

    bundle_dir = tmp_path / "bundle"
    write_bundle(source, bundle_dir)

    template_path = bundle_dir / "page_template.html"
    data_path = bundle_dir / "data" / "page_data.json"
    html_path = bundle_dir / "retarget_debug_offline.html"

    assert template_path.exists()
    assert data_path.exists()
    assert html_path.exists()
    assert "Demo" in data_path.read_text(encoding="utf-8")
    assert "PAGE_DATA" in html_path.read_text(encoding="utf-8")
