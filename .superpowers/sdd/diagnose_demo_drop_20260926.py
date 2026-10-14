"""Read-only HTTP observation of the existing live service; no serial or tare."""
import json
import time
import urllib.request

started = time.monotonic()
samples = []
events = []
previous = None
while time.monotonic() - started < 30:
    request_at = time.monotonic()
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765/api/state', timeout=2) as response:
            state = json.load(response)
        entry = {key: state.get(key) for key in (
            'mode', 'status', 'rate', 'frames', 'invalid_frames', 'invalid_recent',
            'saturated_recent', 'resyncs', 'updated_at')}
        entry['elapsed'] = round(time.monotonic() - started, 3)
        entry['http_ms'] = round((time.monotonic() - request_at) * 1000, 1)
        samples.append(entry)
        if previous is None or any(entry[key] != previous[key] for key in (
                'status', 'invalid_frames', 'invalid_recent', 'saturated_recent', 'resyncs')):
            events.append(entry)
            print(json.dumps({'event': entry}), flush=True)
        previous = entry
    except Exception as error:
        entry = {'elapsed': round(time.monotonic() - started, 3), 'error': str(error)}
        events.append(entry)
        print(json.dumps({'event': entry}), flush=True)
    time.sleep(0.05)
print(json.dumps({'sample_count': len(samples), 'first': samples[0] if samples else None,
                  'last': samples[-1] if samples else None, 'events': events,
                  'max_http_ms': max((s['http_ms'] for s in samples), default=0)}), flush=True)
