"""Entitlements store — the real (minimal) provisioning target for webhook events.

Turns the webhook's TODO stubs into actual grants/revokes so a completed test
checkout produces a durable record. JSON-backed for zero-infra; swap for the
swarm_ledger DB later without changing the webhook call sites.

Concurrency: single-process best-effort with an atomic replace on write. The
webhook is low-volume and idempotent upstream (seen-event guard), so this is
sufficient for the scaffolding phase.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_STORE = Path(__file__).resolve().parents[2] / "data" / "billing" / "entitlements.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    if _STORE.exists():
        try:
            return json.loads(_STORE.read_text())
        except Exception:
            return {"schema": "hasf-entitlements-v1", "customers": {}}
    return {"schema": "hasf-entitlements-v1", "customers": {}}


def _save(data: dict) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(_STORE.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, _STORE)  # atomic
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def grant(customer_id: str, tier: str, *, status: str = "active",
          access_until: Optional[str] = None, source_event: str = "",
          lifetime: bool = False) -> dict:
    """Provision or upgrade a customer's entitlement."""
    if not customer_id:
        return {}
    data = _load()
    rec = data["customers"].get(customer_id, {})
    rec.update({
        "tier": tier,
        "status": status,
        "access_until": access_until,
        "lifetime": lifetime or rec.get("lifetime", False),
        "updated_at": _now(),
        "last_source_event": source_event,
    })
    rec.setdefault("created_at", _now())
    data["customers"][customer_id] = rec
    _save(data)
    return rec


def extend(customer_id: str, access_until: Optional[str], source_event: str = "") -> dict:
    """Renewal — push the access window out."""
    if not customer_id:
        return {}
    data = _load()
    rec = data["customers"].get(customer_id)
    if not rec:
        return {}
    rec["access_until"] = access_until
    rec["status"] = "active"
    rec["updated_at"] = _now()
    rec["last_source_event"] = source_event
    data["customers"][customer_id] = rec
    _save(data)
    return rec


def mark_status(customer_id: str, status: str, source_event: str = "") -> dict:
    if not customer_id:
        return {}
    data = _load()
    rec = data["customers"].get(customer_id)
    if not rec:
        return {}
    rec["status"] = status
    rec["updated_at"] = _now()
    rec["last_source_event"] = source_event
    data["customers"][customer_id] = rec
    _save(data)
    return rec


def revoke(customer_id: str, source_event: str = "") -> dict:
    """Cancellation — revoke access but keep the record for history."""
    if not customer_id:
        return {}
    data = _load()
    rec = data["customers"].get(customer_id)
    if not rec:
        return {}
    if rec.get("lifetime"):
        # lifetime one-time buyers keep access even if a stray sub event fires
        rec["last_source_event"] = source_event
        data["customers"][customer_id] = rec
        _save(data)
        return rec
    rec["status"] = "cancelled"
    rec["tier"] = "free"
    rec["updated_at"] = _now()
    rec["last_source_event"] = source_event
    data["customers"][customer_id] = rec
    _save(data)
    return rec


def get(customer_id: str) -> Optional[dict]:
    return _load()["customers"].get(customer_id)


def all_customers() -> dict:
    return _load()["customers"]
