import json, os, time
from pathlib import Path
from scripts.backend import get_json
LOKI=os.getenv("LOKI_URL","http://lgtm:3100")
STATE=Path("/workspace/.lab-state/last-traffic.json")
QUERY='{service_name="payment"} | event_name = "payment.amount_validation_rejected"'

def find():
    state=json.loads(STATE.read_text())
    payload=get_json(LOKI,"/loki/api/v1/query_range",{"query":QUERY,"start":int(state["started_at"]*1e9),"end":int(time.time()*1e9),"limit":1000,"direction":"forward"})
    if payload.get("status")!="success": raise RuntimeError(payload)
    rows=[]
    for stream in payload.get("data",{}).get("result",[]):
        labels=stream.get("stream",{})
        for value in stream.get("values",[]):
            line=value[1]; meta=value[2] if len(value)>2 and isinstance(value[2],dict) else {}
            merged={**labels,**meta}
            try:
                body=json.loads(line)
                if isinstance(body,dict): merged.update(body)
            except Exception: pass
            rows.append(merged)
    valid=[]
    for row in rows:
        checks=[
            row.get("event_name")=="payment.amount_validation_rejected",
            row.get("reason_code")=="minor_unit_mismatch",
            row.get("payment_currency")=="CAD",
            str(row.get("payment_discounted")).lower()=="true",
            str(row.get("expected_minor_units"))=="1000",
            str(row.get("received_minor_units"))=="1001",
            row.get("checkout_rounding_mode")=="HALF_UP",
            row.get("payment_rounding_mode")=="HALF_EVEN",
            bool(row.get("trace_id")), bool(row.get("span_id")),
        ]
        if all(checks): valid.append(row)
    return valid

def main():
    if not STATE.exists(): print("CODE_OR_SERVICE_ERROR: run ./lab traffic incident first"); return 2
    deadline=time.time()+20; last='no fresh structured rejection events'
    while time.time()<deadline:
        try:
            rows=find()
            if len(rows)==25:
                trace_ids={str(row["trace_id"]) for row in rows}
                print(f"PASS logs: events=25, correlated_traces={len(trace_ids)}")
                print("  segment=CAD discounted; expected=1000; received=1001")
                print("  modes=HALF_EVEN/HALF_UP; reason=minor_unit_mismatch")
                return 0
            last=f"matching events={len(rows)}, expected exactly 25"
        except Exception as exc:last=str(exc)
        time.sleep(2)
    print("WAITING_FOR_TELEMETRY: "+last); print("Recovery: ./lab recover logs"); return 1
if __name__=="__main__": raise SystemExit(main())
