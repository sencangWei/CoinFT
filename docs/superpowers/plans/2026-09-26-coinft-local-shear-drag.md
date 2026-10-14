# CoinFT Local Shear Drag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将操作者批准的 A 型局部侧向拖弯接入现有实时网格，保持其他数据和UI不变。

**Architecture:** 仅改变 draw 内材料平面非均匀位移与局部高度/颜色。沿用现有两强度、平滑和故障门禁；用隔离Canvas几何测试与离线dashboard截图验证，root负责最终实机页面显示。

**Tech Stack:** 原生JS Canvas，Python unittest，Playwright Chromium，现有标准库HTTP服务。

## Global Constraints
- 采用已选择的预览 A：中部被沿剪切方向拖动，外围位移连续减小，外缘不随之整块移动。
- −X 对应画面向右、+X 对应画面向左。反向输入产生镜像形变，松开回到原网格。
- 不修改 normalLevel/shearLevel、方向模板、阈值、画面归零、串口服务、矩阵、固件或设备去皮。
- 保留当前画布布局、相机投影、样式、趋势图、G1–G6 和 12 路原始数据显示，不重做仪表盘。
- 无独立时间驱动的水波、持续流动或随机动画。
- 继续标注定性演示、非标定力值；不声称真实表面或接触点重建。
- 本目录非Git仓库，不初始化或提交；snapshot/no-index diff替代Git范围。
- 实际页面刷新后须操作者空载确认并点演示归零，不自动带载归零。

---
### Task 1: A 型局部拖拽绘图与回归

**Files:**
- Modify: `demo_web/surface.js` (draw 内 point 与 intensity，仅绘图)
- Create: `tests/test_surface_drag.py`（真实 Chromium Canvas 绘制行为）
- Evidence: `.superpowers/sdd/local-drag-*.png`
- Report: `.superpowers/sdd/local-drag-task-1-report.md`

**Interfaces:** 保留 createSurface(canvas) 返回 target/level/shearTarget/shearLevel/set/clear/resize；保留 normalLevel/shearLevel 与所有 API。新测试可加载 surface.js 到隔离 canvas 页面，不访问 COM10 或生产服务。测试 synthetic profile：version=1,mode=qualitative, normal threshold=100/span=600, shear enabled=true/weights=[.125,.125,.125,.125,-.125,-.125,-.125,-.125]/pressLeak=8个0/threshold=20/span=80。channels=[100×4,-100×4,0×4] → s=1；反向 → s=-1；末4路700 → p=1。

- [x] Step 1: 新增测试后先运行 RED，使用真实浏览器 canvas、记录绘图 path 同时调用原 ctx 方法。隔离页面设 reduced_motion="reduce"，加载 production surface.js，createSurface(canvas)，检查 flat/right/left/normal/combined/clear。可按以下方式捕获实际 draw，不给生产加 test-only API：

```javascript
const canvas = document.getElementById('test-canvas');
const ctx = canvas.getContext('2d');
window.drawnCells = [];
let points = [];
const begin = ctx.beginPath.bind(ctx), move = ctx.moveTo.bind(ctx);
const line = ctx.lineTo.bind(ctx), stroke = ctx.stroke.bind(ctx);
ctx.beginPath = () => { points = []; begin(); };
ctx.moveTo = (x,y) => { points.push([x,y]); move(x,y); };
ctx.lineTo = (x,y) => { points.push([x,y]); line(x,y); };
ctx.stroke = () => { drawnCells.push(points.map(p => [...p])); stroke(); };
window.dragView = createSurface(canvas);
```

每次 set/clear/resize 前清空 drawnCells。采用既有18×18网格，cell[j*18+i] 的四顶点顺序为(i,j),(i+1,j),(i+1,j+1),(i,j+1)。
首轮至少以下两种预期失败：right 的外边缘与 flat 应一致（旧图统一平移不一致）；固定 j=9 的同一条网格线若干顶点应非共线（旧图线性 tilt 仍共线）。
测试完整约束：中心 x 位移明显，外围位移小，左右镜像，从实际绘图顶点移除约定高度项并逆投影后的材料坐标中，单元两三角形有向面积为正且非相邻线段不交叉（p=0/1,s=-1/0/1）；颜色/alpha 在纯剪切时有局部变化，clear 返回完全相同的 flat path/pixels，正压-only 维持旧 center (w*.5,h*(.34+.17)) 与原包络，resize/reduced-motion 保持。2026-09-26 操作者“保留”批准替换原先投影三角形同向条件，原正压高度必须不变。
输出前先明确 RED 原因，不修改生产代码。

Run: `D:\conda\python.exe -m unittest tests.test_surface_drag -v`
Expected: meaningful assertion FAIL for current planar shift/tilt.

- [x] Step 2: 仅替换绘图坐标。当前投影、18步网格及渲染生命周期不变。以下是实现公式：

```javascript
const shift = surface.shearLevel;
const envelope = ((1 - u * u) * (1 - v * v)) ** 2;
const drag = 0.44 * shift * envelope;
const center = 0.19 * shift;
const bump = Math.exp(-((u - center) ** 2 + (v + center) ** 2) / 0.18);
const ridge = 0.19 * shift * (u - v) * envelope;
return [
  w * (0.5 + (u + drag - v + drag) * 0.23),
  h * (0.34 + (u + v) * 0.105 + (bump * surface.level + ridge) * 0.17),
  Math.min(1, bump * surface.level + Math.abs(shift) * envelope * 0.8)
];
```

intensity 变为四顶点[2]均值，不再二次乘 surface.level。s=0 时保持旧强度、形状；剪切-only 有局部色块。数学满幅不应翻折；若实际测试指出规格冲突，报告，不暗中改公式或测试绕过。
不得修改计算normalLevel/shearLevel及profile、app.js、index.html、style.css、采集端。

- [x] Step 3: GREEN 与全回归。
Run: `D:\conda\python.exe -m unittest tests.test_surface_drag -v`
Expected: 新测试通过。
Run: `D:\conda\python.exe -m unittest discover -s tests -q`
Expected: 全部通过，若既有像素质心测试出现不符合方向条件的失败，分析颜色质心及几何原因，不删/放宽旧断言掩盖失败。

- [x] Step 4: 离线真实 dashboard 截图：利用既有 FakeSource/make_handler 独立随机端口 HTTP 服务，mode="replay"或页面明确追加“模拟验收，非实时设备”标记，模拟右/左/normal/combined/clear，保存 local-drag-*.png，不能注入本机8765生产页面。root 负责图像目视复核与实机页面换版，不操作live COM10或自动tare。

- [x] Step 5: 自审并写报告：记录命令、RED/GREEN、全回归计数、截图来源、变更文件、遗留限制、任何测试日志噪声。非Git目录不init/commit；不得覆盖他人改动。root 生成no-index diff后独立审阅。
