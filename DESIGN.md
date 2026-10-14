# CoinFT 演示界面设计

## Source of truth
- Status: Active
- Last refreshed: 2026-09-26
- Primary product surfaces: 本机浏览器中的单传感器实时演示页。
- Evidence reviewed: `PROJECT_LOG.md`、`coinft_acceptance.py`、`calibration/coinft_calib.json`、`docs/superpowers/specs/2026-09-25-coinft-normal-bidirectional-shear-demo-design.md`、Stanford `visualization/visualize_coinfts.py`。

## Brand
- Personality: 精密、克制、清晰的实验室仪器。
- Trust signals: 明示数据源、连接状态、采样率、是否回放、是否标定。
- Avoid: 将相对趋势写成实际 N/N·m，或把回放伪装成实时。

## Product goals
- Goals: 访客一眼看到中心正压凹陷、一轴双向剪切侧移、六维未标定趋势与 12 路原始响应。
- Non-goals: 测量准确力值、定位接触点、识别第二个剪切轴、重新标定六轴矩阵或修改传感器调参。
- Success signals: Windows 浏览器打开后能连接 COM10；空载去基线；中心正压凹陷；已验证的相反推向出现相反侧移；断线有明确提示。

## Personas and jobs
- Primary personas: 演示操作者、现场访客。
- User jobs: 操作者启动并确认数据源；访客从大屏理解响应方向和强弱。
- Key contexts of use: 单台 Windows 电脑、单个 CoinFT、Teensy 串口桥接。

## Information architecture
- Primary navigation: 单页。
- Core routes/screens: `/` 仪表盘。
- Content hierarchy: 连接与真实性状态 → 中央六维活动图 → 六路趋势卡 → 12 路原始通道。

## Design principles
- Principle 1: 可演示性与可核对性同等重要。
- Principle 2: 视觉敏感度只改变画面，不改变原始数据。
- Tradeoffs: 用既有旧板矩阵提供方向趋势，同时明确它不适用于当前板的物理计量。

## Visual language
- Color: 深海军蓝背景、青蓝力通道、琥珀色力矩通道、低饱和辅助线。
- Typography: 系统中文字体与等宽数字。
- Spacing/layout rhythm: 宽屏中央主图，两侧六维卡，底部原始通道。
- Shape/radius/elevation: 圆角仪器卡、细边框、轻微光晕。
- Motion: 20 Hz 以内平滑更新；正压使中心凹陷。操作者选择 A 型剪切显示：中部随推向拖动、外围渐弱，网格连续弯曲而非整块平面倾斜；正压与剪切可以叠加，无数据时回平。视觉选择不代替方向验收；已批准实现约定见 `docs/superpowers/specs/2026-09-26-coinft-local-shear-drag-design.md`。
- Imagery/iconography: CSS/SVG 几何图形，不使用第三方素材。

## Components
- Existing components to reuse: Teensy 26 字节帧格式和本地历史矩阵。
- New/changed components: 浏览器网格的正压/剪切示意，以及本地实测的单轴剪切方向配置；串口桥接与回放路径不变。
- Variants and states: 实时、回放、去基线、断线。
- Token/component ownership: 页面样式独立于采集程序。

## Accessibility
- Target standard: 文本状态与颜色并用，常规键盘可操作。
- Keyboard/focus behavior: 按钮可 Tab 与 Enter 操作，焦点可见。
- Contrast/readability: 深色背景上的高对比度标签与大号数值。
- Screen-reader semantics: 状态区使用文字与 ARIA live。
- Reduced motion and sensory considerations: 尊重 `prefers-reduced-motion`。

## Responsive behavior
- Supported breakpoints/devices: 演示电脑 1366 px 以上优先，窄屏按单列排列。
- Layout adaptations: 主图与通道卡堆叠，避免横向滚动。
- Touch/hover differences: 控件无需悬停才能操作。

## Interaction states
- Loading: 显示正在连接/去基线。
- Empty: 网格保持平面，不显示模拟成真实的读数。
- Error: 明确显示串口占用/未连接与重试状态。
- Success: 显示实时采样率和最近一帧时间。
- Disabled: 无数据时去基线按钮不可用；剪切方向未通过当前总成复测时不启用侧移动画。
- Offline/slow network: 页面与服务完全本地化，无外网依赖。

## Content voice
- Tone: 简短、专业。
- Terminology: “相对趋势”“原始计数”“回放”“实时”。
- Microcopy rules: 不出现 N/N·m；不要把方向趋势称为定量力值。

## Implementation constraints
- Framework/styling system: Python 标准库 HTTP 服务 + pyserial，原生 HTML/CSS/JS。
- Design-token constraints: 页面 CSS 变量集中管理。
- Performance constraints: 串口约 200 Hz 输入，前端约 20 Hz 更新。
- Compatibility constraints: Windows 本机、Chrome/Edge。
- Test/screenshot expectations: 单元测试检验帧解析与去基线；历史 CSV 回放和浏览器截图验收。

## Open questions
- [ ] 当前总成的一轴正/反剪切模板与屏幕左右方向仍待实测复核；未通过前不能启用方向动画。
