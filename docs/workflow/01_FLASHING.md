# 01 — CoinFT PSoC 底层板烧录

## 固件身份

- 目标：CY8C4149AZI-S593 / PSoC 4100S Max。历史识别 Silicon `0x2E2B`、Family `0xBE`、Rev A0；其他芯片不要套烧。
- 文件：`firmware/psoc/CoinFT_V2_firmware.hex`，官方存档副本。
- SHA256：`615d38614e587bbb03512ab7565b7451839bd992a490ec1541d70e0ba2249725`。
- 官方公开的是 HEX；本库没有可编辑的 PSoC 感测固件源码。不能把 Teensy 程序烧进 PSoC。

## 两条工具路线，别混用

**官方路线（上游参考）**：按上游 Hardware Instructions / 制造文件，使用匹配芯片的新版 Infineon 编程工具和受支持的探针。先确认具体探针型号及供电，而不是只看“PSoC 烧录器”商品名。

**本机历史成功路线（旧 KitProg1）**：项目日志记录 CY8CKIT-059 拆出的 KitProg1，USB `04B4:F139` 专有模式；Zadig 仅将编程接口 **MI_01** 绑定 WinUSB，使用 Infineon OpenOCD 的 `interface/kitprog.cfg` 和 `target/infineon/psoc4.cfg`。本次发布读取到安装版本 `0.12.0+dev-5.19.0.4782`。这条路线不是所有 KitProg、普通 OpenOCD 或主机的通用保证。

旧 PSoC Programmer 3.29.6 曾报 `Unsupported M0S8 Device / Family 0xBE` 和 HEX 解析失败；其界面显示 CY7 开头设备不代表检测到了目标 PSoC。不要靠改 HEX 路径或反复点击来判断已经成功。

## 接线与工具边界

烧录走 **SWDIO、SWCLK、GND、目标供电/电压参考**，需要时按探针规范接 XRES，不走 UART RX/TX。实际板端焊盘和探针脚号以丝印/原理图确认，不按照片猜。

- 本机 SWD 线约 30 cm 时曾无法识别，缩至约 8 cm 后成功；优先短线、共地、牢固接触。
- 确認芯片/板供电及探针适配范围。历史实测约 4.8–5.0 V 是该装配的观测值，不是任意探针或 GPIO 都耐 5 V。
- 不让两个电源互相顶电；UART 转接板和 SWD 目标供电要按各自规范处理。
- 驱动切换只选确认过硬件 ID 的编程接口，不改 USB-UART。关闭 Zadig、旧 Programmer 及占用探针的其他程序再运行 OpenOCD。必要时按 Windows 提示保存工作并重启。

## 命令入口（重现参考，发布时没有执行硬件烧录）

安装官方 Infineon 工具后，在仓库根目录替换为自己的路径。先做目标识别；它也会连接/复位目标，因此不属于无扰动读取。

```powershell
$openocdExe = 'C:/Infineon/Tools/ModusToolboxProgtools-1.9/openocd/bin/openocd.exe'
$openocdScripts = 'C:/Infineon/Tools/ModusToolboxProgtools-1.9/openocd/scripts'
& $openocdExe -s $openocdScripts -f interface/kitprog.cfg -f target/infineon/psoc4.cfg -c 'init; reset halt; flash info 0; shutdown'
```

只有确认目标、接线、供电与探针都正确后再写。以下是 OpenOCD 的 program/verify 入口示例，不宣称已在发布当日用它重烧板子，也不是旧会话完整命令日志：

```powershell
& $openocdExe -s $openocdScripts -f interface/kitprog.cfg -f target/infineon/psoc4.cfg -c 'program firmware/psoc/CoinFT_V2_firmware.hex verify reset exit'
```

不启用 `ALLOW_KILL_MODE`，不为排查而改锁定/保护配置。SDK 脚本/驱动不是本库自带，禁止把其他发行版的同名脚本当成验证等价替代。

## 验收，不能只看“Connected”

1. 确认目标是 CY8C4149AZI-S593，而不是 GUI 的默认设备。
2. 保存完整烧录日志，要求编程成功和明确 verify 成功，不能把超时、checksum mismatch 或验证中断当 PASS。
3. 如旧探针大块读取超时，只能记录读取限制；向量表/小块抽查一致不等于整片逐字节一致。项目后来日志记录 `Programming Finished` / `Verified OK` 与抽查；这是历史记录，不抹掉前期失败。
4. 重启后在 UART 验证合法帧、12 路、帧率与无饱和。写入校验通过不等于装配/标定也合格。

本次发布只核对 HEX 与上游逐字节一致、文件哈希和工程完整性，**未重新连接烧录器、烧录或做整片硬件验证**。若出现超时/目标识别失败，停止宣称成功，先排查模式、驱动、接口占用、SWD 短线、共地与供电。
