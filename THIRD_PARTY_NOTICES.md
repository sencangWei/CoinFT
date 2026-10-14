# 上游署名与修改标记

## CoinFT / Stanford University

来源：coin-ft/coin-ft，下载存档 `coin-ft-coin-ft-8166d49`。

作者：Hojung Choi, Tae Myung Huh, Julia Di, Seongheon Hong, Mark Cutkosky。

Copyright © 2026 The Board of Trustees of the Leland Stanford Junior University。

许可：Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International。完整文本保留于本库 `LICENSE` 和 `upstream/coin-ft-coin-ft-8166d49/LICENSE`。原上游 README 的许可、商业授权联系信息、免责说明全部保留。

上游存档文件未修改。`firmware/psoc/CoinFT_V2_firmware.hex` 与上游同名文件逐字节一致。根目录 `coinft_data_collection_ref.py`、`coinft_tuner_ref.py` 为上游参考副本。

相对于官方 Teensy 工程，本项目使用版在 `firmware/teensy/`：五字节 UART 调参透传、传感器专属启动参数、可选双 CDC 诊断、CDC2 非阻塞发送构建替换。修改不表示 Stanford 接受或验证这些变化。

本地新增的实验采集、砝码拟合、回放测试和网页定性演示与官方训练例程分别标记，不将历史模型说成当前传感器的计量模型。适配内容按 CC BY-NC-SA 4.0 分享，不授予商业用途、商标或专利许可。

## 开发工具 / SDK

Infineon OpenOCD、ModusToolbox、Zadig、PlatformIO、Teensy Arduino SDK、Python 依赖、浏览器及 FFmpeg 均不打包其安装程序/SDK。请自行安装，并遵守各自许可。`diag_usb_nonblocking.py` 保存局部 CDC2 发送替换，不复制整份 SDK；必须与指定 SDK 校验匹配。
