# 03 — 标定与实验数据（不同于演示调参）

## 本库有三种模型，必须区分

1. **官方参考传感器 + MLP**：`upstream/coin-ft-coin-ft-8166d49/calibration/` 与 `visualization/`，原样保留采集、数据处理、训练、参考传感器可视化和 HDF5 例子；环境文件在上游目录。样例 CFT24 权重不适用于我们的装配。
2. **本机历史砝码六维矩阵**：`calibration/coinft_calib_collect.py`、`ground_truth.py`、`coinft_calib_fit.py`、`coinft_read_ft.py`。输出 `coinft_calib.json` 的24×6矩阵；历史证据并非当前六轴计量验收。
3. **当前定性动画**：`demo_web/shear_demo_profile.json`，只做中心按压与一轴双向剪切，没有 N/N·m 输出；历史方向模板工具在 `calibration/fit_demo_profile.py`、`build_qualitative_demo_profile.py`、`shear_refit_replay.py` 和 `.superpowers/sdd/`，不得为复现自动覆盖当前 profile。

## 人工砝码采集

```powershell
python -m pip install -r requirements-calibration.txt
python calibration/coinft_calib_collect.py --port COM6 --poses calibration/poses.csv --seconds 3 --out my_calib_raw.csv
```

脚本逐姿态提示，输入实际质量、摆稳后按 Enter 才采集；不是口头说“5秒”后自动连续换姿态。每次记录空载，载荷轻放，手远离电容区。固定方式、传力面、垫片、屏蔽、供电与调参表都要记录一致；机械结构改变后旧矩阵不能直接当可靠答案。

标定前暖机，粘胶等冷却；热漂、回弹、蠕变与电容靠近效应可大于轻载信号。先做空载→固定载荷→卸载及重复性检查，再拟合；拟合不能修复输入没有可区分信号、错误载荷标签或截断/失流数据。

## 矩阵与可复现历史拟合

历史实现计算 `x = raw - tare`，特征 `[x1..x12, x1²..x12²]`，`FT = features @ A`，列序 `[Fx,Fy,Fz,Mx,My,Mz]`。目标由 `poses.csv` / `poses_flats.csv` 几何和 `ground_truth.py` 求重力及 `r×F`，姿态和力臂符号需实物核对。

`coinft_calib_fit.py` 实际实现：特征只缩放、不去均值的 λ=1 岭回归；Fz 仅用平放样本、normal 四路共享的两参数拟合；`DROP_POSES` 排除了摆放错误/污染姿态。不是“通用官方24维OLS”或所有模型均已验证。历史模型警告包含组合载荷未验证、低载荷法向死区；报告的留一误差也不是可追溯参考传感器精度。

脚本将模型写到**当前工作目录**。为了不覆盖本库旧矩阵，可在新目录中复现已保存两段数据（从仓库根目录执行）：

```powershell
New-Item -ItemType Directory -Path fit_review
Push-Location fit_review
python ../calibration/coinft_calib_fit.py ../calibration/calib_raw_20260910.csv ../calibration/calib_flats_20260911.csv
Pop-Location
```

`fit_review/coinft_calib.json` 是复算产物，不会自动替换运行配置。读取某个新矩阵可用：

```powershell
python calibration/coinft_read_ft.py --port COM6 --calib fit_review/coinft_calib.json
```

该 reader 启动自动空载去皮，需先关闭 demo，并先卸载；屏幕有 N 单位不代表矩阵适用于当前传感器。

## 数据标记

- `calib_raw_20260910.csv` / `calib_flats_20260911.csv`：历史拟合输入；`poses*.csv` 是姿态定义。
- `repeat*` / `shield*` / `official_face*` / `new_coinft*` / `continuous*`：历史 Z 轴、屏蔽、夹具、重复与逐路调参排查。文件中的失败也是证据，不等于当前参数。
- `shear_refit_*` / `demo_attempt_*` / `spatial_gate_*`：旧动画模板与诊断；保留操作纠正 sidecar（例如误报推住实际已松开），不能静默改为成功样本。
- `.superpowers/sdd/*report*` / `*analysis*` / `*failed*`：离线分析和审查；绝对本机路径只描述历史环境。

没有统一 counts/N 常数，也不能直接将六组电容条形对应到 Fx/Fy/Fz/Mx/My/Mz。要标定当前指尖产品，需要匹配量程/不确定度的六轴参考、稳定夹具、时间对齐、覆盖组合载荷的训练/独立验证集；本库没有把未完成部分伪装成验收通过。
