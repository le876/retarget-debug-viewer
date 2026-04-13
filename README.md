# Retarget Debug Page Bundle

This repository packages an already-generated `retarget_debug_offline.html` into a small, shareable structure that can be uploaded to GitHub. The goal is to let teammates open the page directly to inspect episode behavior, and to make it possible to re-render the same viewer from a separated template and data file.

This repository solves the "share and reuse the debug page" problem. It does not compute retargeting results directly from raw episode data. In other words, this repository sits at the end of the diagnostic pipeline. An upstream process must already exist to generate `retarget_debug_offline.html`.

## Repository Layout

- `bundle_page.py`
  - Extracts page structure and page data from an existing offline HTML page and writes out a shareable bundle.
- `generate_page.py`
  - Regenerates the HTML page from `page_template.html` and `data/page_data.json`.
- `current_bundle/`
  - A sample bundle exported from the current page. It can be opened directly for verification.
- `tests/`
  - Regression tests for the extraction and regeneration logic.

## What Problem This Solves

The original `retarget_debug_offline.html` is a single self-contained offline page:

- Frontend logic is embedded directly in the HTML
- Plotly is inlined into the HTML
- Trajectories, summaries, and default interaction state are also embedded in the HTML

That single-file format is convenient for quick sharing, but it has two clear drawbacks:

- The file is too large for comfortable upload, review, and maintenance
- Page logic and episode data are tightly coupled, so teammates cannot easily swap in their own episode data

This repository splits the page into three layers:

1. `page_template.html`
   - Keeps the page layout, styles, and interaction logic
   - Uses `PAGE_DATA` as the injected data entry point
2. `data/page_data.json`
   - Stores trajectories, summaries, figures, and payloads separately
3. `retarget_debug_offline.html`
   - The final page regenerated from the template and the data

After this split, the page shell and the episode data can be managed independently. If a teammate only wants to inspect your result, they can open the final HTML directly. If they want to reuse the viewer for their own episode, they can replace `page_data.json` and re-render the page.

## Implementation Details

### 1. What `bundle_page.py` Does

`bundle_page.py` takes an already-working `retarget_debug_offline.html` as input.

It performs the following steps:

1. Finds the last `<script>` block in the page
   - This block contains the main runtime objects such as `figures`, `summaries`, `payloads`, and `variantLabels`
2. Extracts those objects into `data/page_data.json`
3. Replaces the original inline Plotly bundle with a CDN reference
4. Replaces hardcoded page data objects with a unified `PAGE_DATA` entry point
5. Produces a lighter `page_template.html`
6. Regenerates a new `retarget_debug_offline.html` from the template and the JSON data

So `bundle_page.py` is effectively an "offline page unpacker plus lightweight repackager".

### 2. What `generate_page.py` Does

`generate_page.py` is intentionally simple:

- Read `page_template.html`
- Read `data/page_data.json`
- Inject the JSON payload into `PAGE_DATA`
- Write a new `retarget_debug_offline.html`

This step does not recompute retargeting, and it does not rerun IK. It only rebuilds the page at the rendering layer.

### 3. What Is Stored in the Page Data

Because the current page data comes from an upstream debug page that has already been generated, `page_data.json` contains diagnostic results rather than raw sensor streams. It mainly includes:

- `figures`
  - Plotly traces, layers, and layouts
- `summaries`
  - Key summary fields shown in the page panels
- `payloads`
  - Trajectory points, coordinate frames, target points, and related data used by frontend interactions
- `variantLabels`
  - Labels for switching between episode groups or input variants
- `activeVariantKey`
  - The default active variant when the page loads

For the current UMI replay debug page, the page typically includes these semantic layers:

- `W0` fixed world frame
- `H0` initial headset frame
- `H0+10` comparison layer
- Default neutral robot skeleton
- Left and right retarget targets
- Fixed-collar replay trajectory group

## Relationship to Capstone

### First, the Boundary

This repository does **not** call `capstone/umi_robot` directly, and it does **not** replace Capstone replay semantics. Its relationship to Capstone is:

- `capstone/umi_robot`
  - Provides semantic reference and replay flow reference
- Upstream replay / retarget scripts
  - Convert an episode into a diagnosable offline debug page using Capstone semantics
- `retarget_debug_page_bundle`
  - Turns that debug page into a reusable and shareable bundle

So this repository belongs to the final stage of the full pipeline.

### Capstone Semantics Assumed by the Current Workflow

Based on the current project setup, the diagnostic chain is aligned to the following Capstone semantics:

- `collar` is treated as the headset anchor
- Replay flow follows `warmup -> sync -> playback`
- The current humanoid replay mainline uses fixed-collar, position-only semantics
- `arm_pose_frame = capstone_headset_relative`
- `fixed_collar_replay = true`
- `position_only = true`

These assumptions matter. If teammates want to compare their own episodes against this page, they must first make sure their upstream episode conversion uses the same semantics. Otherwise the page may still render, but the geometry will not be comparable.

### How This Repository Works with Capstone

The recommended way to think about the flow is:

1. Process the episode upstream using Capstone semantics
   - Use `collar` as the anchor
   - Organize replay around `warmup -> sync -> playback`
   - Keep the current fixed-collar, position-only replay semantics
2. Let the upstream scripts generate a debug page
   - A typical output is `/tmp/umireplay_retarget_debug/retarget_debug_offline.html`
3. Use this repository to package that debug page
   - Extract the template
   - Extract the page data
   - Rebuild a lighter, shareable bundle
4. Share the bundle with teammates
   - They can open the HTML directly to inspect the result
   - Or they can replace `page_data.json` with their own data for side-by-side style reuse

### A More Practical Interpretation

If Capstone is treated as the semantic standard and replay reference, then this bundle is the delivery format for the diagnostic report.

In that sense:

- Capstone decides how the data should be interpreted
- Upstream retarget / replay scripts decide what results get computed
- This bundle decides how those results get shared and viewed

## Typical Use Cases

- You already have a working `retarget_debug_offline.html`
- You want to split its logic and data so the page can be uploaded or shared more cleanly
- Teammates want to open the page and inspect trajectories, retarget targets, and debug summaries
- Teammates are also using a Capstone-aligned replay pipeline and want to compare different episodes consistently

## Generate the Current Bundle

Run this in the repository:

```bash
python3 bundle_page.py \
  --source /tmp/umireplay_retarget_debug/retarget_debug_offline.html \
  --bundle-dir current_bundle
```

This generates:

- `current_bundle/page_template.html`
- `current_bundle/data/page_data.json`
- `current_bundle/retarget_debug_offline.html`

## Regenerate the HTML

If you modify `page_template.html` or `data/page_data.json`, you can re-render the page with:

```bash
python3 generate_page.py \
  --template current_bundle/page_template.html \
  --data current_bundle/data/page_data.json \
  --output current_bundle/retarget_debug_offline.html
```

## How Teammates Can Use It

There are two main usage patterns:

1. Inspect your result directly
   - Open `current_bundle/retarget_debug_offline.html`
2. Reuse the page shell for another episode
   - Keep `page_template.html` unchanged
   - Replace `data/page_data.json`
   - Run `generate_page.py`

For meaningful cross-episode comparison, teammates should ensure that:

- Their episode was processed with the same upstream semantic assumptions
- They also follow the Capstone collar-anchor interpretation
- They also use the fixed-collar, position-only replay mainline

Otherwise the page may still render correctly, but the result is not guaranteed to be comparable.

## Plotly

To keep the repository lighter, the generated template replaces the inline Plotly bundle with a CDN reference:

```text
https://cdn.plot.ly/plotly-2.35.2.min.js
```

That means:

- Smaller repository size
- Easier use with GitHub Pages
- The page requires public network access to load Plotly

If a fully offline distribution is required later, Plotly can be bundled locally instead of using the CDN.
