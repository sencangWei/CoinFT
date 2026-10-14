# 00 — 项目文件与版本身份

发布日期：2026-10-14。此文档是公开技术交接；不公开私人聊天或整份本机工作日志。

逐文件身份、大小和校验在根目录 `PROJECT_FILES.json`；当前参数/固件/视频身份汇总在 `config/ACTIVE_RELEASE.json`。历史报告中的原工作机录屏截图、浏览器预览服务令牌/PID与私人交接不公开；核心原始采集数据和分析脚本保留。

## 身份标签

| 标签 | 权威文件 | 用途 / 禁止混淆 |
|---|---|---|
| OFFICIAL_8166d49 | `upstream/coin-ft-coin-ft-8166d49/` | 原版硬件、HEX、Teensy、MLP、样例数据 |
| ACTIVE_PSOC_V2 | `firmware/psoc/CoinFT_V2_firmware.hex` | 与上游 HEX 一致；只给匹配 CY8C4149AZI-S593 使用 |
| ACTIVE_TEENSY_40 | `firmware/teensy/` | 实际使用的 Teensy 4.0 工程，不是原版参考工程 |
| ACTIVE_TUNING_20260907 | `firmware/teensy/teensy_coinft_serial_interface.cpp` 与 `coinft_acceptance.py` 的 TUNING | 当前保留的 12 路参数表 |
| HISTORICAL_TTL_20260901 | `config/historical_tuning_20260901.txt` | 同一项目的早期 TTL 调参，**不再作为默认表** |
| HISTORICAL_CALIB_20260911 | `calibration/coinft_calib.json` | 砝码分轴拟合，低载荷 Fz / 组合载荷限制尚存 |
| ACTIVE_VISUAL_20261006 | `demo_web/shear_demo_profile.json` | 定性按压＋±X 剪切，不是 N/N·m 矩阵 |
| ACCEPTED_DEMO_20261014 | `demo/CoinFT_demo_20261014_after_2min.mp4` | 用户接受当前可用版后的最终裁剪视频 |
| HISTORICAL_EXPERIMENT | `calibration/`、`.superpowers/sdd/`、`docs/superpowers/` | 文件名日期 + 内部报告区分实验/失败/审查；不要按日期最新就自动部署 |

## 阶段时间线（历史证据，不是本次硬件重验）

1. 2026-08 至 09 初：旧 PSoC Programmer 不识别目标 / HEX，旧 KitProg 大块读取超时，先前的“烧录完成”不足以验收。后来使用 Infineon OpenOCD + WinUSB 路线，项目日志记录 `Verified OK`；串口无输出曾定位为 TX 连线断路。
2. 2026-09-01：TTL/CH343 直接采集与手工调参；保存早期表。此表与后期补偿值不同，并不意味着两块完整传感器。
3. 2026-09-07：SWD 线从 30 cm 改约 8 cm，日志记录新底层板烧录成功；修复 Teensy 五字节透传、自动调参后，`dynamic_20260907.csv` 记录 12 路动态响应，`verify_autotune_20260907.csv` 保存启动自动下发检查。
4. 2026-09-10 至 14：砝码姿态采集、分轴矩阵、白色圆柱/屏蔽片/传力/热漂与低载荷 Fz 对比实验。早期若只根据记录名称推断板号，后来已更正；新换传感器参数不可自动沿用。
5. 2026-09-24 至 28：12 路与六组响应、旧矩阵趋势、中心凹陷、局部剪切拖动；增加空载归零、重复快照容忍、失流恢复和双 CDC 诊断。
6. 2026-10-05 至 06：剪切模板/正压泄漏补偿与中心 −X 拉动排查，启用当前 profile；候选与失败数据保留但不替换现用文件。
7. 2026-10-14：核对现用版本；用户确认 Teensy 先接、CoinFT 后供电，授权重新下发**原参数**；推 −X 恢复，轻拉仍有不稳定。用户接受现版并停止继续优化，录制 Demo，裁去正式片前两分钟。

## 不可误用的旧路径

历史记录里的 `C:/Users/.../Desktop`、`D:/semg.claude`、COM10 是当时工作机环境，不是新电脑的安装要求。当前发布副本在本库 `firmware/teensy`，端口按本机设备实际枚举选择。本机录制使用 COM6 数据 / COM8 诊断；不得把诊断口作为数据口。

对无法在公开资料确认的元件脚号、制造胶粘工艺和电流额定值，不根据照片猜测。上游制造文件位于 `upstream/.../hardware_files/`；其中没有可编辑 PSoC 感测源码或完整可编辑 PCB 项目。
