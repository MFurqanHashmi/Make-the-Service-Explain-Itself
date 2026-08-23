import json
import urllib.parse

BASE = "http://localhost:3000"

def explore(uid, query, query_type):
    left = {
        "datasource": uid,
        "queries": [{"refId": "A", "query": query, "queryType": query_type}],
        "range": {"from": "now-15m", "to": "now"},
    }
    return BASE + "/explore?orgId=1&left=" + urllib.parse.quote(json.dumps(left, separators=(",", ":")))

print("Runtime and checkout metrics:")
print(BASE + "/d/checkout-overview/checkout-observability?from=now-15m&to=now&refresh=5s")
print("\nFailed payment-validation traces:")
print(explore("lab-tempo", '{ resource.service.name = "payment" && name = "payment.amount_validation" && status = error }', "traceql"))
print("\nStructured payment-validation events:")
print(explore("lab-loki", '{service_name="payment"} | event_name = "payment.amount_validation_rejected"', "range"))
print("\nNoisy starting logs:")
print(explore("lab-loki", '{service_name=~"checkout|inventory|payment"}', "range"))
