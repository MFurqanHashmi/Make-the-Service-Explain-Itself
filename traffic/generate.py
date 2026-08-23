import asyncio, json, os, sys, time
from pathlib import Path
import httpx

CHECKOUT_URL = os.getenv("CHECKOUT_URL", "http://checkout:8000")
STATE = Path("/workspace/.lab-state/last-traffic.json")


def request(order_id, currency, discounted, total):
    return {"order_id": order_id, "currency": currency, "discounted": discounted, "unrounded_total": total}


def profile(name):
    if name == "healthy":
        return [request(f"healthy-cad-{i:03}", "CAD", False, "10.00") for i in range(50)] + [
            request(f"healthy-usd-{i:03}", "USD", True, "10.015") for i in range(50)
        ]
    if name in {"incident", "checkpoint"}:
        return [request(f"cad-standard-{i:03}", "CAD", False, "10.00") for i in range(50)] + [
            request(f"usd-discount-{i:03}", "USD", True, "10.015") for i in range(25)
        ] + [request(f"cad-discount-{i:03}", "CAD", True, "10.005") for i in range(25)]
    raise SystemExit(f"Unknown profile: {name}")

async def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "incident"
    rows = profile(name)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    outcomes = {}
    statuses = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Ensure a counter sample exists before the freshness boundary.
        await client.post(f"{CHECKOUT_URL}/checkout", json=request("warmup", "CAD", False, "10.00"))
        await asyncio.sleep(3.0)
        started = time.time()
        await asyncio.sleep(3.0)
        for row in rows:
            response = await client.post(f"{CHECKOUT_URL}/checkout", json=row)
            statuses[str(response.status_code)] = statuses.get(str(response.status_code), 0) + 1
            outcome = response.json()["outcome"]
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
            await asyncio.sleep(0.035)
        traffic_ended = time.time()
        await asyncio.sleep(5.0)
        ended = time.time()
    result = {
        "profile": name,
        "started_at": started,
        "traffic_ended_at": traffic_ended,
        "ended_at": ended,
        "requests": len(rows),
        "http_statuses": statuses,
        "business_outcomes": outcomes,
    }
    STATE.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    failures = sum(v for k, v in outcomes.items() if k != "success")
    print(f"Business failure percentage: {100 * failures / len(rows):.1f}%")

if __name__ == "__main__": asyncio.run(main())
