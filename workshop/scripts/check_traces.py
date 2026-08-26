import json, os, time
from pathlib import Path
from workshop.scripts.backend import get_json, attrs
TEMPO=os.getenv("TEMPO_URL","http://lgtm:3200")
STATE=Path("/workspace/.lab-state/last-traffic.json")
OUT=Path("/workspace/.lab-state/last-trace.json")
QUERY='{ resource.service.name = "payment" && name = "payment.amount_validation" && status = error }'

def inspect_trace(trace):
    services=set(); validation=None; checkout_http_200=False
    for batch in trace.get("batches",[]):
        resource=attrs(batch.get("resource",{}).get("attributes")); service=resource.get("service.name")
        if service: services.add(service)
        for scope in batch.get("scopeSpans",[]):
            for span in scope.get("spans",[]):
                sa=attrs(span.get("attributes")); name=span.get("name","")
                status=span.get("status",{}).get("code")
                if service=="payment" and name=="payment.amount_validation" and status in (2,"STATUS_CODE_ERROR"):
                    if "expected_minor_units" in sa or "received_minor_units" in sa: raise RuntimeError("Trace leaks explanation fields")
                    if sa.get("payment.currency")=="CAD" and str(sa.get("payment.discounted")).lower()=="true" and sa.get("validation.result")=="rejected":
                        validation=span
                if service=="checkout":
                    http=sa.get("http.response.status_code",sa.get("http.status_code"))
                    if str(http)=="200": checkout_http_200=True
    return services,validation,checkout_http_200

def find():
    state=json.loads(STATE.read_text()); start=int(state["started_at"]); end=int(time.time())
    payload=get_json(TEMPO,"/api/search",{"q":QUERY,"start":start,"end":end,"limit":50})
    ids=[]
    for item in payload.get("traces",[]):
        tid=item.get("traceID") or item.get("traceId")
        if tid and tid not in ids: ids.append(tid)
    for tid in ids:
        trace=get_json(TEMPO,f"/api/traces/{tid}")
        services,validation,http200=inspect_trace(trace)
        if validation and {"checkout","inventory","payment"}.issubset(services):
            OUT.write_text(json.dumps({"trace_id":tid,"started_at":state["started_at"],"services":sorted(services),"checkout_http_200":http200},indent=2))
            return tid,services,http200
    return None

def main():
    if not STATE.exists(): print("CODE_OR_SERVICE_ERROR: run ./lab traffic incident first"); return 2
    deadline=time.time()+20; last='no fresh distributed failed-validation trace'
    while time.time()<deadline:
        try:
            result=find()
            if result:
                tid,services,http200=result
                print("PASS traces: fresh distributed payment.amount_validation ERROR span")
                print("  services="+",".join(sorted(services)))
                print("  validation=CAD discounted rejected; explanation fields absent")
                print("  checkout_http_200="+str(http200).lower())
                print("  trace_id="+tid); return 0
        except Exception as exc:last=str(exc)
        time.sleep(2)
    print("WAITING_FOR_TELEMETRY: "+last); print("Recovery: ./lab recover traces"); return 1
if __name__=="__main__": raise SystemExit(main())
