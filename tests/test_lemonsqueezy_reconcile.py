"""Lemon Squeezy revenue capture — tests before the implementation.

The HSF StoryBoard was sold through Lemon Squeezy, not Stripe. HELM must capture it the SAME way it
captures Stripe: real order -> hash-chained revenue entry with evidence, idempotent, fail-closed.
No fake green: an order with no payment is not revenue; a refunded order is not revenue.
"""
from __future__ import annotations

from backend.revenue.lemonsqueezy_reconcile import order_to_row, reconcile_orders   # do not exist yet


def _order(oid, status, total_cents, product="HSF StoryBoard", email="buyer@example.com", refunded=False):
    return {"id": oid, "attributes": {
        "status": status, "total": total_cents, "total_usd": total_cents,
        "currency": "USD", "refunded": refunded, "user_email": email,
        "first_order_item": {"product_name": product, "variant_name": "Standard"},
        "created_at": "2026-07-13T10:00:00Z", "identifier": "ord_"+oid}}


# ---------------------------------------------------------------- mapping
def test_a_paid_order_maps_to_SETTLED_business_revenue():
    r = order_to_row(_order("101", "paid", 4900))
    assert r["source"] == "lemonsqueezy:101"
    assert r["amount_usd"] == 49.0          # cents -> dollars
    assert r["state"] == "SETTLED"
    assert r["domain"] == "BUSINESS"
    assert r["product"] == "HSF StoryBoard"
    assert r["evidence"] and r["evidence"] != "NONE"   # order id/receipt = real evidence


def test_a_pending_order_is_PENDING_not_settled():
    r = order_to_row(_order("102", "pending", 4900))
    assert r["state"] == "PENDING"


def test_a_refunded_order_is_not_revenue():
    assert order_to_row(_order("103", "paid", 4900, refunded=True)) is None


def test_a_failed_order_is_not_revenue():
    assert order_to_row(_order("104", "failed", 4900)) is None


# ---------------------------------------------------------------- reconcile (idempotent, fail-closed)
class _FakeLedger:
    def __init__(self, existing=()):
        self._sources = set(existing); self.appended = []
    def existing_sources(self):
        return set(self._sources)
    def record_revenue(self, **row):
        self.appended.append(row); self._sources.add(row["source"]); return row


def test_reconcile_appends_new_orders_only():
    led = _FakeLedger(existing={"lemonsqueezy:101"})   # 101 already captured
    orders = [_order("101", "paid", 4900), _order("102", "paid", 1900)]
    added = reconcile_orders(orders, led)
    assert [a["source"] for a in added] == ["lemonsqueezy:102"]   # 101 skipped, only 102 new
    assert len(led.appended) == 1


def test_reconcile_is_idempotent_on_a_second_run():
    led = _FakeLedger()
    orders = [_order("201", "paid", 9900)]
    first = reconcile_orders(orders, led)
    second = reconcile_orders(orders, led)       # same orders again
    assert len(first) == 1 and second == []      # nothing double-counted


def test_reconcile_skips_refunded_and_failed():
    led = _FakeLedger()
    orders = [_order("301", "paid", 4900, refunded=True), _order("302", "failed", 4900),
              _order("303", "paid", 4900)]
    added = reconcile_orders(orders, led)
    assert [a["source"] for a in added] == ["lemonsqueezy:303"]
