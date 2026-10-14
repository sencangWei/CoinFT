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

## Teensy CDC2 局部适配引用的 PJRC 原许可

`firmware/teensy/scripts/diag_usb_nonblocking.py` 的局部发送适配及其生成结果涉及 Teensy core `usb_serial2.c`。相关 PJRC 原代码保留以下原许可，不由本库 CoinFT 的 CC 许可替代；生成文件仍保留 SDK 原文件头。

```text
Teensyduino Core Library
http://www.pjrc.com/teensy/
Copyright (c) 2017 PJRC.COM, LLC.

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

1. The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

2. If the Software is incorporated into a build system that allows
selection among a list of target devices, then similar target
devices manufactured by PJRC.COM must be included in the list of
target devices and selectable in the same manner.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
