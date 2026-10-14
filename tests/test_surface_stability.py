"""Deterministic Chromium checks of qualitative signal lifecycle."""
import math
import json
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright


class SurfaceStabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.page = self.browser.new_page(reduced_motion="reduce")
        self.page.set_content('<canvas id="c" style="width:600px;height:400px"></canvas>')
        self.page.add_script_tag(path=str(Path(__file__).resolve().parents[1] / 'demo_web/surface.js'))
        self.page.evaluate("""() => {
          window.now = 0; performance.now = () => now;
          window.profile = {version:1, mode:'qualitative', normal:{threshold:100,span:600},
            shear:{enabled:true,weights:[.125,.125,.125,.125,-.125,-.125,-.125,-.125],
              pressLeak:Array(8).fill(0),threshold:100,span:200}};
          window.view = createSurface(document.getElementById('c'));
        }""")

    def tearDown(self):
        self.page.close()

    def update(self, score, dt=100, pressure=0):
        return self.page.evaluate("""a => {
          now += a.dt; view.set(Array(4).fill(a.score).concat(Array(4).fill(-a.score),
            Array(4).fill(a.pressure)),profile);
          return [view.target,view.shearTarget];
        }""", dict(score=score, dt=dt, pressure=pressure))

    def test_exact_gain_smoothing_and_same_sign_continuation(self):
        self.assertEqual(self.update(80, pressure=700), [1, 0])
        self.page.evaluate('view.clear()')
        self.assertAlmostEqual(self.update(120)[1], 60/170)
        filtered = 80 + 40 * math.exp(-100/180)
        self.assertAlmostEqual(self.update(80)[1], (filtered-60)/170)
        for _ in range(20):
            continued = self.update(80)[1]
        self.assertGreater(continued, 0)
        for _ in range(20):
            reversed_below_start = self.update(-80)[1]
        self.assertEqual(reversed_below_start, 0)

    def test_release_reversal_clipping_and_combined_pressure(self):
        self.assertEqual(self.update(230, pressure=700), [1, 1])
        for _ in range(6):
            released = self.update(0, pressure=700)
        self.assertEqual(released, [1, 0])
        self.page.evaluate('view.clear()')
        self.update(230)
        targets = [self.update(-230)[1] for _ in range(6)]
        self.assertLess(targets[-1], 0)
        self.assertTrue(all(-1 <= x <= 1 for x in targets))
        self.page.evaluate('view.clear()')
        self.assertEqual(self.update(-10000)[1], -1)

    def test_threshold_chatter_keeps_same_sign_active(self):
        self.update(120)
        self.assertGreater(self.update(80)[1], 0)

    def test_resets_clear_fault_disabled_identity_and_mode(self):
        resets = ['view.clear()', 'view.set([NaN],profile)',
                  'profile.shear.enabled=false; view.set(Array(12).fill(0),profile); profile.shear.enabled=true',
                  'profile={...profile}; view.set(Array(12).fill(0),profile)',
                  'profile.mode="strict"; view.set(Array(12).fill(0),profile); profile.mode="qualitative"',
                  'profile.normal.span=0; view.set(Array(12).fill(0),profile); profile.normal.span=600',
                  'profile.version=2; view.set(Array(12).fill(0),profile); profile.version=1']
        for reset in resets:
            self.page.evaluate('view.clear()')
            self.update(230)
            self.page.evaluate(reset)
            self.assertEqual(self.update(80)[1], 0, reset)

    def test_strict_helpers_and_instance_isolation(self):
        self.page.evaluate('profile.mode="strict"')
        self.assertAlmostEqual(self.update(120)[1], .1)
        self.assertAlmostEqual(self.update(80)[1], .05)
        self.assertAlmostEqual(self.update(-80)[1], -.05)
        self.assertEqual(self.update(0)[1], 0)
        self.page.evaluate('profile.mode="qualitative"; view.clear()')
        self.update(230)
        other = self.page.evaluate("""() => {const other=createSurface(document.getElementById('c'));
          other.set(Array(4).fill(80).concat(Array(4).fill(-80),Array(4).fill(0)),profile);
          return other.shearTarget;}""")
        self.assertEqual(other, 0)

    def test_synthetic_chatter_variation_and_motion_preference(self):
        scores = [120, 80]*22 + [120]
        old = [max(0, (s-100)/200) for s in scores]
        targets = [self.update(s)[1] for s in scores]
        variation = lambda values: sum(abs(b-a) for a,b in zip(values, values[1:]))
        self.assertLess(sum(v == 0 for v in targets), 24)
        self.assertLess(variation(targets), variation(old))
        self.page.emulate_media(reduced_motion="no-preference")
        self.page.evaluate('view.clear()')
        self.assertAlmostEqual(self.update(120)[1], 60/170)
        self.page.evaluate('view.clear()')
        self.assertEqual(self.page.evaluate('[view.target,view.shearTarget,view.level,view.shearLevel]'), [0]*4)

    def test_extreme_display_score_releases_and_reverses_within_600ms(self):
        root = Path(__file__).resolve().parents[1]
        real = json.loads((root / 'demo_web/shear_demo_profile.json').read_text())
        for template in (None, real):
            if template:
                self.page.evaluate('p => {profile=p; view.clear();}', template)
            result = self.page.evaluate("""() => {
              const channels=score=>{const w=profile.shear.weights;
                const mean=w.reduce((a,b)=>a+b,0)/8;
                const norm=w.reduce((sum,v)=>sum+(v-mean)**2,0);
                return w.map(v=>(v-mean)*score/norm).concat(Array(4).fill(0));};
              const set=score=>{now+=100; view.set(channels(score),profile); return view.shearTarget;};
              view.clear(); const held=set(10000);
              const release=Array.from({length:6},()=>set(0));
              view.clear(); set(10000);
              const reverse=Array.from({length:6},()=>set(-10000));
              return {held,release,reverse};
            }""")
            self.assertEqual(result['held'], 1)
            with self.subTest(template='real' if template else 'synthetic', behavior='release'):
                self.assertEqual(result['release'][-1], 0)
            self.assertLess(result['reverse'][-1], 0)
            self.assertTrue(all(-1 <= x <= 1 for x in result['release']+result['reverse']))

    def test_exact_bounded_score_irregular_and_zero_elapsed_ema(self):
        self.assertEqual(self.update(10000)[1], 1)
        self.assertEqual(self.update(-10000, dt=0)[1], 1)
        expected = 230 * math.exp(-37/180)
        self.assertAlmostEqual(self.update(0, dt=37)[1], (expected-60)/170)
        expected += (150-expected)*(1-math.exp(-211/180))
        self.assertAlmostEqual(self.update(150, dt=211)[1], (expected-60)/170)

    def test_real_capture_replay_reduces_zero_windows_and_variation(self):
        root = Path(__file__).resolve().parents[1]
        capture = json.loads((root / '.superpowers/sdd/combined_press_minusx_retry_20260926.json').read_text())
        profile = json.loads((root / 'tests/fixtures/shear_demo_profile_20260925.json').read_text(encoding='utf-8'))
        result = self.page.evaluate("""a => {
          profile=a.profile; view.clear();
          const old=[], current=[], normals=[];
          for (const sample of a.capture.samples) {
            now=sample.elapsed*1000;
            const channels=sample.channels.map((v,i)=>v-a.capture.baseline[i]);
            old.push(shearLevel(channels,profile));
            view.set(channels,profile); current.push(view.shearTarget); normals.push(view.target);
          }
          const stats=values=>({zero:values.filter(v=>v===0).length,
            variation:values.slice(1).reduce((sum,v,i)=>sum+Math.abs(v-values[i]),0)});
          return {old:stats(old),current:stats(current),normals};
        }""", dict(capture=capture, profile=profile))
        self.assertEqual(result['old']['zero'], 24)
        self.assertLess(result['current']['zero'], 24)
        self.assertLess(result['current']['variation'], result['old']['variation'])
        self.assertEqual(result['normals'], [1]*45)
        print('CAPTURE_REPLAY', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
