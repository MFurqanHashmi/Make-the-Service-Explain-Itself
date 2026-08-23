import os,time
from scripts.backend import get_json
PROM=os.getenv("PROMETHEUS_URL","http://lgtm:9090"); TEMPO=os.getenv("TEMPO_URL","http://lgtm:3200"); LOKI=os.getenv("LOKI_URL","http://lgtm:3100")
deadline=time.time()+25
ok=[False,False,False]
while time.time()<deadline and not all(ok):
    try: ok[0]=bool(get_json(PROM,"/api/v1/query",{"query":'sum({__name__=~"lab_readiness.*"})'}).get("data",{}).get("result"))
    except Exception: pass
    try: ok[1]=bool(get_json(TEMPO,"/api/search",{"q":'{ name = "lab.readiness" }',"limit":5}).get("traces"))
    except Exception: pass
    try: ok[2]=bool(get_json(LOKI,"/loki/api/v1/query_range",{"query":'{service_name=~"checkout|inventory|payment"} | event_name = "lab.readiness"',"start":int((time.time()-300)*1e9),"end":int(time.time()*1e9),"limit":10}).get("data",{}).get("result"))
    except Exception: pass
    if not all(ok): time.sleep(2)
if not all(ok): raise SystemExit(f"Telemetry pipeline not ready: metrics={ok[0]} traces={ok[1]} logs={ok[2]}")
print("READY: checkout, inventory, payment, metrics, traces, logs, and Grafana are available")
