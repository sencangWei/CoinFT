"""Fit CoinFT 12ch raw -> 6-axis F/T calibration matrix (quadratic, per official method).

    D:/conda/python.exe coinft_calib_fit.py calib_raw_20260907.csv

Per pose: trim first/last 10% of samples, average the rest. Each pose is tared
by the most recent tare* pose before it in collection order (sessions collected
at different times have different thermal states — pass multiple CSVs in
collection order and start each session's file with its own tare pose).
Regressors X = [x_tared, x_tared^2] (24), targets Y = ground-truth 6-axis from
poses.csv geometry. Least squares (truncated SVD) per official method.
Writes coinft_calib.json + RMSE report + leave-one-out validation.
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ground_truth import ground_truth  # noqa: E402

POSES_CSV = Path(__file__).with_name("poses.csv")
AXES = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]

# 20260910 数据: 4 个倒挂姿态响应与竖立姿态几乎完全相同(相关系数 0.99~1.00,
# 物理上不可能——倒挂应以 +Fz 拉力为主), 判定摆法未真正实现倒挂, 不参与拟合.
# 若补采了正确的倒挂数据, 把对应 pose_id 从下面删掉重跑即可.
# 旧平放 4 姿态(f100/f200/f400/f1000): 暖机+蠕变污染(法向通道 20g 与 100g 读数
# 几乎相同, Fz 拟合被毒化), 由 poses_flats.csv 补采的 fz* 姿态替代其角色.
DROP_POSES = {"x_hang", "y_hang", "xf_hang", "yf_hang",
              "f100", "f200", "f400", "f1000"}


def main():
    raw_paths = [Path(a) for a in sys.argv[1:]]
    if not raw_paths:
        sys.exit("用法: coinft_calib_fit.py 数据.csv [更多数据.csv ...]  (按采集先后顺序)")
    samples = defaultdict(list)
    actual_mass = {}
    order = []  # 跨文件全局采集顺序, 决定每个姿态用哪个 tare
    for raw_path in raw_paths:
        with open(raw_path) as f:
            for row in csv.DictReader(f):
                pid = row["pose_id"]
                if pid not in samples:
                    order.append(pid)
                samples[pid].append([float(row[f"ch{k}"]) for k in range(1, 13)])
                ma = row.get("mass_actual_g")
                if ma:
                    actual_mass[pid] = float(ma)

    poses = {}
    for table in (POSES_CSV, POSES_CSV.with_name("poses_flats.csv")):
        if not table.exists():
            continue
        with open(table, encoding="utf-8") as f:
            lines = [l for l in f if not l.startswith("#")]
        for r in csv.DictReader(lines):
            if r["pose_id"].strip():
                poses[r["pose_id"]] = r

    # Per-pose stable mean (trim 10% each end)
    means = {}
    for pid, rows in samples.items():
        a = np.array(rows)
        k = max(1, len(a) // 10)
        means[pid] = a[k:-k].mean(axis=0)

    if "tare0" not in means:
        sys.exit("数据里必须有 tare0 空载姿态")
    tare = means["tare0"]  # 仅用于 json 记录和漂移检查

    # 每个姿态用它前面(全局采集顺序)最近一次空载当零点——不同采集段热状态不同
    tare_of = {}
    last = "tare0"
    for pid in order:
        if pid.startswith("tare"):
            last = pid
        else:
            tare_of[pid] = last

    X_rows, Y_rows, used = [], [], []
    for pid, mean in means.items():
        if pid.startswith("tare") or pid in DROP_POSES:
            continue
        if pid not in poses:
            print(f"!! 跳过 {pid}: 姿态表中无定义")
            continue
        p = dict(poses[pid])
        if pid in actual_mass:
            p["mass_g"] = str(actual_mass[pid])  # 采集时输入的实测质量优先
        f, m = ground_truth(p)
        x = mean - means[tare_of[pid]]
        X_rows.append(np.concatenate([x, x ** 2]))
        Y_rows.append([*f, *m])
        used.append(pid)

    X, Y = np.array(X_rows), np.array(Y_rows)
    is_flat = np.array([poses[pid]["type"] == "flat" for pid in used])
    print(f"{len(used)} 个姿态参与拟合（平放 {is_flat.sum()} 个只用于 Fz 列）")

    # 分轴拟合:
    # - Fx/Fy/Mx/My/Mz: 全部姿态(含平放)。平放提供关键约束"法向通道大读数
    #   => 剪切/力矩 = 0"; 若踢掉平放, 剪切列在按压(法向主导)输入上外推
    #   出垃圾(实测: 100g 居中压, Fx 读出 +1.96N)。按压恰是主要使用场景.
    # - Fz: 只用平放姿态(干净, 无胶), 法向通道 ch9-12 共享系数的 2 参数模型
    #   Fz = a*sum(x_n) + b*sum(x_n^2). 斜面姿态的法向通道被热漂污染(同载荷
    #   反号), 不能用于 Fz; 该传感器法向有死区(<100g 响应很平), 2 参数更稳.
    Xm, Ym = X, Y
    # 只缩放(不去均值)的岭回归: 保持 x=0 -> 输出 0 的原点锚定(运行时去皮后 x=0),
    # 同时消除 x 与 x^2 特征量纲悬殊(200g 姿态的 x^2 ~1e8, 会霸占最小二乘子空间).
    # λ=1: 居中按压剪切泄漏 0.36N -> ~0.01N, LOO 中位 Fx 0.055/Fy 0.084/M 0.0002.
    # 极端剪切姿态(tx90 等, 采集最晚漂移最大)与干净数据矛盾, 拟合不足是刻意的
    # ——硬拟合等于把漂移引进矩阵. scale 最后折进矩阵, 运行时接口不变.
    LAM = 1.0
    scale = X.std(axis=0)
    scale[scale == 0] = 1.0
    Zs = X / scale
    A = np.linalg.solve(Zs.T @ Zs + LAM * np.eye(Zs.shape[1]), Zs.T @ Ym)
    Xf, Yf = X[is_flat], Y[is_flat]
    if len(Xf) >= 2:
        S = Zs[is_flat][:, 8:12].sum(axis=1)
        Q = Zs[is_flat][:, 20:24].sum(axis=1)
        ab, *_ = np.linalg.lstsq(np.column_stack([S, Q]), Yf[:, 2], rcond=None)
        A[:, 2] = 0.0
        A[8:12, 2] = ab[0]
        A[20:24, 2] = ab[1]
        print(f"Fz 列: {len(Xf)} 个平放姿态, a={ab[0]:.3e} b={ab[1]:.3e}")
    else:
        print("!! 无平放姿态, Fz 列由斜面姿态拟合, 不可信")
    A = A / scale[:, None]  # 折回原始特征空间: FT = [x, x^2] @ A

    # 分轴评估: Fz 列只在平放姿态上评(它的训练集), 其余列在全部姿态上评
    span = np.abs(Ym).max(axis=0)
    span[span == 0] = np.nan
    rmse = np.sqrt(((Xm @ A - Ym) ** 2).mean(axis=0))
    if len(Xf):
        rmse[2] = np.sqrt(((Xf @ A - Yf)[:, 2] ** 2).mean())
        span[2] = np.abs(Yf[:, 2]).max()

    print("\naxis   RMSE        max|true|   RMSE%   (分轴: Fz 评于平放, 其余评于非平放)")
    for i, ax in enumerate(AXES):
        print(f"{ax:<4}  {rmse[i]:.5f}    {span[i]:.4f}      "
              f"{100*rmse[i]/span[i] if span[i]==span[i] else float('nan'):.2f}")

    # 留一交叉验证(中位绝对误差): 比样本内 RMSE 更诚实的泛化指标.
    # 剪切/力矩列在全部姿态间做(同分布), Fz 列在平放姿态间做.
    loo_m = np.zeros_like(Ym)
    for k in range(len(Xm)):
        m_ = np.arange(len(Xm)) != k
        Ak = np.linalg.solve(Zs[m_].T @ Zs[m_] + LAM * np.eye(Zs.shape[1]),
                             Zs[m_].T @ Ym[m_])
        loo_m[k] = Xm[k] @ (Ak / scale[:, None]) - Ym[k]
    med = np.median(np.abs(loo_m), axis=0)
    if len(Xf) >= 2:
        loo_f = np.zeros(len(Xf))
        for k in range(len(Xf)):
            m_ = np.arange(len(Xf)) != k
            abk, *_ = np.linalg.lstsq(
                np.column_stack([S[m_], Q[m_]]), Yf[m_, 2], rcond=None)
            loo_f[k] = abk[0] * S[k] + abk[1] * Q[k] - Yf[k, 2]
        # 最重锚点(fz200)留出=外推, 误差不计入中位
        keep = np.arange(len(Xf)) != np.abs(Yf[:, 2]).argmax()
        med[2] = np.median(np.abs(loo_f[keep]))
        print("\nFz 平放留一误差 (N; 最重锚点留出属外推, 仅供参考): " +
              "  ".join(f"{pid} {e:+.3f}" for pid, e in
                       zip(np.array(used)[is_flat], loo_f)))
    print("\n留一验证中位|误差| (N / N*m; Fz 在平放姿态间, 其余在非平放姿态间):")
    print("  " + "  ".join(f"{ax} {med[i]:.4f}" for i, ax in enumerate(AXES)))

    # Drift check
    if "tare1" in means:
        drift = means["tare1"] - tare
        print(f"\n零点漂移 (tare1-tare0) 最大通道: {np.abs(drift).max():.0f} counts")
        if np.abs(drift).max() > 200:
            print("!! 漂移偏大，标定期间环境/温度可能不稳定")

    out = {
        "created": "+".join(p.name for p in raw_paths),
        "poses_used": used,
        "tare_counts": tare.tolist(),
        "matrix_24x6": A.tolist(),
        "ridge_lambda": LAM,
        "regressor_order": "x = raw - tare_counts; features = [x(12), x^2(12)]; "
                           "FT = [1*x..., x^2...] @ matrix -> [Fx Fy Fz Mx My Mz] (N, N*m)",
        "rmse": dict(zip(AXES, rmse.tolist())),
        "loo_median_abs": dict(zip(AXES, med.tolist())),
        "warnings": ["Fz column fit from flat poses only (2-param shared-normal model); "
                     "accuracy under combined shear+normal loads unverified. "
                     "Normal channels have a dead zone below ~100g."],
    }
    out_path = Path("coinft_calib.json")
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n标定矩阵 -> {out_path.resolve()}")


if __name__ == "__main__":
    main()
