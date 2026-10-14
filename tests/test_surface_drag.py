"""Real Canvas geometry regressions for the qualitative local shear drawing."""

import math
import unittest
from pathlib import Path

from playwright.sync_api import sync_playwright


PROFILE = {
    "version": 1, "mode": "qualitative",
    "normal": {"threshold": 100, "span": 600},
    "shear": {"enabled": True, "weights": [.125] * 4 + [-.125] * 4,
              "pressLeak": [0] * 8, "threshold": 20, "span": 80},
}


def vertex(cells, i, j):
    col, row = min(i, 17), min(j, 17)
    corner = 0 if i < 18 and j < 18 else 1 if j < 18 else 3 if i < 18 else 2
    return cells[row * 18 + col][corner]


def area(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def material_geometry(cells, p, s, width=600, height=400):
    """Remove specified height from captured vertices, then invert the camera."""
    material = {}
    for i in range(19):
        for j in range(19):
            u, v = i / 9 - 1, j / 9 - 1
            envelope = ((1-u*u)*(1-v*v))**2
            bump = math.exp(-((u-.19*s)**2+(v+.19*s)**2)/.18)
            z = bump*p + .19*s*(u-v)*envelope
            x, y = vertex(cells, i, j)
            difference = (x / width - .5) / .23
            total = (y / height - .34 - z*.17) / .105
            material[i, j] = ((total+difference)/2, (total-difference)/2)
    return material


def material_quality(material):
    areas = []
    for i in range(18):
        for j in range(18):
            cell = [material[i,j], material[i+1,j], material[i+1,j+1], material[i,j+1]]
            areas.extend(area(*(cell[k] for k in corners))
                         for corners in ((0,1,2), (0,2,3)))
    segments = [((i,j), (i+1,j)) for i in range(18) for j in range(19)]
    segments += [((i,j), (i,j+1)) for i in range(19) for j in range(18)]
    intersections = 0

    def on_segment(a, b, point):
        return (abs(area(a, b, point)) <= 1e-12 and
                min(a[0], b[0]) - 1e-12 <= point[0] <= max(a[0], b[0]) + 1e-12 and
                min(a[1], b[1]) - 1e-12 <= point[1] <= max(a[1], b[1]) + 1e-12)

    for index, (ak, bk) in enumerate(segments):
        a, b = material[ak], material[bk]
        for ck, dk in segments[index+1:]:
            if ak in (ck, dk) or bk in (ck, dk):
                continue
            c, d = material[ck], material[dk]
            proper = (area(a,b,c)*area(a,b,d) < -1e-12 and
                      area(c,d,a)*area(c,d,b) < -1e-12)
            if proper or any((on_segment(a,b,c), on_segment(a,b,d),
                              on_segment(c,d,a), on_segment(c,d,b))):
                intersections += 1
    return areas, intersections


class SurfaceDragTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page(reduced_motion="reduce")
        self.page.set_content('<canvas id="test-canvas" style="width:600px;height:400px"></canvas>')
        self.page.add_script_tag(path=str(Path(__file__).resolve().parents[1] / "demo_web/surface.js"))
        self.page.evaluate("""() => {
            const canvas = document.getElementById('test-canvas');
            const ctx = canvas.getContext('2d');
            window.drawnCells = []; window.drawnColors = [];
            let points = [];
            const begin = ctx.beginPath.bind(ctx), move = ctx.moveTo.bind(ctx);
            const line = ctx.lineTo.bind(ctx), stroke = ctx.stroke.bind(ctx);
            ctx.beginPath = () => { points = []; begin(); };
            ctx.moveTo = (x,y) => { points.push([x,y]); move(x,y); };
            ctx.lineTo = (x,y) => { points.push([x,y]); line(x,y); };
            ctx.stroke = () => {
                drawnCells.push(points.map(p => [...p]));
                drawnColors.push(ctx.fillStyle); stroke();
            };
            window.dragView = createSurface(canvas);
        }""")
        self.flat = self.snapshot()

    def tearDown(self):
        self.page.close()

    def snapshot(self):
        return self.page.evaluate("""() => ({cells: drawnCells, colors: drawnColors,
            pixels: document.getElementById('test-canvas').toDataURL(),
            levels: [dragView.level, dragView.shearLevel]})""")

    def draw(self, p=0, s=0):
        channels = [s * 100] * 4 + [-s * 100] * 4 + [p * 700] * 4
        self.page.evaluate("""args => {
            dragView.clear();
            drawnCells = []; drawnColors = []; dragView.set(args.channels, args.profile);
        }""", {"channels": channels, "profile": PROFILE})
        state = self.snapshot()
        self.assertEqual(state["levels"], [p, s])
        self.assertEqual(len(state["cells"]), 324)
        return state

    def test_shear_keeps_outer_boundary_fixed_and_localizes_displacement(self):
        right = self.draw(s=1)["cells"]
        for i in range(19):
            for j in range(19):
                if i in (0, 18) or j in (0, 18):
                    self.assertEqual(vertex(right, i, j), vertex(self.flat["cells"], i, j))
        center = vertex(right, 9, 9)[0] - vertex(self.flat["cells"], 9, 9)[0]
        near_edge = vertex(right, 1, 9)[0] - vertex(self.flat["cells"], 1, 9)[0]
        self.assertGreater(center, 100)
        self.assertLess(abs(near_edge), center * .1)

    def test_shear_bends_a_material_grid_line(self):
        right = self.draw(s=1)["cells"]
        points = [vertex(right, i, 9) for i in (3, 9, 15)]
        self.assertGreater(abs(area(*points)), 100)

    def test_left_and_right_are_mirrored_including_combined_pressure(self):
        for p in (0, 1):
            right, left = self.draw(p, 1)["cells"], self.draw(p, -1)["cells"]
            for i in range(19):
                for j in range(19):
                    a, b = vertex(right, i, j), vertex(left, j, i)
                    self.assertAlmostEqual(a[0] + b[0], 600)
                    self.assertAlmostEqual(a[1], b[1])

    def test_full_scale_material_cells_do_not_fold_or_intersect(self):
        for p in (0, 1):
            for s in (-1, 0, 1):
                cells = self.draw(p, s)["cells"]
                areas, intersections = material_quality(material_geometry(cells, p, s))
                self.assertEqual(len(areas), 648)
                self.assertGreater(min(areas), 0, f"p={p}, s={s}")
                self.assertEqual(intersections, 0, f"p={p}, s={s}")

    def test_material_checks_detect_test_side_inversion_and_crossing(self):
        cells = self.flat["cells"]
        material = material_geometry(cells, 0, 0)
        material[9, 9] = material[11, 9]
        areas, intersections = material_quality(material)
        self.assertLess(min(areas), 0)
        self.assertGreater(intersections, 0)

    def test_shear_has_local_color_and_clear_restores_exact_pixels(self):
        right = self.draw(s=1)
        self.assertGreater(len(set(right["colors"])), 3)
        self.assertNotEqual(right["colors"][9 * 18 + 9], right["colors"][0])
        self.page.evaluate("drawnCells = []; drawnColors = []; dragView.clear()")
        self.assertEqual(self.snapshot(), self.flat)

    def test_pressure_preserves_original_shape_and_resize(self):
        normal = self.draw(p=1)
        for i in range(19):
            for j in range(19):
                u, v = i / 9 - 1, j / 9 - 1
                x, y = vertex(normal["cells"], i, j)
                self.assertAlmostEqual(x, 600 * (.5 + (u - v) * .23))
                self.assertAlmostEqual(y, 400 * (.34 + (u + v) * .105 +
                                               math.exp(-(u*u + v*v) / .18) * .17))
        self.assertEqual(vertex(normal["cells"], 9, 9), [300, 204])
        self.page.evaluate("""() => {
            document.getElementById('test-canvas').style.width = '300px';
            drawnCells = []; drawnColors = []; dragView.resize();
        }""")
        resized = self.snapshot()
        self.assertEqual(resized["levels"], [1, 0])
        for a, b in zip(normal["cells"], resized["cells"]):
            for old, new in zip(a, b):
                self.assertAlmostEqual(old[0] / 2, new[0])
                self.assertAlmostEqual(old[1], new[1])
