"""Offline diagnostic only: recorded page coordinates and unchanged production JS."""
import copy
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / '.superpowers/sdd'
PROFILE = ROOT / 'demo_web/shear_demo_profile.json'
profile = json.loads(PROFILE.read_text(encoding='utf-8'))
profile_sha = hashlib.sha256(PROFILE.read_bytes()).hexdigest()
names = [
    'empty', 'minus-x', 'plus-x', 'center-same-baseline',
    'release-after-minus-x', 'release-after-plus-x', 'release-after-center',
    'pull-compare-empty-before', 'center-pull-minus-x', 'center-pull-release',
    'edge-pull-minus-x', 'edge-pull-release', 'center-pull-foreground',
]
records = []

def describe(values):
    return {'min': min(values), 'median': statistics.median(values), 'max': max(values)}

for name in names:
    path = EVIDENCE / f'shear-live-page-{name}-20261005.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    assert not data['errors'] and data['samples']
    rows = []
    for sample in data['samples']:
        before = sample['before']
        assert before['profile'] == profile
        assert before['baseline'] == [-45, -30, -27.5, -23.5, 19, -37, -9, -60.5, -3, 3, 8, -9]
        channels = [v-b for v, b in zip(before['channels'], before['baseline'])]
        assert len(channels) == 12 and all(math.isfinite(v) for v in channels)
        normal = max(0, statistics.median(channels[8:]))
        avg = statistics.mean(channels[:8])
        uncompensated = sum(w*(v-avg) for w, v in zip(profile['shear']['weights'], channels[:8]))
        correction = normal * sum(w*p for w, p in zip(profile['shear']['weights'], profile['shear']['pressLeak']))
        assert math.isclose(uncompensated-correction, sample['pageScore'], abs_tol=1e-8)
        rows.append({'ms': sample['host']-data['samples'][0]['host'], 'channels': channels,
                     'score': sample['pageScore'], 'normal_score': normal,
                     'uncompensated_score': uncompensated, 'pressure_correction': correction,
                     'actual_normal': before['normal'], 'actual_shear': before['shear'],
                     'actual_rendered_shear': before['renderedShear']})
    records.append({'name': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'rows': rows, 'span_ms': rows[-1]['ms'],
                    'recorded': {k: describe([r[k] for r in rows]) for k in
                        ['score', 'normal_score', 'uncompensated_score', 'pressure_correction',
                         'actual_normal', 'actual_shear', 'actual_rendered_shear']}})

thresholds = [profile['shear']['threshold'], 50, 45, 40, 35]
profiles = []
for threshold in thresholds:
    candidate = copy.deepcopy(profile)
    candidate['shear']['threshold'] = threshold
    profiles.append(candidate)

variant_labels = [f'threshold_{t}' for t in thresholds]
if '--leak-sweep' in sys.argv:
    profiles = [copy.deepcopy(profile)]
    variant_labels = ['installed']
    for scale in [.97, .95, .925, .9]:
        candidate = copy.deepcopy(profile)
        candidate['shear']['pressLeak'] = [v*scale for v in profile['shear']['pressLeak']]
        profiles.append(candidate)
        variant_labels.append(f'pressure_compensation_scale_{scale}')

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    try:
        page = browser.new_page(reduced_motion='reduce')
        page.set_content('<canvas id="c" style="width:600px;height:400px"></canvas>')
        page.add_script_tag(path=str(ROOT / 'demo_web/surface.js'))
        replays = page.evaluate('''input => {
          let now=0; performance.now=()=>now;
          const result=[];
          for (const profile of input.profiles) {
            const poses={}; let normalUnchanged=true;
            for (const record of input.records) {
              const surface=createSurface(document.getElementById('c'));
              const rows=[];
              for (const row of record.rows) {
                now=row.ms; surface.set(row.channels,profile);
                normalUnchanged &&= surface.target===row.actual_normal;
                rows.push({ms:now,score:shearScore(row.channels,profile),
                  normal:surface.target,shear:surface.shearTarget});
              }
              poses[record.name]=rows;
            }
            result.push({threshold:profile.shear.threshold,normalUnchanged,poses});
          }
          return result;
        }''', {'profiles': profiles, 'records': records})
    finally:
        browser.close()

for label, replay in zip(variant_labels, replays):
    replay['variant'] = label
    replay['summary'] = {}
    for name, rows in replay['poses'].items():
        stable = [r['shear'] for r in rows if r['ms'] >= 600]
        replay['summary'][name] = {'count': len(stable), 'shear': describe(stable),
            'right_fraction': sum(v >= .2 for v in stable)/len(stable),
            'left_fraction': sum(v <= -.2 for v in stable)/len(stable),
            'false_shear_fraction': sum(abs(v) > .05 for v in stable)/len(stable)}

manifest = json.loads((EVIDENCE / 'stream-recovery-final-manifest.json').read_text(encoding='utf-8'))
protected = []
for entry in manifest['files']:
    path = Path(entry['path'])
    if path == PROFILE:
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    protected.append({'path': str(path), 'sha256': actual, 'unchanged': actual.upper() == entry['sha256'].upper()})
backend_sha = hashlib.sha256((ROOT / 'coinft_demo.py').read_bytes()).hexdigest()
protected.append({'path': str(ROOT / 'coinft_demo.py'), 'sha256': backend_sha,
    'unchanged': backend_sha.upper() == '96EF5BBE88CEB9797686D1E6B1B2473B50360B0A9225E5FAC192CA6DDB913828'})
assert all(p['unchanged'] for p in protected)
assert hashlib.sha256(PROFILE.read_bytes()).hexdigest() == profile_sha
report = {'scope': 'offline diagnosis only; no fit, installation or acceptance',
    'limitations': ['Each record is a short sampled window, not >=40 snapshots/5 seconds.',
                    'Cold-start replay does not reconstruct unrecorded live filter history.',
                    'Different contact locations have no matched reference force.',
                    'Same page baseline does not prove uninterrupted streaming between records.'],
    'profile_sha256': profile_sha, 'profile_unchanged': True, 'protected': protected,
    'records': records, 'threshold_sweeps': replays,
    'profile_variants': dict(zip(variant_labels, profiles))}

# These previously independent windows are now historical regressions, not new acceptance.
sys.path.insert(0, str(ROOT))
from calibration.shear_refit_replay import KEYS, replay, passes
frozen = json.loads((EVIDENCE / 'shear-refit-fresh-right-20261005.json').read_text(encoding='utf-8'))
validation = json.loads((EVIDENCE / 'shear-frozen-independent-validation-20261005.json').read_text(encoding='utf-8'))
windows, sources = {}, {}
for key in KEYS:
    path = ROOT / 'calibration/shear_frozen_validation_20261005' / f'{key}.json'
    contents = path.read_bytes()
    sha = hashlib.sha256(contents).hexdigest()
    assert sha == validation['sources'][key]['sha256']
    window = json.loads(contents)
    for sample in window['samples']:
        sample['channels'] = [v-b for v, b in zip(sample['raw'], frozen['feature_basis']['common_raw_baseline'])]
    windows[key] = window
    sources[key] = {'path': str(path), 'sha256': sha}
report['historical_regression'] = {'scope': 'raw-coordinate historical regression only, not current live-page alignment or independent candidate acceptance',
    'raw_baseline': frozen['feature_basis']['common_raw_baseline'], 'sources': sources, 'sweeps': []}
for label, candidate in zip(variant_labels, profiles):
    result = replay(candidate, profile, windows, [0]*12)
    summary = {}
    for key, values in result['poses'].items():
        sign = 1 if key == 'right' else -1
        active = sum(sign*v >= .2 for v in values) if key in ('left', 'right') else sum(abs(v) > .05 for v in values)
        reverse = sum(sign*v < -.05 for v in values) if key in ('left', 'right') else 0
        summary[key] = {'count': len(values), 'active': active, 'reverse': reverse, 'shear': describe(values)}
    report['historical_regression']['sweeps'].append({'variant': label, 'threshold': candidate['shear']['threshold'],
        'passes_raw_replay': passes(result), 'normalUnchanged': result['normalUnchanged'], 'summary': summary})
assert hashlib.sha256(PROFILE.read_bytes()).hexdigest() == profile_sha
print(json.dumps(report, ensure_ascii=False, allow_nan=False), flush=True)
