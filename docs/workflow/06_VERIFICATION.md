# 06 — 发布检查与复现

本次发布不烧录、不开硬件采集、不重新拟合动画参数。软件回放检查与真实硬件计量验收分别报告。

## 2026-10-14 已执行

- `python -X utf8 -m unittest discover -s tests -v`：**160/160 PASS**，95.744秒；包括浏览器、失流恢复、串口诊断、固件主机侧C++桩测试等。串口测试使用模拟对象，浏览器测试使用本地临时服务器，不替代实机。
- `python -X utf8 .superpowers/sdd/test_center_pull_refit_20261006.py -v`：**3/3 PASS**，历史数据回放，不宣称任何轻拉都稳定。
- `python firmware/teensy/test_tuning_passthrough.py`：五字节调参透传静态断言 PASS。
- `pio run -d firmware/teensy -e teensy40 -e teensy40_diag`：**2/2构建 SUCCESS**，PlatformIO Teensy5.2.0 / framework1.162.0；仅编译，没有上传到 Teensy。
- 最终 MP4：ffprobe 确认95.92秒/1080p/25fps/H264/yuv420p，FFmpeg整片严格解码检查 exit0。
- 官方存档41个文件逐字节与原下载ZIP一致，含被上游忽略规则排除、此处显式纳入的全部样例数据。
- 在隔离输出目录重算历史砝码拟合：31姿态/4平放，产物与原 `calibration/coinft_calib.json` 字节一致（SHA256 `c5847d9a03a16cf3a9fd6a951ec8c1dc7e58516cc071826169e90a8cd496beb2`）。复算仍报告热漂499 counts和 Fz 留一中位0.4212 N；没有把这些局限写成当前传感器验收通过。
- PSoC HEX 与上游字节一致；Teensy CPP、两脚本、透传断言与桌面实际工程字节一致。发布副本的 ini 只新增工具版本锁定。
- 原保护清单（profile单独核对）无新增变化；当前 profile/app/surface/backend 哈希如下。
- 公开候选文本进行凭据/私钥模式扫描，15个匹配均为 `task-3-normal-motion...` 文件名匹配 `sk-` 模式，人工复核非凭据；私人聊天、完整本机交接日志、账户缓存和排查原片不进入索引。该扫描是已知模式检查，不声称绝对不存在任何敏感信息。
- 完整逐文件清单 `PROJECT_FILES.json` 包含阶段、大小与SHA256；排除清单自身以避免递归。Git索引排查还排除了浏览器脑暴预览的 `.last-token`/PID等本机运行态，原件保留在本地，从未上传。

## 冻结哈希

```text
demo_web/shear_demo_profile.json
1df74f4570f5119f180f9e7830120abe555bd6c37cc33ab3dbc33b8dba5a6020
demo_web/app.js
e83a20cfcf844ef8733927bdd6e0774c93bf2f64b1aa68a075c89e3d416e2d66
demo_web/surface.js
d7ad21efd772367e0a63a9b1fceac466da481ece2abcc185505e1a63ee1fedbf
coinft_demo.py
96ef5bbe88ceb9797686d1e6b1b2473b50360b0a9225e5fac192ca6ddb913828
```

## 新电脑复现测试

```powershell
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
pio run -d firmware/teensy -e teensy40 -e teensy40_diag
python -X utf8 -m unittest discover -s tests -v
python -X utf8 .superpowers/sdd/test_center_pull_refit_20261006.py -v
```

还需系统 PATH 中的 `g++`（主机C++夹具，不是ARM编译器），并默认将 Teensy SDK 安装在当前用户 `.platformio/packages/framework-arduinoteensy/`。缺 SDK / 浏览器 / 编译器时全套测试会失败，这是依赖缺失，不应改断言让它冒充通过。本次只将两个测试的桌面绝对源码路径改为仓库相对路径，SDK查找改为当前用户目录；未改测试行为或演示算法。

上游 MLP / ATI / NI-DAQ 例程使用上游单独的 Conda 环境与真实采集设备，不包含在此160项本地演示软件测试中。SDK/安装程序没有上传。

## 检查边界

本次检查不等于重新验证全部历史实验结论、全部旧脚本可在任意电脑直接运行、当前传感器六轴精度、供电安全或真实接触点定位。旧文件中的 COM号/绝对路径和审批记录仅历史证据。需要硬件验收时按阶段01–03重新记录目标、供电、校验和独立载荷证据，不能用“动画会动”代替。
