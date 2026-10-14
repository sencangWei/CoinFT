import json,copy,statistics
from pathlib import Path
from calibration.shear_refit_replay import replay,passes
r=json.loads(Path(".superpowers/sdd/shear-refit-confirmed-left-report-20261005.json").read_text(encoding="utf-8"))
ref=r["reference_offset"]
w={}
for key,meta in r["sources"].items():
    data=json.loads(Path(meta["path"]).read_text(encoding="utf-8"))
    data["pose"]=key
    data["evidence"]="aligned_currentbaseline_"+key+".json"
    for sample in data["samples"]: sample["channels"]=[v-b for v,b in zip(sample["raw"],ref)]
    w[key]=data
base=[statistics.median(s["channels"][i] for s in w["left_before"]["samples"]) for i in range(12)]
old=json.loads(Path("demo_web/shear_demo_profile.json").read_text(encoding="utf-8"))
p=replay(r["candidate"],old,w,base)
summary={}
for key,vals in p["poses"].items():
    summary[key]={"count":len(vals),"min":min(vals),"max":max(vals),"median":statistics.median(vals)}
    if key=="left": summary[key].update(active_fraction=sum(x<=-0.2 for x in vals)/len(vals),reverse_count=sum(x>0.05 for x in vals))
    elif key=="right": summary[key].update(active_fraction=sum(x>=0.2 for x in vals)/len(vals),reverse_count=sum(x< -0.05 for x in vals))
    else: summary[key]["false_shear_count"]=sum(abs(x)>0.05 for x in vals)
print(json.dumps({"purpose":"same candidate, one latest recorded unloaded reference shared by all windows; no retune","baseline":base,"accepted":passes(p),"summary":summary,"replay":p},ensure_ascii=True,allow_nan=False,separators=(",",":")))
