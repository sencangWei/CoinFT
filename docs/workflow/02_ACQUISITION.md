# 02 — Teensy 4.0、12 路采集与原参数

## 接线与两个固件的区别

PSoC HEX 在阶段 01；本阶段在 Teensy 4.0 上编译/上传 `firmware/teensy/`。当前 `NUM_COINFTS=1`，桥接 `Serial2`。上游原版默认两只，不要把它覆盖当前实际使用版。

当前源代码使用 Teensy 4.0 Serial2：TX2 pin8、RX2 pin7。CoinFT TX 经 **5 V→3.3 V** 转换进 RX2；TX2 经 **3.3 V→5 V** 转换进 CoinFT RX，所有地共地。CoinFT 的 5 V 供电与 GPIO 电平转换是两件事，**Teensy GPIO 不可接 CoinFT 的约 5 V TX**。购买的模块需明确支持 UART 推挽与 1 Mbps；不要默认任意标着“3.3/5V”的稳压板或 I²C MOS 管模块都适用。

焊盘实际位置按丝印/资料检查，砝码不能短接焊点。固定一片 PCB，使另一片能相对受压/剪切，避免推整块组件或牵动线束。不是根据屏幕动画判断电气接线安全。

## 编译，不自动替你烧录

发布副本仅锁定本机验证工具版本：PlatformIO Teensy5.2.0 / framework-arduinoteensy1.162.0；CPP 与 scripts 从实际桌面工程原样复制。SDK 不打包。

```powershell
pio run -d firmware/teensy -e teensy40
pio run -d firmware/teensy -e teensy40_diag
```

普通版一个数据串口；当前使用的诊断版 `USB_DUAL_SERIAL` 有数据串口与 `CFD1` 心跳串口。诊断 SDK 适配只替换构建目录中的 CDC2 发送，不改全局 SDK；`usb_serial2.c` 必须匹配 SHA256 `575f5852165647e39f059548ae244a4b426a8be31bfef57cc4a9044fa8a37a3b`，不匹配应停止而非关闭保护。

确实需要上传 Teensy 时，先关闭占用数据/诊断串口的程序，再执行：

```powershell
pio run -d firmware/teensy -e teensy40_diag -t upload
```

这会改写 Teensy 固件。按板上 Program 键可能进入 HalfKay 加载器（VID16C0/PID0478，数据 COM 消失）；不是日常复位。误按后先不再按键，重新插 USB 检查程序是否启动。

## 协议

- CoinFT UART：1,000,000 baud / 8N1，`02 + 24字节 + 03`；12 × uint16 小端。
- Teensy 数据 USB：`00 00 + 24字节`，解析器检查相邻帧头，约 200 Hz；上位机设置 115200 是 USB CDC 配置，不是 CoinFT 的 UART 波特率。
- `i` 停止扫描/流，`s` 启动扫描/流；本机修复的调参下行是五字节 `t,ch,res,ref,comp`，通道索引 0–11。
- 诊断 `CFD1` 只从第二 CDC 输出，不混入原始 26 字节数据口。

## 当前冻结参数（ACTIVE_TUNING_20260907）

格式 `{Resolution, Ref, Compensation}`，权威源码在 Teensy 的 `TUNING`，主机 `coinft_acceptance.py` 相同：

```text
CH01 {12,50,50}  CH02 {12,30,72}  CH03 {12,30,81}  CH04 {12,30,82}
CH05 {12,30,83}  CH06 {12,30,85}  CH07 {12,30,76}  CH08 {12,30,75}
CH09 {12,100,17} CH10 {12,100,26} CH11 {12,80,58}  CH12 {12,80,42}
```

**参数写入 CoinFT 运行时，断电丢失，不是持久烧入 PSoC。** Teensy 的 setup 会重新下发，所以 CoinFT 必须在这时已经供电；Teensy 先启动、CoinFT 后通电会错过初始化。重新打开 demo 只发送 i/s，不会补发 t，也不能用“演示归零”补偿错表。

后上电时，先关掉占用 COM 的 demo；确认仍是已调好的传感器、空载，才重发**原表**并采一段：

```powershell
python coinft_acceptance.py --port COM6 --tune --seconds 5 --out restored_baseline.csv
```

会写运行时参数并启停流，不是自动重新优化。完成再启动 demo 并空载演示归零。新换一只传感器不可盲套此表。早期 TTL 高补偿表单独保存于 `config/historical_tuning_20260901.txt`，仅历史对照。

## 采集检查

```powershell
python coinft_acceptance.py --port COM6 --seconds 5 --out unloaded.csv
python coinft_acceptance.py --port COM6 --seconds 15 --out loaded.csv
```

两段需要人工分别准备空载和受力；脚本不替你换砝码。检查新帧、约 200 Hz、错位、饱和、12 路 distinct/跨度；已知饱和平台33782。历史 `baseline_20260907.csv`、`dynamic_20260907.csv`、`verify_autotune_20260907.csv` 是保存证据，不是本次新的硬件验收。

CH1–8 为 shear 相关电容，CH9–12 为 normal 相关；它们不是互相独立的六轴力计。耦合、寄生电容、偏心载荷和噪声会使多个通道同时变化，G1–G6 仅成对绝对响应，不能据此断言六个力分量全满。
