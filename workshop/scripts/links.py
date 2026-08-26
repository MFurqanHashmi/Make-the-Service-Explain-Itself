import json
import urllib.parse

BASE = "http://localhost:3000"


def explore(uid, field, query, query_type):
    """Build a Grafana Explore link.

    Loki and Prometheus carry the query in `expr`; Tempo carries it in `query`.
    Using the wrong field opens Explore with an empty editor.
    """
    pane = {
        "datasource": uid,
        "queries": [{"refId": "A", field: query, "queryType": query_type, "editorMode": "code"}],
        "range": {"from": "now-15m", "to": "now"},
    }
    return BASE + "/explore?orgId=1&left=" + urllib.parse.quote(json.dumps(pane, separators=(",", ":")))


def loki(query):
    return explore("lab-loki", "expr", query, "range")


def tempo(query):
    return explore("lab-tempo", "query", query, "traceql")


LINKS = [
    ("Runtime and checkout metrics",
     BASE + "/d/checkout-overview/checkout-observability?from=now-15m&to=now&refresh=5s"),
    ("Failed payment-validation traces",
     tempo('{ resource.service.name = "payment" && name = "payment.amount_validation" && status = error }')),
    ("Structured payment-validation events",
     loki('{service_name="payment"} | event_name = "payment.amount_validation_rejected"')),
    ("Noisy starting logs",
     loki('{service_name=~"checkout|inventory|payment"}')),
]

if __name__ == "__main__":
    for index, (title, url) in enumerate(LINKS):
        if index:
            print()
        print(f"{title}:")
        print(url)
