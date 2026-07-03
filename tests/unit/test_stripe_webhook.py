"""Stripe webhook handler unit tests.

Tests signature verification, event dispatch, idempotency, and fail-closed
secret guard — all per Stripe webhook best practices.

Refs:
  [1] https://docs.stripe.com/webhooks#verify-official-libraries
  [2] https://docs.stripe.com/webhooks#handle-duplicate-events
  [3] https://docs.stripe.com/webhooks#best-practices
"""
import hashlib, hmac, importlib, json, time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_SECRET = "whsec_testsecret1234567890abcdef"
_SECRET_RAW = _SECRET.encode()


def _sign(payload: bytes, ts: int | None = None) -> str:
    """Produce a Stripe-Signature header value matching the SDK verification."""
    ts = ts or int(time.time())
    signed = f"{ts}.".encode() + payload
    sig = hmac.new(_SECRET_RAW, signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def _event(event_type: str, event_id: str = "evt_001", data: dict | None = None) -> bytes:
    """Minimal Stripe event envelope that satisfies the SDK deserialiser."""
    return json.dumps({
        "id": event_id,
        "object": "event",
        "type": event_type,
        "livemode": False,
        "created": int(time.time()),
        "data": {"object": data or {}},
        "pending_webhooks": 0,
        "request": {"id": None, "idempotency_key": None},
    }).encode()


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", _SECRET)
    import backend.routers.stripe_webhook as mod
    mod._seen_event_ids.clear()
    yield
    mod._seen_event_ids.clear()


@pytest.fixture()
def client():
    import backend.routers.stripe_webhook as mod
    importlib.reload(mod)
    a = FastAPI()
    a.include_router(mod.router)
    return TestClient(a)


def _post(client, payload: bytes, sig: str | None = None):
    return client.post(
        "/api/stripe/webhook",
        content=payload,
        headers={"stripe-signature": sig or _sign(payload)},
    )


# -- Rejection tests ---------------------------------------------------------

def test_missing_signature_returns_400(client):
    r = client.post("/api/stripe/webhook", content=b"{}")
    assert r.status_code == 400, r.text
    assert "Stripe-Signature" in r.text


def test_invalid_signature_returns_400(client):
    payload = _event("invoice.paid")
    r = client.post("/api/stripe/webhook", content=payload,
                    headers={"stripe-signature": "t=1,v1=badhash"})
    assert r.status_code == 400


def test_missing_secret_returns_500(monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    import backend.routers.stripe_webhook as mod
    importlib.reload(mod)
    a = FastAPI()
    a.include_router(mod.router)
    c = TestClient(a, raise_server_exceptions=False)
    payload = _event("invoice.paid")
    r = c.post("/api/stripe/webhook", content=payload,
               headers={"stripe-signature": _sign(payload)})
    assert r.status_code == 500


# -- Acceptance tests --------------------------------------------------------

@pytest.mark.parametrize("event_type", [
    "checkout.session.completed",
    "invoice.paid",
    "invoice.payment_failed",
    "customer.subscription.updated",
    "customer.subscription.deleted",
])
def test_handled_event_returns_200(client, event_type):
    payload = _event(event_type)
    r = _post(client, payload)
    assert r.status_code == 200, f"{event_type}: {r.text}"


def test_unknown_event_returns_200_no_retry_storm(client):
    """Unhandled event types must return 200 to prevent Stripe retry storms.
    https://docs.stripe.com/webhooks#best-practices
    """
    payload = _event("some.future.event.type")
    r = _post(client, payload)
    assert r.status_code == 200


def test_duplicate_event_idempotent(client):
    """Same event_id delivered twice must both return 200.
    https://docs.stripe.com/webhooks#handle-duplicate-events
    """
    payload = _event("invoice.paid", event_id="evt_dupe_001")
    r1 = _post(client, payload)
    r2 = _post(client, payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert "duplicate" in r2.text
