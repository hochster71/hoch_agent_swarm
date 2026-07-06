"""Billing scaffolding tests — fully offline (no live Stripe calls).

Covers:
  * mode guard fail-closed logic (test / live / test_locked / disabled)
  * catalog structural integrity + all three founder-chosen models present
  * checkout endpoint: subscription vs one-time, free rejection, mode gating
  * webhook -> entitlements provisioning (grant / revoke)
"""
import importlib

import pytest
import stripe
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.billing import catalog as catalog_mod
from backend.billing import entitlements
from backend.billing import mode as billing_mode


# ----------------------------- mode guard --------------------------------
def test_mode_test_key(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    monkeypatch.delenv("HASF_BILLING_LIVE", raising=False)
    assert billing_mode.effective_mode() == billing_mode.MODE_TEST
    assert billing_mode.can_charge() is True
    assert billing_mode.stripe_price_field() == "test_price_id"


def test_mode_live_key_without_switch_is_locked(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_abc")
    monkeypatch.delenv("HASF_BILLING_LIVE", raising=False)
    # live key present but founder switch OFF -> must NOT be allowed to charge live
    assert billing_mode.effective_mode() == billing_mode.MODE_TEST_LOCKED
    assert billing_mode.can_charge() is False


def test_mode_live_requires_both_key_and_switch(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_abc")
    monkeypatch.setenv("HASF_BILLING_LIVE", "1")
    assert billing_mode.effective_mode() == billing_mode.MODE_LIVE
    assert billing_mode.stripe_price_field() == "live_price_id"


def test_mode_disabled_without_key(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")
    assert billing_mode.effective_mode() == billing_mode.MODE_DISABLED
    assert billing_mode.can_charge() is False


# ------------------------------ catalog ----------------------------------
def test_catalog_is_structurally_valid():
    assert catalog_mod.validate() == []


def test_catalog_has_all_three_models():
    kinds = {t["kind"] for t in catalog_mod.tiers()}
    assert {"freemium", "subscription", "one_time"} <= kinds


def test_public_catalog_leaks_no_price_ids():
    pub = catalog_mod.public_catalog()
    dumped = str(pub)
    assert "test_price_id" not in dumped and "REPLACE_" not in dumped and "sk_" not in dumped


# ------------------------------ checkout ---------------------------------
def _client():
    from backend.routers.stripe_billing import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_checkout_subscription_mode(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    monkeypatch.setattr(catalog_mod, "resolve_price_id", lambda t: "price_test_123")
    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return {"id": "cs_test_1", "url": "https://checkout.stripe.test/cs_test_1"}

    monkeypatch.setattr(stripe.checkout.Session, "create", staticmethod(fake_create))
    r = _client().post("/api/stripe/checkout", json={"tier_id": "pro_monthly"})
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "subscription"
    assert captured["mode"] == "subscription"
    assert captured["metadata"]["tier_id"] == "pro_monthly"


def test_checkout_one_time_mode(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    monkeypatch.setattr(catalog_mod, "resolve_price_id", lambda t: "price_test_lt")
    monkeypatch.setattr(
        stripe.checkout.Session, "create",
        staticmethod(lambda **k: {"id": "cs_test_2", "url": "https://checkout.test/2"}),
    )
    r = _client().post("/api/stripe/checkout", json={"tier_id": "lifetime"})
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "payment"


def test_checkout_free_tier_rejected(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
    r = _client().post("/api/stripe/checkout", json={"tier_id": "free"})
    assert r.status_code == 400


def test_checkout_blocked_when_disabled(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "")
    r = _client().post("/api/stripe/checkout", json={"tier_id": "pro_monthly"})
    assert r.status_code == 503


def test_checkout_blocked_when_live_key_no_switch(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_abc")
    monkeypatch.delenv("HASF_BILLING_LIVE", raising=False)
    r = _client().post("/api/stripe/checkout", json={"tier_id": "pro_monthly"})
    assert r.status_code == 409


# --------------------------- webhook -> entitlements ---------------------
def _webhook_client():
    from backend.routers.stripe_webhook import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_webhook_checkout_completed_grants_lifetime(monkeypatch, tmp_path):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(entitlements, "_STORE", tmp_path / "ent.json")
    fake_event = {
        "id": "evt_1", "type": "checkout.session.completed",
        "data": {"object": {"customer": "cus_1", "mode": "payment",
                            "subscription": None, "metadata": {"tier": "pro"}}},
    }
    monkeypatch.setattr(stripe.Webhook, "construct_event", staticmethod(lambda **k: fake_event))
    r = _webhook_client().post("/api/stripe/webhook", content=b"{}",
                               headers={"stripe-signature": "t=1,v1=x"})
    assert r.status_code == 200
    rec = entitlements.get("cus_1")
    assert rec and rec["tier"] == "pro" and rec["lifetime"] is True and rec["status"] == "active"


def test_webhook_subscription_deleted_revokes(monkeypatch, tmp_path):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(entitlements, "_STORE", tmp_path / "ent.json")
    entitlements.grant("cus_2", "team", status="active", source_event="seed")
    fake_event = {
        "id": "evt_2", "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_2", "ended_at": 123}},
    }
    monkeypatch.setattr(stripe.Webhook, "construct_event", staticmethod(lambda **k: fake_event))
    r = _webhook_client().post("/api/stripe/webhook", content=b"{}",
                               headers={"stripe-signature": "t=1,v1=x"})
    assert r.status_code == 200
    rec = entitlements.get("cus_2")
    assert rec["status"] == "cancelled" and rec["tier"] == "free"
