"""Replay captured center-pull page coordinates; never fit or install parameters."""
import hashlib
import json
import statistics
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / '.superpowers/sdd'
source = HERE / 'shear-center-pull-full-diagnostic-20261005.json'
data = json.loads(source.read_text(encoding='utf-8'))
proposal = json.loads((HERE / 'shear-pull-compensation-proposed-candidate-20261005.json').read_text(encoding='utf-8'))
installed_bytes = (ROOT / 'demo_web/shear_demo_profile.json').read_bytes()
installed = json.loads(installed_bytes)
assert hashlib.sha256(installed_bytes).hexdigest() == proposal['installed_profile_sha256']
assert data['capture_ok'] and data['page_before']['profile'] == installed
rows = []
for obs in data['observations']:
    page = obs['page']
    assert page['baseline'] == data['page_before']['baseline'] and not page['paused']
    delta = [v-b for v, b in zip(page['channels'], page['baseline'])]
    normal = max(0, statistics.median(delta[8:]))
    avg = statistics.mean(delta[:8])
    raw_projection = sum(w*(v-avg) for w, v in zip(installed['shear']['weights'], delta[:8]))
    correction = sum(w*p*normal for w, p in zip(installed['shear']['weights'], installed['shear']['pressLeak']))
    assert abs(raw_projection-correction-page['score']) < 1e-8
    rows.append({'ms': (obs['monotonic']-data['observations'][0]['monotonic'])*1000,
        'frame': page['frame'], 'channels': delta, 'normalScore': normal,
        'uncompensatedProjection': raw_projection, 'pressureCorrection': correction,
        'score': page['score'], 'actualTarget': page['shear'], 'actualRendered': page['renderedShear']})

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    try:
        page = browser.new_page(reduced_motion='reduce')
        page.set_content('<canvas id="c" style="width:600px;height:400px"></canvas>')
        page.add_script_tag(path=str(ROOT / 'demo_web/surface.js'))
        replays = page.evaluate('''input => {
          let now=0;performance.now=()=>now;
          const results=[];
          for (const [label,profile] of Object.entries(input.profiles)) {
            const surface=createSurface(document.getElementById('c')), rows=[];
            for (const sample of input.rows) {
              now=sample.ms;surface.set(sample.channels,profile);
              rows.push({ms:now,normal:surface.target,shear:surface.shearTarget,score:shearScore(sample.channels,profile)});
            }
            results.push({label,rows});
          }
          return results;
        }''', {'rows': rows, 'profiles': {'installed': installed, 'proposed_3_percent': proposal['candidate']}})
    finally:
        browser.close()

def summary(values):
    return {'min': min(values), 'median': statistics.median(values), 'max': max(values)}

for result in replays:
    stable = [r for r in result['rows'] if r['ms'] >= 600]
    result['summary'] = {'count': len(stable), 'score': summary([r['score'] for r in stable]),
        'shear': summary([r['shear'] for r in stable]),
        'rightActive': sum(r['shear'] >= .2 for r in stable),
        'reversed': sum(r['shear'] < -.05 for r in stable),
        'normalUnchanged': all(a['normal'] == b['page']['normal'] for a,b in zip(result['rows'], data['observations']))}
assert (ROOT / 'demo_web/shear_demo_profile.json').read_bytes() == installed_bytes
report = {'scope': 'one confirmed center-pull diagnosis only; not fitting, deployment or full acceptance',
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'profile_sha256': hashlib.sha256(installed_bytes).hexdigest(),
    'candidate_installed': False, 'baseline': data['page_before']['baseline'],
    'component_statistics': {k: summary([r[k] for r in rows]) for k in
        ['normalScore', 'uncompensatedProjection', 'pressureCorrection', 'score', 'actualTarget', 'actualRendered']},
    'replays': replays,
    'limitations': ['No reference force; cannot identify physical force composition or hardware defect.',
        'Page filter prehistory before capture is not recorded; replay uses an explicit cold start.',
        '3 percent candidate was selected on earlier short records at a different page basis.',
        'Force application and baseline differences are not isolated by this single loading action.']}
print(json.dumps(report,ensure_ascii=False,allow_nan=False),flush=True)
