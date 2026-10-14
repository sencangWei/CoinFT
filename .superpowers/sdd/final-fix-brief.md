# Final-review fix brief — stalled poll and motion preference

整体审查在 `demo_web/app.js` / `demo_web/surface.js` 发现两个问题，需以最小改动修复：

1. Important: `/api/state` 的 `fetch` 或 `response.json()` 若一直挂起，`fetching` 保持 true，旧受力凹陷和“数据正常”可无限冻结。增加覆盖请求和正文读取的有界超时（约 1.5 秒，符合现有 50 ms 轮询但容忍短暂抖动）；超时应进入已有 `catch` 清空路径，`finally` 释放定时器和 `fetching`。之后服务恢复仍能重新轮询。先加浏览器失败测试，模拟请求挂起并验证超时清空、恢复后重新 live。
2. Minor: 在曲面正在插值时，系统媒体查询 `prefers-reduced-motion` 改为 reduce，现有 `set()` 不再调用时动画仍会跑完。监听媒体查询 `change`，切换到 reduce 时取消 RAF、使 `level` 立即到 `target` 并绘制；先加聚焦测试使旧实现失败，再修复。

负责文件：`demo_web/app.js`、`demo_web/surface.js`、`tests/test_demo_ui.py`。保留其它已有变更，不改后端、固件、API、调参或原图表。此目录不是 Git 仓库；不创建提交。所有编辑用 `apply_patch`。

验证：两项新测试各自红→绿；再运行 `D:\conda\python.exe -m unittest discover -s tests -v`。若浏览器或本地 HTTP 服务因人为挂起产生异常日志，说明是测试工况还是实现问题；清理测试资源。报告写到 `D:\semg.claude\coinft\.superpowers\sdd\final-fix-report.md`，写明测试命令/结果、变更、风险和剩余限制。
