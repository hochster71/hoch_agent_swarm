"""Verified revenue observation for voice — SETTLED + verified ledger only.

Doctrine from HochLedger:
  - Forecast is never income
  - Zero settled dollars → metric UNDEFINED / revenue UNKNOWN-as-zero-proven
  - Speak dollars only when chain-valid SETTLED verified rows exist
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from backend.voice.sanitizer import sanitize_for_speech

UNKNOWN = "UNKNOWN"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def observe_revenue() -> Dict[str, Any]:
    """Observe hash-chained revenue + north-star terms. Fail closed."""
    try:
        from backend.mission_control.hoch_ledger import HochLedger

        led = HochLedger()
        summary = led.summary()
    except Exception as e:
        return {
            "truth_class": "HELM_VOICE_REVENUE",
            "status": "UNKNOWN",
            "observed_at": _now(),
            "speech_text": sanitize_for_speech(
                f"Revenue ledger unreadable: {e}. Settled revenue UNKNOWN."
            ),
            "labels": {"revenue": "UNKNOWN", "north_star_metric": "UNKNOWN", "chain": "UNKNOWN"},
            "data": {"reason": str(e)},
        }

    rev = float(summary.get("revenue_settled_usd") or 0.0)
    chain_ok = bool(summary.get("revenue_chain_valid"))
    by_product = summary.get("revenue_by_product") or {}
    lifetime = summary.get("lifetime_sales")
    metric = summary.get("value")
    reason = summary.get("reason") or ""
    spend = summary.get("spend_total_usd")
    mins = summary.get("founder_minutes_total")

    labels: Dict[str, str] = {
        "revenue": "LIVE" if chain_ok else "CONTRADICTED",
        "north_star_metric": "LIVE" if metric not in (None, "UNDEFINED") else "UNDEFINED",
        "chain": "LIVE" if chain_ok else "CONTRADICTED",
    }

    parts = ["Revenue from verified hash-chained ledger only."]
    if not chain_ok:
        parts.append(
            "Revenue chain INVALID — dollars not trusted. Status CONTRADICTED. "
            f"Chain errors: {summary.get('chain_errors')}."
        )
        status = "CONTRADICTED"
        labels["revenue"] = "CONTRADICTED"
    elif rev <= 0:
        # Observed zero settled verified revenue — NOT fabricated green, NOT invented
        labels["revenue"] = "LIVE"  # we observed the ledger; amount is zero
        labels["earning"] = "NONE"
        parts.append(
            "Verified settled revenue: zero dollars. "
            "EARNING is not claimed. North-star minutes-per-dollar is UNDEFINED, not infinity."
        )
        status = "LIVE"
        if metric == "UNDEFINED":
            parts.append(f"Metric undefined reason: {reason[:200]}")
    else:
        labels["revenue"] = "LIVE"
        labels["earning"] = "LIVE"
        parts.append(f"Verified settled revenue: ${rev:.2f} USD across {lifetime} sale(s).")
        if by_product:
            bits = [f"{k} ${v:.2f}" for k, v in list(by_product.items())[:6]]
            parts.append("By product: " + ", ".join(bits) + ".")
        if metric != "UNDEFINED" and metric is not None:
            parts.append(f"Founder-minutes per shipped dollar: {metric}.")
        else:
            parts.append("Founder-minutes per shipped dollar: UNDEFINED.")
        status = "LIVE"

    if spend is not None and spend != "UNKNOWN":
        parts.append(f"Observed spend total: ${float(spend):.4f}.")
        labels["spend"] = "LIVE"
    else:
        parts.append("Spend total: UNKNOWN.")
        labels["spend"] = "UNKNOWN"

    if mins is not None:
        parts.append(f"Founder minutes logged: {mins}.")

    parts.append(
        "Stripe dashboard balances are not spoken unless written as SETTLED verified ledger rows. "
        "Forecasts are never income."
    )

    return {
        "truth_class": "HELM_VOICE_REVENUE",
        "status": status,
        "observed_at": _now(),
        "speech_text": sanitize_for_speech(" ".join(parts)),
        "labels": labels,
        "data": {
            "revenue_settled_usd": rev if chain_ok else None,
            "revenue_by_product": by_product if chain_ok else {},
            "lifetime_sales": lifetime,
            "north_star_value": metric,
            "north_star_reason": reason,
            "spend_total_usd": spend,
            "founder_minutes_total": mins,
            "revenue_chain_valid": chain_ok,
            "doctrine": summary.get("doctrine"),
        },
    }
