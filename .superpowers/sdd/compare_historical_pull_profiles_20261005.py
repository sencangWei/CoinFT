"""Read-only old/current profile replay on saved actual page coordinates."""
import hashlib
import json
import statistics
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / '.superpowers/sdd'
production = ROOT / 'demo_web/shear_demo_profile.json'
original = production.read_bytes()
current = json.loads(original)
old = json.loads(json.loads((HERE / 'shear-refit-original-profile-20261005.json').read_text(encoding='utf-8'))['original_text'])
assert old == json.loads((ROOT / 'tests/fixtures/shear_demo_profile_20260925.json').read_text(encoding='utf-8'))
names = [
    'shear-live-page-minus-x-20261005.json',
    'shear-live-page-plus-x-20261005.json',
    'shear-live-page-center-same-baseline-20261005.json',
    'shear-live-page-center-pull-minus-x-20261005.json',
    'shear-live-page-edge-pull-minus-x-20261005.json',
    'shear-live-page-center-pull-foreground-20261005.json',
    'shear-center-pull-full-diagnostic-20261005.json',
    'shear-center-pull-controls-empty-20261005.json',
    'shear-center-pull-controls-press-20261005.json',
]
datasets = []
for name in names:
    path = HERE / name
    data = json.loads(path.read_text(encoding='utf-8'))
    if 'observations' in data:
        observations = data['observations']
        first = observations[0]['monotonic']
        rows = [{'ms': (o['monotonic']-first)*1000,
                 'channels': [a-b for a, b in zip(o['page']['channels'], o['page']['baseline'])]}
                for o in observations]
        actual = [o['page']['renderedShear'] for o in observations]
        baseline = observations[0]['page']['baseline']
    else:
        observations = data['samples']
        first = observations[0]['host']
        rows = [{'ms': o['host']-first,
                 'channels': [a-b for a, b in zip(o['before']['channels'], o['before']['baseline'])]}
                for o in observations]
        actual = [o['before']['renderedShear'] for o in observations]
        baseline = observations[0]['before']['baseline']
    datasets.append({'source': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'rows': rows, 'actual_rendered_range': [min(actual), max(actual)], 'baseline': baseline})

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    try:
        page = browser.new_page(reduced_motion='reduce')
        page.set_content('<canvas id="c" style="width:600px;height:400px"></canvas>')
        page.add_script_tag(path=str(ROOT / 'demo_web/surface.js'))
        replay = page.evaluate('''input => {
          let now=0;performance.now=()=>now;
          return input.datasets.map(d=>{
            const results={};
            for(const [name,profile] of Object.entries(input.profiles)){
              const surface=createSurface(document.getElementById('c')), rows=[];
              for(const r of d.rows){
                now=r.ms;surface.set(r.channels,profile);
                rows.push({ms:now,score:shearScore(r.channels,profile),normal:surface.target,shear:surface.shearTarget});
              }
              results[name]=rows;
            }
            return {source:d.source,results};
          });
        }''', {'datasets': datasets, 'profiles': {'old': old, 'current': current}})
    finally:
        browser.close()

def stats(values):
    return {'min': min(values), 'median': statistics.median(values), 'max': max(values)}

results = []
for data, replayed in zip(datasets, replay):
    summary = {}
    for name, rows in replayed['results'].items():
        stable = [v for v in rows if v['ms'] >= 600]
        summary[name] = {
            'stable_samples': len(stable), 'right_active': sum(v['shear'] >= .2 for v in stable),
            'left_active': sum(v['shear'] <= -.2 for v in stable),
            'nonzero': sum(abs(v['shear']) > .05 for v in stable),
            'score': stats([v['score'] for v in stable]), 'shear': stats([v['shear'] for v in stable]),
        }
    results.append({k: v for k, v in data.items() if k != 'rows'} | {
        'replay': summary, 'normal_identical': all(a['normal'] == b['normal'] for a, b in
                                                 zip(replayed['results']['old'], replayed['results']['current']))})
assert production.read_bytes() == original
print(json.dumps({
    'scope': 'Read-only historical-profile comparison on identical captured page-coordinate inputs, unchanged current surface.js, cold start; no fitting/deployment/new hardware capture',
    'profile_sha256': hashlib.sha256(original).hexdigest(),
    'pressure_projection_coefficient': {name: sum(w*l for w, l in zip(p['shear']['weights'], p['shear']['pressLeak']))
                                        for name, p in [('old', old), ('current', current)]},
    'results': results,
    'limitations': [
        'Historical operator observations are distinct from offline numerical replay.',
        'Earlier short pull record has numerical shear but operator reported no visible deformation.',
        'Separate windows retain their actual distinct baselines; not merged for fitting.',
        'No archived pre-refit center-pull labeled capture identified; user historical observation preserved.',
        'Replay has no captured filter prehistory and cannot prove live causation.',
    ],
}, ensure_ascii=False, allow_nan=False))
