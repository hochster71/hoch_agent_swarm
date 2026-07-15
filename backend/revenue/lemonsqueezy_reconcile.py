"""Lemon Squeezy revenue capture — reconcile real orders into HELM's hash-chained revenue ledger.

WHY: the HSF StoryBoard was sold through Lemon Squeezy, not Stripe. HELM captured the Epic Fury Stripe
subscription but had no Lemon Squeezy path, so that revenue was invisible. This closes the gap with the
SAME discipline as the Stripe capture: every order becomes a hash-chained revenue entry with real
evidence, idempotently, fail-closed.

DISCIPLINE (No fake green):
  * paid + not refunded  -> SETTLED  (collected sale)
  * pending              -> PENDING  (not yet money)
  * refunded / failed    -> NOT revenue (skipped)
  * evidence is the Lemon Squeezy order id + receipt identifier — a sale with no evidence is a claim.
  * idempotent: an order already in the ledger (by source id) is never double-counted.

SECURITY: the read-only Lemon Squeezy API key is read from the LEMONSQUEEZY_API_KEY env var and never
logged. This module only READS orders and RECORDS revenue — it never moves money or issues refunds.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Optional

API_ROOT = "https://api.lemonsqueezy.com/v1"
ENV_KEY = "LEMONSQUEEZY_API_KEY"


# ----------------------------------------------------------------- pure mapping
def order_to_row(order: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Map one Lemon Squeezy order to a HELM revenue row, or None if it is not revenue."""
    a = order.get("attributes", {}) or {}
    status = str(a.get("status", "")).lower()
    if a.get("refunded") or status in ("refunded", "failed", "void", "cancelled", "canceled"):
        return None                                  # not revenue
    if status not in ("paid", "pending", "processing"):
        return None
    cents = a.get("total_usd")
    if cents is None:
        cents = a.get("total", 0)
    amount_usd = round((cents or 0) / 100.0, 4)
    if amount_usd <= 0:
        return None
    item = a.get("first_order_item", {}) or {}
    product = item.get("product_name") or "Lemon Squeezy order"
    state = "SETTLED" if status == "paid" else "PENDING"
    oid = str(order.get("id"))
    return {
        "product": product,
        "domain": "BUSINESS",
        "amount_usd": amount_usd,
        "state": state,
        "source": f"lemonsqueezy:{oid}",
        "buyer_ref": a.get("user_email"),
        "evidence": f"lemonsqueezy_order:{a.get('identifier') or oid} status={status} total_cents={cents}",
    }


# ----------------------------------------------------------------- reconcile (idempotent)
def reconcile_orders(orders: list[dict[str, Any]], ledger) -> list[dict[str, Any]]:
    """Append rows for orders not already captured. `ledger` needs existing_sources() + record_revenue().
    Returns the rows actually appended (new revenue only)."""
    have = set(ledger.existing_sources())
    added = []
    for o in orders:
        row = order_to_row(o)
        if row is None or row["source"] in have:
            continue
        ledger.record_revenue(**row)
        have.add(row["source"])
        added.append(row)
    return added


# ----------------------------------------------------------------- network (read-only)
def fetch_orders(api_key: str, page_size: int = 100) -> list[dict[str, Any]]:
    """Read all orders from the Lemon Squeezy API. Read-only; paginates. Never logs the key."""
    orders: list[dict[str, Any]] = []
    url = f"{API_ROOT}/orders?page[size]={page_size}"
    while url:
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/vnd.api+json",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        orders.extend(body.get("data", []))
        url = (body.get("links", {}) or {}).get("next")
    return orders


# ----------------------------------------------------------------- ledger adapter
class _HochLedgerAdapter:
    """Wraps HELM's HochLedger with the existing_sources()/record_revenue() shape reconcile needs."""
    def __init__(self):
        from backend.mission_control.hoch_ledger import HochLedger
        self._l = HochLedger()
    def existing_sources(self) -> set[str]:
        return {e.get("source") for e in self._l.revenue.entries() if e.get("source")}
    def record_revenue(self, **row):
        return self._l.record_revenue(**row)


def main() -> int:
    key = os.environ.get(ENV_KEY, "").strip()
    if not key:
        print(f"{ENV_KEY} not set — fail closed. Create a READ-ONLY Lemon Squeezy API key and export it. "
              "Nothing was written.")
        return 2
    try:
        orders = fetch_orders(key)
    except urllib.error.HTTPError as e:
        print(f"Lemon Squeezy API error {e.code}: {e.reason}. Nothing written.")
        return 1
    except Exception as e:
        print(f"Lemon Squeezy fetch failed: {e}. Nothing written.")
        return 1
    added = reconcile_orders(orders, _HochLedgerAdapter())
    settled = sum(r["amount_usd"] for r in added if r["state"] == "SETTLED")
    pending = sum(r["amount_usd"] for r in added if r["state"] == "PENDING")
    print(f"Lemon Squeezy: {len(orders)} orders read · {len(added)} new revenue rows captured "
          f"(${settled:.2f} settled, ${pending:.2f} pending). Ledger is hash-chained.")
    for r in added:
        print(f"   + {r['product']} · ${r['amount_usd']:.2f} · {r['state']} · {r['source']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
