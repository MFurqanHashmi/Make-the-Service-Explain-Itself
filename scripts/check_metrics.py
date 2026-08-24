import json, os, time
from pathlib import Path
from scripts.backend import get_json
PROM=os.getenv("PROMETHEUS_URL","http://lgtm:9090")
STATE=Path("/workspace/.lab-state/last-traffic.json")
LOOKBACK=60

def api(path,params=None):
    payload=get_json(PROM,path,params)
    if payload.get("status")!="success": raise RuntimeError(payload)
    return payload["data"]
def metric_name(prefix):
    vals=api("/api/v1/label/__name__/values")
    candidates=[v for v in vals if v.startswith(prefix)]
    preferred=[v for v in candidates if v.endswith("_total")]
    if preferred:return preferred[0]
    if candidates:return candidates[0]
    raise LookupError(prefix)
def series(query,start,end):
    return api("/api/v1/query_range",{"query":query,"start":start-LOOKBACK,"end":end,"step":1})["result"]
def deltas(rows,start):
    """Increase per series between `start` and the end of the window.

    Hot reload restarts the process, so any counter can reset to zero part way
    through. A reset is not always visible at the window's first sample: a series
    the reloaded process has not touched yet keeps reporting its stale pre-reload
    value, and the drop only appears once traffic reaches that series. So walk the
    whole window and treat every decrease as a restart.
    """
    out=[]
    for item in rows:
        vals=[(float(t),float(v)) for t,v in item.get("values",[])]
        window=[v for t,v in vals if t>=start]
        if not window: continue
        before=[v for t,v in vals if t<start]
        previous=before[-1] if before else 0.0
        total=0.0
        for current in window:
            total += (current-previous) if current>=previous else current
            previous=current
        out.append((item["metric"],max(0.0,total)))
    return out

def main():
    if not STATE.exists(): print("CODE_OR_SERVICE_ERROR: run ./lab traffic incident first"); return 2
    state=json.loads(STATE.read_text()); deadline=time.time()+20; last=''
    while time.time()<deadline:
        try:
            business=metric_name("checkout_completed"); http=metric_name("checkout_http_responses")
            start=state["started_at"]; end=time.time()
            br=deltas(series(f'sum by (checkout_outcome,checkout_currency,checkout_discounted) ({business})',start,end),start)
            hr=deltas(series(f'sum by (http_response_status_code) ({http})',start,end),start)
            total=sum(v for _,v in br); failures=sum(v for m,v in br if m.get("checkout_outcome")!="success")
            cad=sum(v for m,v in br if m.get("checkout_outcome")=="payment_rejected" and m.get("checkout_currency")=="CAD" and str(m.get("checkout_discounted","")).lower()=="true")
            ht=sum(v for _,v in hr); non200=sum(v for m,v in hr if m.get("http_response_status_code")!="200")
            if total>=95 and failures>=24 and cad>=24 and ht>=95 and non200==0:
                print(f"PASS metrics: completed={total:.0f}, failures={failures:.0f}, discounted_CAD={cad:.0f}, HTTP_200={ht:.0f}"); return 0
            last=f"completed={total}, failures={failures}, discounted_CAD={cad}, HTTP={ht}"
        except Exception as exc:last=str(exc)
        time.sleep(2)
    print("WAITING_FOR_TELEMETRY: "+last); print("Recovery: ./lab recover metrics"); return 1
if __name__=="__main__": raise SystemExit(main())
