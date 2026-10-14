import json,time,sys,hashlib
from pathlib import Path
from datetime import datetime
import psutil
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path.cwd()))
from calibration.capture_demo_pose import capture

def owner():
    listeners=[c for c in psutil.net_connections(kind='tcp') if c.status==psutil.CONN_LISTEN and c.laddr.port==8765]
    assert len(listeners)==1,'expected one HTTP owner'
    proc=psutil.Process(listeners[0].pid)
    assert any(Path(a).name=='coinft_demo.py' for a in proc.cmdline()),'wrong HTTP owner'
    return {'pid':proc.pid,'created':proc.create_time()}

observations=[]
EXPECTED_BASELINE=[-9.5,-44,-26,-61,28,-20,17.5,-9.5,-0.5,-4,3.5,6.5]
EXPECTED_RAW_OFFSET=[28211,27830,26368,27209.5,26761.5,26826,27727,26471,28678,28314,29317,28379]
EXPECTED_SHA='1df74f4570f5119f180f9e7830120abe555bd6c37cc33ab3dbc33b8dba5a6020'
who=owner()
out=Path('.superpowers/sdd/demo-pull-controls-plus-20261014.json')
assert not out.exists(),'do not overwrite evidence'
with sync_playwright() as pw:
    browser=pw.chromium.connect_over_cdp('http://127.0.0.1:9225',timeout=2000)
    pages=[p for c in browser.contexts for p in c.pages if p.url=='http://127.0.0.1:8765/']
    assert len(pages)==1
    page=pages[0]
    before=page.evaluate('({baseline:demoBaseline,profile:shearProfile,paused:demoPaused,frame:latestFrame})')
    assert before['baseline']==EXPECTED_BASELINE,'expected restored visual baseline changed'
    assert isinstance(before['baseline'],list) and len(before['baseline'])==12 and not before['paused']
    assert all(isinstance(v,(int,float)) for v in before['baseline'])
    assert before['profile']==json.loads(Path('demo_web/shear_demo_profile.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(Path('demo_web/shear_demo_profile.json').read_bytes()).hexdigest()==EXPECTED_SHA
    def observe(state):
        observations.append({'host':datetime.now().astimezone().isoformat(),'monotonic':time.monotonic(),'state':state})
        current=page.evaluate('({frame:latestFrame,baseline:demoBaseline,channels:lastChannels,paused:demoPaused,normal:surfaceView.target,shear:surfaceView.shearTarget,renderedNormal:surfaceView.level,renderedShear:surfaceView.shearLevel,score:demoBaseline?shearScore(lastChannels.map((v,i)=>v-demoBaseline[i]),shearProfile):null})')
        observations[-1]['page']=current
        assert current['baseline']==before['baseline'] and not current['paused'],'page basis changed or animation paused'
        assert [a-b for a,b in zip(state['raw'],state['channels'])]==EXPECTED_RAW_OFFSET,'backend reference changed'
        assert state['port']=='COM6' and state['mode']=='live' and state['tare_progress']==100
        if len(observations)>1:
            first=observations[0]['state']
            for key in ['invalid_frames','saturated','resyncs']:
                assert state[key]==first[key],'quality fault '+key
            for key in ['attempts','successes']:
                assert state['recovery'][key]==first['recovery'][key],'recovery epoch changed'
            assert [a-b for a,b in zip(state['raw'],state['channels'])]==[a-b for a,b in zip(first['raw'],first['channels'])],'channel reference changed'
            assert state['diagnostics']['parser_discarded_bytes']==first['diagnostics']['parser_discarded_bytes']
    try:
        data=capture('http://127.0.0.1:8765','confirmed_plus_x_control','coinft-current-20260925',5.0,0.125,on_state=observe,minimum_samples=40)
        after=page.evaluate('({baseline:demoBaseline,profile:shearProfile,paused:demoPaused,frame:latestFrame})')
        assert after['baseline']==before['baseline'] and after['profile']==before['profile'] and not after['paused']
        assert owner()==who
        a,b=observations[0],observations[-1]
        rate=(b['state']['frames']-a['state']['frames'])/(b['monotonic']-a['monotonic'])
        assert 150<=rate<=250
        data.update(scope='confirmed plus control for pull diagnosis; read-only, no zero or fitting',owner=who,capture_ok=True,aggregate_rate=rate,observations=observations,evidence=str(out),page_before=before,page_after=after)
        screenshot=Path('.superpowers/sdd/demo-pull-controls-plus-20261014.png')
        assert not screenshot.exists(),'do not overwrite screenshot'
        data['screenshot_state']=page.evaluate('({frame:latestFrame,normal:surfaceView.level,shear:surfaceView.shearLevel,paused:demoPaused,baseline:demoBaseline})')
        page.screenshot(path=str(screenshot))
        data['screenshot']=str(screenshot)
        print(json.dumps({'out':str(out),'evidence':data},ensure_ascii=False,allow_nan=False,separators=(',',':')),flush=True)
    except Exception as exc:
        print(json.dumps({'out':str(out.with_suffix('.failed.json')),'evidence':{'capture_ok':False,'owner':who,'error':repr(exc),'page_before':before,'observations':observations}},ensure_ascii=False,separators=(',',':')),flush=True)
        raise SystemExit(1)
