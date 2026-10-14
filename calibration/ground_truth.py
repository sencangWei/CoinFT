"""Ground-truth 6-axis F/T computation for DIY CoinFT calibration poses.

Sensor frame: origin at center of the top sensing surface, +Z up.
World gravity acts along -Z. For a tilted sensor, F_sensor = R^T @ F_world
where R is the sensor->world rotation of the tilt.

All forces in N, moments in N*m, positions converted mm -> m.
"""
import math

G = 9.80665

PULL_DIRS = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0)}


def ground_truth(pose):
    """pose: dict from poses.csv row. Returns (F, M) as 3-tuples in sensor frame."""
    t = pose["type"]
    m = float(pose["mass_g"]) / 1000.0  # kg
    W = m * G

    if t == "flat":
        return (0.0, 0.0, -W), (0.0, 0.0, 0.0)

    if t in ("tilt_x", "tilt_y"):
        phi = math.radians(float(pose["angle_deg"]))
        c, s = math.cos(phi), math.sin(phi)
        if t == "tilt_x":
            # 约定(与 tilt_y 一致): +Y 箭头指下坡为正角, 重力沿 +Y 分量 = +W·sinφ
            f = (0.0, W * s, -W * c)
        else:
            # R_y(phi)^T @ (0,0,-W)
            f = (W * s, 0.0, -W * c)
        return f, (0.0, 0.0, 0.0)  # weight still centered -> no moment

    if t == "offset":
        x = float(pose["x_mm"]) / 1000.0
        y = float(pose["y_mm"]) / 1000.0
        # r=(x,y,0), F=(0,0,-W) -> M = r x F = (-y*W, x*W, 0)
        return (0.0, 0.0, -W), (-y * W, x * W, 0.0)

    if t == "spool":
        r_d = float(pose["radius_mm"]) / 1000.0
        d = PULL_DIRS[pose["pull_dir"]]
        # tension T=W along pull_dir; string tangent to drum -> pure couple
        # about Z plus shear along pull_dir.
        sgn = 1.0 if pose["wrap"] == "cw" else -1.0
        # 绕线轮+线自重 4g(实测54-50), 粘在板面正中 -> 恒定小Fz, 不产生力矩
        drum_w = 4.0 / 1000.0 * G
        f = (W * d[0], W * d[1], -drum_w)
        # Mz sign: cw wrap pulled toward +x applies +Mz when string leaves the
        # drum at the top (-y side)... defined empirically: verify sign with
        # one known pose during fitting QA; magnitude is exact.
        m = (0.0, 0.0, sgn * W * r_d)
        return f, m

    raise ValueError(f"unknown pose type {t!r}")
