# CoinFT：烧录 → 采集 → 标定 → 可视化 Demo

基于 Stanford CoinFT 的非官方复现与实验工程，保留官方存档、实际使用的 Teensy 4.0 固件、12 路原始数据、标定实验、浏览器演示和录制视频。

完整逐文件清单：[PROJECT_FILES.json](PROJECT_FILES.json)（阶段标签、字节数、SHA256；清单自身不递归列入）。当前使用版本的机器可读标记：[ACTIVE_RELEASE.json](config/ACTIVE_RELEASE.json)。

**当前演示：中心按压凹陷 + ±X 水平剪切拖动。−X 对应画面向右，+X 向左。动画是实时信号驱动的定性展示，不代表真实表面形貌、接触点定位或经计量验收的六维力值。** 原趋势页保留；2026-10-14 用户接受当前可用版本，不继续调参。轻拉 −X 在部分接触方式下仍不稳定。

## 从头开始：阶段导航

| 标记 | 阶段 | 文档 / 文件 | 状态 |
|---|---|---|---|
| 00 | 文件身份、版本和历史索引 | [版本索引](docs/workflow/00_INDEX.md) | 首先阅读 |
| 01 | PSoC 底层板烧录、KitProg 排查 | [烧录说明](docs/workflow/01_FLASHING.md)、`firmware/psoc/` | 历史成功路线；发布时未重烧硬件 |
| 02 | Teensy 4.0 烧录、UART、电平转换、运行时调参 | [采集说明](docs/workflow/02_ACQUISITION.md)、`firmware/teensy/` | 本项目实际使用版 |
| 03 | 砝码标定、拟合、参考传感器采集 | [标定说明](docs/workflow/03_CALIBRATION.md)、`calibration/` | 实验记录，不是通用准确矩阵 |
| 04 | 实时界面、中心按压与双向剪切 | [现场操作](DEMO_README.md)、`demo_web/`、`coinft_demo.py` | 当前保留版 |
| 05 | 最终录制 Demo | [视频](demo/CoinFT_demo_20261014_after_2min.mp4)、[视频说明](demo/README.md) | 已裁去前两分钟，95.92 秒 |
| 06 | 测试、文件完整性和发布检查 | [检查记录](docs/workflow/06_VERIFICATION.md) | 区分软件检查与硬件验收 |

## 快速打开界面

需要 Python（本机验证环境 3.13）、`pyserial`，浏览器无需前端构建。

```powershell
python -m pip install -r requirements.txt
python coinft_demo.py --port COM6
```

将 `COM6` 换成 Teensy 的**数据串口**。诊断版有两个串口，另一个输出 `CFD1` 诊断，不是 12 路数据。页面地址 `http://127.0.0.1:8765/`。保持空载，先点“演示归零（仅画面）”；实时状态正常后演示。CoinFT 必须在 Teensy 初始化下发参数时已供电，后上电需重发原参数，见阶段 02。

无硬件查看历史回放（不能冒充实时）：

```powershell
python coinft_demo.py --replay dynamic_20260907.csv
```

`START_DEMO.bat` 保留原工作机入口（`D:\conda\python.exe`、COM6）；其他电脑使用上述通用命令。软件测试依赖见 `requirements-dev.txt`；完整复现说明在阶段 06。

## 原版、改版、历史数据不要混用

- `upstream/coin-ft-coin-ft-8166d49/`：官方下载存档，保持文件原样。官方样例模型、参数及 ATI 同步数据不是本机这只 CoinFT 的标定。
- `firmware/teensy/`：从实际使用的桌面工程复制，修复五字节调参透传，含可选双 CDC 诊断；`firmware/psoc/` 是官方 HEX 副本。没有可编辑 PSoC 感测固件源码。
- `demo_web/shear_demo_profile.json`：当前启用的定性参数；`calibration/coinft_calib.json`：历史砝码拟合矩阵，两者用途不同。
- `calibration/`、`.superpowers/sdd/`、`docs/superpowers/`：按日期保留的实验、诊断、失败候选与设计审查。路径未移动以保留测试/回放依赖；旧方案不代表正在启用。

公开包不含私人聊天导出、完整私人交接日志、账户配置、缓存和超大排查录屏；原文件仍留在本地。公开技术时间线见阶段 00。

## 署名与许可

CoinFT 原项目：Stanford University；Hojung Choi、Tae Myung Huh、Julia Di、Seongheon Hong、Mark Cutkosky。Copyright © 2026 The Board of Trustees of the Leland Stanford Junior University。

上游源地址：`https://github.com/coin-ft/coin-ft`，本库存档版本短号 `8166d49`。原许可 **CC BY-NC-SA 4.0**，完整文本见 [LICENSE](LICENSE)，原版权/使用说明保存在上游 README。适配部分继续遵守同一许可；修改说明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。公开不意味着可用于商业产品；商业使用需按上游要求另行获得授权。此仓库不代表 Stanford 官方或其背书。
