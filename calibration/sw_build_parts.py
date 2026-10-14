"""Build the CoinFT DIY calibration kit v2 in SolidWorks via COM (late binding).

v2 changes (user feedback):
  - spool drum much smaller: drum D20 x 10 + flange D24 x 2, plus a D1.5 radial
    tie hole through the drum at mid height to knot the fishing line.
  - wedges: stop wall REMOVED (it would shunt force at high angles). Sensor is
    instead screwed onto the slope with 4 x M2 self-tapping screws using the
    official hole pattern extracted from CFT_V2_Top Gerber drill file
    (Top_V3.TXT, 4 x D2.0 plated holes). Weights go on the sensor top with
    foam tape.
  - wedge_60 dropped (low angles suffice, matrix extrapolates).

Hole pattern (mm, relative to board center, Gerber top view):
  h1(-9.121, -10.497)  h2(11.887, -6.877)  h3(7.460, 10.502)  h4(-10.741, 7.391)
Pattern X runs along the slope, Y across the width. Pilot holes D1.7 for M2
self-tappers, cut normal to the slope, through the whole wedge body.

All SW API units are meters. STLs (trimesh, same numbers) are the print files.
"""
import math
import os
import time

import numpy as np
import pythoncom
import trimesh
import win32com.client

NOCALLOUT = None  # main() 里初始化为 VARIANT(VT_DISPATCH, None)；SelectByID2 第 8 参必须用这个

OUT = r"D:\semg.claude\coinft\calibration\parts"
TPL = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2023\templates\gb_part.prtdot"
MM = 0.001

# ---- spool drum ----
DRUM_R = 10 * MM       # 鼓半径 r=10mm -> poses.csv radius_mm 占位值同步改
DRUM_H = 10 * MM
FLANGE_R = 12 * MM     # 法兰仅作热熔胶粘接面
FLANGE_H = 2 * MM
TIE_R = 0.75 * MM      # Ø1.5 穿线孔
TIE_H = 7 * MM         # 孔轴高度（距法兰底面）

# ---- wedge ----
WEDGE_L = 70 * MM      # 斜面水平投影长
WEDGE_FLOOR = 3 * MM   # 低端厚度
WEDGE_W = 60 * MM      # 宽度(Z)
WEDGE_ANGLES = (15, 30, 45)

# ---- CoinFT 官方安装孔位（mm，相对板中心）----
HOLES_MM = [(-9.121, -10.497), (11.887, -6.877),
            (7.460, 10.502), (-10.741, 7.391)]
HOLE_R = 0.85 * MM     # Ø1.7 M2 自攻底孔


def connect():
    pythoncom.CoInitialize()
    try:
        sw = win32com.client.GetActiveObject("SldWorks.Application")
    except Exception:
        sw = win32com.client.DispatchEx("SldWorks.Application")
    sw.Visible = True
    # 清掉之前崩溃运行留下的未保存零件（只关未命名的新零件）
    while True:
        doc = sw.ActiveDoc
        if doc is None:
            break
        if doc.GetPathName:
            break
        sw.CloseDoc(doc.GetTitle)
    return sw


def planes(doc):
    """Feature-tree order: Front, Top, Right (language-independent)."""
    names = []
    feat = doc.FirstFeature
    while True:
        try:
            t = feat.GetTypeName2
        except Exception:
            break
        if t == "RefPlane":
            names.append(feat.Name)
        feat = feat.GetNextFeature
    assert len(names) >= 3, f"基准面数量异常: {names}"
    return names[0], names[1], names[2]


def select_last_sketch(doc):
    name = doc.FeatureByPositionReverse(0).Name
    doc.ClearSelection2(True)
    ok = doc.Extension.SelectByID2(name, "SKETCH", 0, 0, 0, False, 0, NOCALLOUT, 0)
    assert ok, f"选草图 {name} 失败"


def extrude(doc, depth, merge=True):
    feat = doc.FeatureManager.FeatureExtrusion3(
        True, False, False, 0, 0, depth, 0,
        False, False, False, False, 0.0, 0.0,
        False, False, False, False,
        merge, True, True, 0, 0, False)
    assert feat is not None, "拉伸失败"
    return feat


def cut_midplane(doc, width):
    """Cut-extrude, mid-plane end condition (T1=6), total width `width` (m).
    FeatureCut3 exact 26-arg signature read from sldworks.tlb."""
    feat = doc.FeatureManager.FeatureCut3(
        True, False, False, 6, 0, width, 0.0,          # Sd Flip Dir T1 T2 D1 D2
        False, False, False, False, 0.0, 0.0,          # Dchk1 Dchk2 Ddir1 Ddir2 Dang1 Dang2
        False, False, False, False,                    # OffsetRev1/2 TranslateSurf1/2
        False,                                         # NormalCut
        True, True, True, False, False,                # UseFeatScope UseAutoSelect AsmScope AutoSelComp Propagate
        0, 0.0, False)                                 # T0 StartOffset FlipStartOffset
    assert feat is not None, "切除失败"
    return feat


def sketch_circle_on_plane(doc, plane, radius, x=0.0, y=0.0):
    doc.ClearSelection2(True)
    assert doc.Extension.SelectByID2(plane, "PLANE", 0, 0, 0, False, 0, NOCALLOUT, 0), "选平面失败"
    doc.SketchManager.InsertSketch(True)
    doc.SketchManager.CreateCircleByRadius(x, y, 0, radius)
    doc.SketchManager.InsertSketch(True)


def sketch_circle_on_face(doc, xyz, radius):
    doc.ClearSelection2(True)
    ok = doc.Extension.SelectByID2("", "FACE", xyz[0], xyz[1], xyz[2], False, 0, NOCALLOUT, 0)
    assert ok, "选面失败"
    doc.SketchManager.InsertSketch(True)
    doc.SketchManager.CreateCircleByRadius(0, 0, 0, radius)
    doc.SketchManager.InsertSketch(True)


def sketch_polygon_on_plane(doc, plane, pts_xy):
    doc.ClearSelection2(True)
    assert doc.Extension.SelectByID2(plane, "PLANE", 0, 0, 0, False, 0, NOCALLOUT, 0), "选平面失败"
    doc.SketchManager.InsertSketch(True)
    n = len(pts_xy)
    for i in range(n):
        x1, y1 = pts_xy[i]
        x2, y2 = pts_xy[(i + 1) % n]
        doc.SketchManager.CreateLine(x1, y1, 0, x2, y2, 0)
    doc.SketchManager.InsertSketch(True)


def holes_on_slope_sw(doc, deg):
    """在斜面上按官方孔位切 4 个 Ø1.7 底孔（法向贯穿）。"""
    theta = math.radians(deg)
    H = WEDGE_FLOOR + WEDGE_L * math.tan(theta)
    cx, cy = WEDGE_L / 2, (WEDGE_FLOOR + H) / 2  # 斜面中心(模型 XY)
    ux, uy = math.cos(theta), math.sin(theta)    # 沿斜面向上单位向量
    # 选斜面建草图
    doc.ClearSelection2(True)
    ok = doc.Extension.SelectByID2("", "FACE", cx, cy, WEDGE_W / 2, False, 0, NOCALLOUT, 0)
    assert ok, "选斜面失败"
    doc.SketchManager.InsertSketch(True)
    sk = doc.SketchManager.ActiveSketch
    data = sk.ModelToSketchTransform.ArrayData  # 16 doubles
    # 实测: ArrayData 的 3x3 需要转置后用, 即 v_sketch = R^T v_model + t
    R = [data[0:3], data[3:6], data[6:9]]
    t, scale = data[9:12], data[12]

    def to_sketch(px, py, pz):
        v = [px, py, pz]
        return [scale * sum(R[j][i] * v[j] for j in range(3)) + t[i] for i in range(3)]

    for hx_mm, hy_mm in HOLES_MM:
        hx, hy = hx_mm * MM, hy_mm * MM
        # 模型空间孔位: 斜面中心 + hx 沿斜面 + hy 沿宽度(Z)
        p = (cx + hx * ux, cy + hx * uy, WEDGE_W / 2 + hy)
        s = to_sketch(*p)
        doc.SketchManager.CreateCircleByRadius(s[0], s[1], 0.0, HOLE_R)
    doc.SketchManager.InsertSketch(True)
    select_last_sketch(doc)
    cut_midplane(doc, 0.06)


def volume_mm3(doc):
    mp = doc.Extension.CreateMassProperty
    return mp.Volume * 1e9


def save_close(sw, doc, path):
    doc.EditRebuild3
    if os.path.exists(path):
        os.remove(path)
    # SaveAs3 的返回值在这台机器上不可靠（报 False/1 但文件其实写好了），
    # 以文件实际存在且非空为准。
    try:
        doc.SaveAs3(path, 0, 1)
    except Exception:
        pass
    for _ in range(20):
        if os.path.exists(path) and os.path.getsize(path) > 0:
            break
        time.sleep(0.5)
    if not (os.path.exists(path) and os.path.getsize(path) > 0):
        no_disp = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
        err = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        warn = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        doc.Extension.SaveAs(path, 0, 1, no_disp, err, warn)
        for _ in range(20):
            if os.path.exists(path) and os.path.getsize(path) > 0:
                break
            time.sleep(0.5)
    assert os.path.exists(path) and os.path.getsize(path) > 0, f"保存失败: {path}"
    print("saved:", path)
    sw.CloseDoc(doc.GetTitle)


# ---------------- STL builders (same numbers, mm) ----------------

def stl_drum(path):
    z0 = FLANGE_H * 1000
    flange = trimesh.creation.cylinder(radius=FLANGE_R * 1000, height=FLANGE_H * 1000, sections=128)
    flange.apply_translation([0, 0, FLANGE_H * 1000 / 2])
    drum = trimesh.creation.cylinder(radius=DRUM_R * 1000, height=DRUM_H * 1000, sections=128)
    drum.apply_translation([0, 0, z0 + DRUM_H * 1000 / 2])
    body = trimesh.util.concatenate([flange, drum])
    # 穿线孔: 沿 X 轴, 高 TIE_H, 长度需穿透鼓身(直径 2*DRUM_R)
    hole = trimesh.creation.cylinder(radius=TIE_R * 1000, height=DRUM_R * 1000 * 2.4, sections=32)
    hole.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
    hole.apply_translation([0, 0, TIE_H * 1000])
    trimesh.boolean.difference([body, hole], engine="manifold").export(path)


def wedge_profile(deg):
    H = WEDGE_FLOOR + WEDGE_L * math.tan(math.radians(deg))
    return [(0, 0), (WEDGE_L, 0), (WEDGE_L, H), (0, WEDGE_FLOOR)]


def stl_wedge(deg, path):
    pts = wedge_profile(deg)
    tris = [(0, i, i + 1) for i in range(1, len(pts) - 1)]
    n = len(pts)
    verts = [[x, y, 0] for x, y in pts] + [[x, y, WEDGE_W] for x, y in pts]
    faces = list(tris) + [(a + n, c + n, b + n) for (a, b, c) in tris]
    for i in range(n):
        j = (i + 1) % n
        faces += [(i, j, j + n), (i, j + n, i + n)]
    body = trimesh.Trimesh(vertices=np.array(verts) * 1000, faces=np.array(faces))
    body.fix_normals()
    assert body.is_watertight and body.volume > 0
    # 4 个底孔: 轴 = 斜面法向
    theta = math.radians(deg)
    H = WEDGE_FLOOR + WEDGE_L * math.tan(theta)
    cx, cy = WEDGE_L / 2 * 1000, (WEDGE_FLOOR + H) / 2 * 1000
    ux, uy = math.cos(theta), math.sin(theta)
    normal = np.array([-uy, ux, 0.0])
    cutters = []
    for hx, hy in HOLES_MM:
        p = np.array([cx + hx * ux, cy + hx * uy, WEDGE_W / 2 * 1000 + hy])
        cyl = trimesh.creation.cylinder(radius=HOLE_R * 1000, height=40, sections=32)
        M = trimesh.geometry.align_vectors([0, 0, 1], normal)
        cyl.apply_transform(M)
        cyl.apply_translation(p)
        cutters.append(cyl)
    trimesh.boolean.difference([body] + cutters, engine="manifold").export(path)


# ---------------- SW part builders ----------------

def build_drum(sw):
    doc = sw.NewDocument(TPL, 0, 0, 0)
    assert doc is not None, "NewDocument 失败"
    front, top, right = planes(doc)
    sketch_circle_on_plane(doc, top, FLANGE_R)
    select_last_sketch(doc)
    extrude(doc, FLANGE_H)
    sketch_circle_on_face(doc, (0, FLANGE_H, 0), DRUM_R)
    select_last_sketch(doc)
    extrude(doc, DRUM_H)
    # 穿线孔: Front 平面草图, 圆心在 (0, TIE_H), 双向贯穿(沿 Z)
    sketch_circle_on_plane(doc, front, TIE_R, x=0.0, y=TIE_H)
    select_last_sketch(doc)
    cut_midplane(doc, 0.06)
    v = volume_mm3(doc)
    save_close(sw, doc, os.path.join(OUT, "spool_drum.SLDPRT"))
    stl_drum(os.path.join(OUT, "spool_drum.stl"))
    stl_v = trimesh.load(os.path.join(OUT, "spool_drum.stl")).volume
    print(f"spool_drum 体积: SW {v:.0f} vs STL {stl_v:.0f} mm^3")


def build_wedge(sw, deg):
    pts = wedge_profile(deg)
    doc = sw.NewDocument(TPL, 0, 0, 0)
    assert doc is not None
    front, top, right = planes(doc)
    sketch_polygon_on_plane(doc, front, pts)
    select_last_sketch(doc)
    extrude(doc, WEDGE_W)
    holes_on_slope_sw(doc, deg)
    v = volume_mm3(doc)
    save_close(sw, doc, os.path.join(OUT, f"wedge_{deg}.SLDPRT"))
    stl_wedge(deg, os.path.join(OUT, f"wedge_{deg}.stl"))
    stl_v = trimesh.load(os.path.join(OUT, f"wedge_{deg}.stl")).volume
    print(f"wedge_{deg} 体积: SW {v:.0f} vs STL {stl_v:.0f} mm^3")


def main():
    global NOCALLOUT
    NOCALLOUT = win32com.client.VARIANT(pythoncom.VT_DISPATCH, None)
    sw = connect()
    print("SolidWorks", sw.RevisionNumber)
    # 删掉 v1 的 60° 斜块
    for f in ("wedge_60.SLDPRT", "wedge_60.stl"):
        p = os.path.join(OUT, f)
        if os.path.exists(p):
            os.remove(p)
            print("deleted v1:", f)
    build_drum(sw)
    time.sleep(0.5)
    for deg in WEDGE_ANGLES:
        build_wedge(sw, deg)
        time.sleep(0.3)
    print("全部完成 ->", OUT)


if __name__ == "__main__":
    main()
