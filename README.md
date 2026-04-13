# Retarget Debug Page Bundle

这个目录的目标，是把已经生成好的 `retarget_debug_offline.html` 整理成一个可以单独上传到 GitHub 的小仓库结构，方便同事直接打开页面诊断 episode，也方便后续基于同一份数据重新渲染页面。

它解决的是“分享和复用调试页”这个问题，不负责从原始 episode 直接计算重定向结果。也就是说，这个目录位于诊断链路的末端，前面仍然需要有一条能产出 `retarget_debug_offline.html` 的上游流程。

## 目录说明

- `bundle_page.py`
  - 从现有离线 HTML 中抽取页面结构和页面数据，输出一个更适合分享的 bundle。
- `generate_page.py`
  - 根据 bundle 内的 `page_template.html` 和 `data/page_data.json` 重新生成 HTML 页面。
- `current_bundle/`
  - 当前页面导出的示例 bundle，可以直接打开验证。
- `tests/`
  - 核心抽取与再生成逻辑的测试。

## 它具体解决什么问题

原始的 `retarget_debug_offline.html` 是一个“大一统离线页”：

- 前端逻辑在 HTML 里
- Plotly 也被内联在 HTML 里
- 图上的轨迹、摘要、交互状态默认值也都塞在 HTML 里

这样单文件分发虽然简单，但有两个明显问题：

- 文件太大，不利于上传、review 和后续维护
- 数据和页面逻辑耦合在一起，不方便同事替换成自己的 episode 数据

这个 bundle 目录的做法是把页面拆成三层：

1. `page_template.html`
   - 保留页面布局、样式、交互逻辑
   - 用 `PAGE_DATA` 占位注入数据
2. `data/page_data.json`
   - 单独保存页面所需的轨迹、摘要、figure、payload
3. `retarget_debug_offline.html`
   - 由模板和数据重新渲染得到的最终页面

这样做以后，你可以把“页面壳”和“页面数据”分开管理。同事如果只想看你的结果，直接打开最终 HTML 就行；如果想复用页面结构诊断自己的 episode，就替换 `page_data.json` 再渲染一次。

## 具体实现

### 1. `bundle_page.py` 做了什么

`bundle_page.py` 的输入是一份已经可以打开的 `retarget_debug_offline.html`。

它会做几件事：

1. 找到页面里最后一个 `<script>` 块
   - 这个块里保存了页面运行时的大对象，比如 `figures`、`summaries`、`payloads`、`variantLabels`
2. 把这些对象抽出来，写进 `data/page_data.json`
3. 把原始 HTML 里的内联 Plotly 替换成 CDN 引用
4. 把原来直接写死在 HTML 里的数据对象替换成统一入口 `PAGE_DATA`
5. 产出一个更轻的 `page_template.html`
6. 再用模板和 JSON 数据重新生成一份 `retarget_debug_offline.html`

因此，`bundle_page.py` 本质上是一个“离线页解包器 + 轻量重打包器”。

### 2. `generate_page.py` 做了什么

`generate_page.py` 很简单：

- 读入 `page_template.html`
- 读入 `data/page_data.json`
- 把 JSON 数据注入 `PAGE_DATA`
- 输出新的 `retarget_debug_offline.html`

这一步不重新做 retarget，也不重新算 IK。它只负责页面渲染层面的重建。

### 3. 页面数据里包含什么

当前页面数据来自上游已经生成好的调试页，所以 `page_data.json` 里包含的是诊断结果，而不是原始传感器流。主要包括：

- `figures`
  - Plotly 需要的轨迹、图层、布局
- `summaries`
  - 页面右下角/摘要面板里展示的关键信息
- `payloads`
  - 页面交互逻辑要用到的轨迹点、坐标系、目标点等
- `variantLabels`
  - 不同 episode 或不同输入分组在页面中的切换按钮
- `activeVariantKey`
  - 默认打开时选中的数据分组

对于当前这类 UMI replay 调试页，页面通常会包含这些语义层：

- `W0` 固定世界系
- `H0` 初始头显系
- `H0+10` 对照层
- 机器人默认中立骨架
- 左右手重定向目标
- 固定 collar replay 轨迹组

## 与 capstone 的关系

### 先说边界

这个目录**不直接调用** `capstone/umi_robot`，也**不替代** capstone 的 replay 语义。它和 capstone 的关系是：

- `capstone/umi_robot`
  - 提供语义参考和 replay 流程参考
- 上游 replay / retarget 脚本
  - 根据 capstone 语义把 episode 转成可诊断的离线调试页
- `retarget_debug_page_bundle`
  - 把这份调试页整理成可分享、可复用的 bundle

所以，这个目录在整条链路里的位置是最下游。

### 当前采用的 capstone 语义

根据当前项目约定，这条调试链路是按 capstone 的这些语义在对齐：

- `collar` 作为 headset anchor
- replay 流程参考 `warmup -> sync -> playback`
- 当前 humanoid replay 主线使用固定 collar 的 position-only 语义
- `arm_pose_frame = capstone_headset_relative`
- `fixed_collar_replay = true`
- `position_only = true`

这几点非常重要，因为同事如果拿别的 episode 来比对，必须先确认他们的上游 episode 也是按同一套语义转出来的。否则页面虽然能打开，但几何意义就不一致。

### 它如何和 capstone 配合使用

推荐按下面顺序理解：

1. 在上游链路里，先按 capstone 语义处理 episode
   - 用 `collar` 作为 anchor
   - 按 `warmup -> sync -> playback` 的时间组织方式生成 replay
   - 在当前主线中保持 fixed-collar、position-only 语义
2. 上游脚本生成一份调试页
   - 典型产物是 `/tmp/umireplay_retarget_debug/retarget_debug_offline.html`
3. 再用本目录把这份调试页打包出来
   - 抽出模板
   - 抽出页面数据
   - 重建一个更适合分享的 bundle
4. 把 bundle 发给同事
   - 同事直接打开 HTML 看结果
   - 或者替换成自己的 `page_data.json` 做对照

### 一个更实用的理解方式

如果把 capstone 看成“语义规范和 replay 参考”，那这个 bundle 就是“诊断报告封装器”。

也就是说：

- capstone 决定你该怎么看数据
- 上游 retarget / replay 脚本决定你算出什么结果
- 这个 bundle 决定你怎么把结果发给别人看

## 适用场景

- 你已经有一份可打开的 `retarget_debug_offline.html`
- 你希望把它和生成逻辑拆出来，单独传给同事或上传到 GitHub
- 同事希望直接打开页面，观察某个 episode 的轨迹、重定向目标和调试摘要
- 同事也在沿用 capstone 对齐过的 replay 语义，希望横向比较不同 episode

## 生成当前 bundle

在这个目录下运行：

```bash
python3 bundle_page.py \
  --source /tmp/umireplay_retarget_debug/retarget_debug_offline.html \
  --bundle-dir current_bundle
```

执行后会生成：

- `current_bundle/page_template.html`
- `current_bundle/data/page_data.json`
- `current_bundle/retarget_debug_offline.html`

## 重新生成 HTML

如果你修改了 `page_template.html` 或 `data/page_data.json`，可以重新渲染：

```bash
python3 generate_page.py \
  --template current_bundle/page_template.html \
  --data current_bundle/data/page_data.json \
  --output current_bundle/retarget_debug_offline.html
```

## 同事如何使用

同事有两种使用方式：

1. 只看结果
   - 直接打开 `current_bundle/retarget_debug_offline.html`
2. 复用页面结构看自己的结果
   - 保持 `page_template.html` 不变
   - 替换 `data/page_data.json`
   - 运行 `generate_page.py`

更严格一点说，如果同事要做“和你这份页面有意义的横向对比”，需要保证：

- episode 的语义和你的上游链路一致
- 同样按 capstone 的 collar anchor 思路处理
- 同样使用 fixed-collar / position-only 这条 replay 主线

否则页面只是“能显示”，但不一定“可比较”。

## 关于 Plotly

为了让目录更轻量，生成后的模板会把内联 Plotly 替换成 CDN：

```text
https://cdn.plot.ly/plotly-2.35.2.min.js
```

这意味着：

- GitHub 上传体积更小
- 通过 GitHub Pages 打开更方便
- 打开页面时需要能访问公网

如果你后面想做成完全离线包，可以再把 Plotly 改成随仓库一起分发的本地文件。
