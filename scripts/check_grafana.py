import os
from scripts.backend import get_json
GRAFANA=os.getenv("GRAFANA_URL","http://lgtm:3000")
health=get_json(GRAFANA,"/api/health")
if health.get("database")!="ok": raise SystemExit("Grafana database not ready")
for uid in ("lab-prometheus","lab-loki","lab-tempo"):
    data=get_json(GRAFANA,f"/api/datasources/uid/{uid}")
    if data.get("uid")!=uid: raise SystemExit(f"Missing datasource {uid}")
tempo=get_json(GRAFANA,"/api/datasources/uid/lab-tempo")
loki=get_json(GRAFANA,"/api/datasources/uid/lab-loki")
if tempo.get("jsonData",{}).get("tracesToLogsV2",{}).get("datasourceUid")!="lab-loki": raise SystemExit("Tempo to Loki correlation not provisioned")
derived=loki.get("jsonData",{}).get("derivedFields",[])
if not any(item.get("datasourceUid")=="lab-tempo" for item in derived): raise SystemExit("Loki to Tempo correlation not provisioned")
dashboard=get_json(GRAFANA,"/api/dashboards/uid/checkout-overview")
if dashboard.get("dashboard",{}).get("uid")!="checkout-overview": raise SystemExit("Checkout dashboard missing")
print("PASS Grafana: dashboard, datasources, and bidirectional correlation configuration are provisioned")
