"""Deterministic traffic for the lab.

Two properties matter and are easy to break:

1. Order IDs are opaque. If they encoded the segment ("cad-discount-014"),
   the plain-prose logs in section 1 would hand over the scope answer and the
   metrics step would have nothing left to teach.
2. Segments are interleaved, not grouped. Every four consecutive requests
   contain exactly one from the failing segment, so any sampling window over
   the burst reads the same 25% business-failure rate. Grouped traffic makes
   the dashboard read 0% or 100% depending on where the window lands.
"""
import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import httpx

CHECKOUT_URL = os.getenv("CHECKOUT_URL", "http://checkout:8000")
STATE = Path("/workspace/.lab-state/last-traffic.json")

REQUEST_COUNT = 100
# ~20 seconds of traffic. Long enough that the dashboard's 15s rate window fits
# entirely inside the burst, and long enough to watch the graph move live.
REQUEST_SPACING_SECONDS = 0.15

# Quiet period around the burst. It must exceed the dashboard's rate window so
# that consecutive traffic runs never share a sampling window.
LEAD_IN_SECONDS = 18.0
TAIL_SECONDS = 6.0

# currency, discounted, total per profile
CAD_STANDARD = ("CAD", False, "10.00", "10.00")
USD_DISCOUNT = ("USD", True, "10.015", "10.015")
# HALF_UP gives 1001, HALF_EVEN gives 1000: a one-cent disagreement.
CAD_DISCOUNT = ("CAD", True, "10.005", "10.005")

PROFILES = {
    # No failing segment at all, and no discounted CAD, so the incident's
    # affected segment stands alone on the dashboard.
    "healthy": (CAD_STANDARD, USD_DISCOUNT),
    # One in four requests comes from the failing segment.
    "incident": (CAD_STANDARD, USD_DISCOUNT, CAD_STANDARD, CAD_DISCOUNT),
}


def order_id(profile, index):
    """An opaque but reproducible identifier, like a real order reference."""
    digest = hashlib.sha1(f"{profile}:{index}".encode()).hexdigest()
    return f"ord-{digest[:10]}"


def profile(name):
    if name == "checkpoint":
        name = "incident"
    if name not in PROFILES:
        raise SystemExit(f"Unknown profile: {name}. Use 'healthy' or 'incident'.")
    cycle = PROFILES[name]
    rows = []
    for index in range(REQUEST_COUNT):
        currency, discounted, total, _ = cycle[index % len(cycle)]
        rows.append({
            "order_id": order_id(name, index),
            "currency": currency,
            "discounted": discounted,
            "unrounded_total": total,
        })
    return rows


async def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "incident"
    rows = profile(name)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    outcomes = {}
    statuses = {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Ensure a counter sample exists before the freshness boundary.
        await client.post(f"{CHECKOUT_URL}/checkout", json={
            "order_id": order_id("warmup", 0),
            "currency": "CAD",
            "discounted": False,
            "unrounded_total": "10.00",
        })
        await asyncio.sleep(3.0)
        started = time.time()
        print(f"Sending {len(rows)} {name} checkouts...")
        await asyncio.sleep(LEAD_IN_SECONDS)
        for row in rows:
            response = await client.post(f"{CHECKOUT_URL}/checkout", json=row)
            statuses[str(response.status_code)] = statuses.get(str(response.status_code), 0) + 1
            outcome = response.json()["outcome"]
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
            await asyncio.sleep(REQUEST_SPACING_SECONDS)
        traffic_ended = time.time()
        await asyncio.sleep(TAIL_SECONDS)
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


if __name__ == "__main__":
    asyncio.run(main())
