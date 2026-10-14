import json,copy,hashlib
from pathlib import Path
from datetime import datetime
from calibration.shear_refit_replay import KEYS,replay,passes
r=json.loads(Path('.superpowers/sdd/shear-refit-fresh-right-20261005.json').read_text(encoding='utf-8'));p=r['candidate'];old=json.loads(Path('demo_web/shear_demo_profile.json').read_text(encoding='utf-8'));base=r['feature_basis']['common_raw_baseline'];offset=r['feature_basis']['reference_offset'];baseline=r['feature_basis']['common_baseline']
sha=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest();assert sha=='e59c5876fe815262811a000f9afe2b755748daf9762b1611a095ecbb21c0e283';assert [a-b for a,b in zip(base,offset)]==baseline
windows={};sources={};first_state=None;previous=None
for key in KEYS:
 path=Path('calibration/shear_frozen_validation_20261005')/(key+'.json');data=path.read_bytes();w=json.loads(data);assert w['capture_ok'] and len(w['samples'])>=40 and 150<=w['aggregate_rate']<=250
 assert w['owner']=={'pid':87952,'created':1791188496.384482}
 assert (datetime.fromisoformat(w['samples'][-1]['host'])-datetime.fromisoformat(w['samples'][0]['host'])).total_seconds()>=5
 for obs in w['observations']:
  s=obs['state'];assert s['invalid_frames']==4 and s['saturated']==0 and s['resyncs']==0 and s['invalid_recent']==0 and s['saturated_recent']==0
  assert s['status']=='live' and s['mode']=='live' and s['port']=='COM6' and s['tare_progress']==100
  assert s['recovery']['attempts']==31 and s['recovery']['successes']==3;assert s['diagnostics']['parser_discarded_bytes']==0
  if previous:
   assert obs['monotonic']>previous['monotonic']
   assert s['frames']>=previous['state']['frames']
   assert s['diagnostics']['serial_bytes']>=previous['state']['diagnostics']['serial_bytes']
   assert s['diagnostics']['parsed_frames']>=previous['state']['diagnostics']['parsed_frames']
  previous=obs
 sources[key]={'path':str(path),'sha256':hashlib.sha256(data).hexdigest(),'sample_count':len(w['samples']),'observation_count':len(w['observations']),'span':(datetime.fromisoformat(w['samples'][-1]['host'])-datetime.fromisoformat(w['samples'][0]['host'])).total_seconds(),'rate':w['aggregate_rate']}
 for sample in w['samples']:sample['channels']=[a-b for a,b in zip(sample['raw'],offset)]
 windows[key]=w
last=r['sources']['right_after'];first=windows['press_before']['samples'][0];assert first['f']>last['last_frame'] and datetime.fromisoformat(first['host'])>datetime.fromisoformat(last['last_host'])
result=replay(p,old,windows,baseline);summaries={}
for key,v in result['poses'].items():
 sign=1 if key=='right' else -1
 active=sum(sign*x>=.2 for x in v) if key in ('left','right') else sum(abs(x)>.05 for x in v)
 reverse=sum(sign*x<-.05 for x in v) if key in ('left','right') else 0
 summaries[key]={'count':len(v),'active':active,'reverse':reverse,'min':min(v),'max':max(v)}
manifest=json.loads(Path('.superpowers/sdd/stream-recovery-final-manifest.json').read_text(encoding='utf-8'));protected={x['path']:hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256'].lower() for x in manifest['files']};protected['coinft_demo.py']=hashlib.sha256(Path('coinft_demo.py').read_bytes()).hexdigest()==manifest['production_hash'].lower();assert all(protected.values())
print(json.dumps({'scope':'independent frozen-candidate validation; no fitting, no baseline change, no deployment','accepted':passes(result),'candidate_sha256':sha,'candidate_report':'.superpowers/sdd/shear-refit-fresh-right-20261005.json','fixed_raw_baseline':base,'reference_offset':offset,'common_baseline':baseline,'sources':sources,'summaries':summaries,'report':result,'protected_unchanged':protected,'quality':{'owner':windows['press_before']['owner'],'invalid':4,'saturated':0,'resyncs':0,'parser_discarded_bytes':0,'recovery_attempts':31,'recovery_successes':3}}))
