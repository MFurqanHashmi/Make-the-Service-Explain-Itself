import json, os, time, urllib.parse, urllib.request

def get_json(base, path, params=None):
    url=base.rstrip('/')+path
    if params: url += '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=8) as response:
        return json.load(response)

def wait_until(fn, timeout=20, interval=2):
    deadline=time.time()+timeout; error='no matching evidence'
    while time.time()<deadline:
        try:
            value=fn()
            if value: return value
        except Exception as exc: error=str(exc)
        time.sleep(interval)
    raise TimeoutError(error)

def attrs(items):
    out={}
    for item in items or []:
        key=item.get('key')
        val=item.get('value',{})
        for field in ('stringValue','intValue','doubleValue','boolValue'):
            if field in val: out[key]=val[field]; break
    return out
