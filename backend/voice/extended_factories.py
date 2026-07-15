"""Observe declared factories that are not full BRAIN-registry entries.

HSF / HCF / HFF / HPF / HHF — honest PARTIAL observation from real files.
Never claim LIVE revenue or secure posture without evidence.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.voice.policy import load_voice_policy
from backend.voice.sanitizer import sanitize_for_speech

ROOT = Path(__file__).resolve().parents[2]
UNKNOWN = "UNKNOWN"

_PLACEHOLDER_MARKERS = (
    "REPLACE_ME",
    "your_",
    "xxx",
    "changeme",
    "placeholder",
    "TODO",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fresh(mtime: Optional[float]) -> str:
    if mtime is None:
        return "UNKNOWN"
    budget = float(load_voice_policy().get("freshness_budget_seconds") or 300)
    return "STALE" if (time.time() - mtime) > budget else "LIVE"


def _env_status(path: Path, keys: List[str]) -> Dict[str, str]:
    """Classify env keys as SET | PLACEHOLDER | MISSING without speaking secret values."""
    out = {k: "MISSING" for k in keys}
    if not path.exists():
        return out
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return out
    for key in keys:
        m = re.search(rf"^{re.escape(key)}=(.*)$", text, flags=re.MULTILINE)
        if not m:
            continue
        val = m.group(1).strip().strip("\"'")
        if not val:
            out[key] = "MISSING"
        elif any(p.lower() in val.lower() for p in _PLACEHOLDER_MARKERS):
            out[key] = "PLACEHOLDER"
        elif key == "STRIPE_SECRET_KEY" and not (
            val.startswith("sk_test_") or val.startswith("sk_live_")
        ):
            out[key] = "PLACEHOLDER"
        else:
            out[key] = "SET"
    return out


def observe_hsf() -> Dict[str, Any]:
    """Hoch Storybook Factory — Story Studio product path + Stripe config honesty."""
    deploy = ROOT / "hsf" / "deploy"
    pricing_p = deploy / "pricing.config.json"
    vercel_p = deploy / "vercel.json"
    env_p = deploy / ".env"
    env_example = deploy / ".env.example"
    studio = ROOT / "hsf" / "story-studio-v2.html"
    engine = ROOT / "hsf" / "story-engine.js"

    labels: Dict[str, str] = {"factory": "PARTIAL", "product_tree": "UNKNOWN", "stripe": "UNKNOWN", "revenue": "UNKNOWN"}
    parts = ["HSF — Hoch Storybook Factory (Story Studio path)."]
    data: Dict[str, Any] = {"registry": "DECLARED_OBSERVABLE", "code": "HSF"}

    tree_ok = studio.exists() or engine.exists() or deploy.exists()
    labels["product_tree"] = "LIVE" if tree_ok else "UNKNOWN"
    parts.append(
        f"Product tree: {'observed' if tree_ok else 'UNKNOWN'} "
        f"(studio={studio.exists()}, engine={engine.exists()}, deploy={deploy.exists()})."
    )

    pricing = None
    if pricing_p.exists():
        try:
            pricing = json.loads(pricing_p.read_text(encoding="utf-8"))
            tiers = pricing.get("tiers") or []
            labels["pricing"] = _fresh(pricing_p.stat().st_mtime)
            tier_bits = [
                f"{t.get('id')} ${t.get('price')}/{t.get('interval')}"
                for t in tiers
                if isinstance(t, dict)
            ]
            parts.append(
                f"Pricing config observed ({labels['pricing']}): "
                + (", ".join(tier_bits) if tier_bits else "no tiers")
                + "."
            )
            data["tiers"] = tier_bits
        except Exception as e:
            labels["pricing"] = "UNKNOWN"
            parts.append(f"Pricing config unreadable: {e}.")
    else:
        labels["pricing"] = "UNKNOWN"
        parts.append("Pricing config: UNKNOWN — missing.")

    labels["vercel"] = "LIVE" if vercel_p.exists() else "UNKNOWN"
    parts.append(f"vercel.json: {'present' if vercel_p.exists() else 'UNKNOWN'}.")

    stripe_keys = [
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "STRIPE_PRICE_ONESTORY",
        "STRIPE_PRICE_CREATORS",
        "BASE_URL",
    ]
    env_status = _env_status(env_p if env_p.exists() else env_example, stripe_keys)
    # Prefer real .env if present for status; never read secrets into speech
    if env_p.exists():
        env_status = _env_status(env_p, stripe_keys)
        data["env_file"] = "hsf/deploy/.env"
    else:
        data["env_file"] = "hsf/deploy/.env.example (template only)"
        parts.append("Local .env not present — reporting template/example status only.")

    set_n = sum(1 for v in env_status.values() if v == "SET")
    ph_n = sum(1 for v in env_status.values() if v == "PLACEHOLDER")
    miss_n = sum(1 for v in env_status.values() if v == "MISSING")
    data["stripe_env_status"] = env_status  # values are SET/PLACEHOLDER/MISSING only
    if set_n == len(stripe_keys):
        labels["stripe"] = "LIVE"
        parts.append(f"Stripe env: all {set_n} required keys SET (values not spoken).")
    elif set_n > 0:
        labels["stripe"] = "PARTIAL"
        parts.append(
            f"Stripe env PARTIAL: {set_n} SET, {ph_n} PLACEHOLDER, {miss_n} MISSING. "
            f"Keys: "
            + ", ".join(f"{k}={v}" for k, v in env_status.items())
            + "."
        )
    else:
        labels["stripe"] = "UNKNOWN"
        parts.append(
            "Stripe env: no SET keys observed — revenue path not proven. "
            + ", ".join(f"{k}={v}" for k, v in env_status.items())
            + "."
        )

    # Revenue: HochLedger SETTLED verified only
    try:
        from backend.voice.revenue import observe_revenue

        rev = observe_revenue()
        rd = rev.get("data") or {}
        settled = rd.get("revenue_settled_usd")
        by_prod = rd.get("revenue_by_product") or {}
        labels["revenue"] = (rev.get("labels") or {}).get("revenue") or "UNKNOWN"
        labels["earning"] = (rev.get("labels") or {}).get("earning") or "NONE"
        if settled and float(settled) > 0:
            hsf_amt = None
            for k, v in by_prod.items():
                if "hsf" in str(k).lower() or "story" in str(k).lower():
                    hsf_amt = v
            parts.append(
                f"Verified settled revenue (ledger): ${float(settled):.2f} total"
                + (f"; HSF-related ${float(hsf_amt):.2f}" if hsf_amt is not None else "")
                + ". Stripe dashboard is not used as truth."
            )
            data["revenue_settled_usd"] = settled
            data["revenue_by_product"] = by_prod
        else:
            parts.append(
                "Verified settled revenue: $0.00 observed (or none). "
                "EARNING not claimed. I will not invent Stripe balances."
            )
            data["revenue_settled_usd"] = 0.0 if settled == 0 or settled == 0.0 else None
    except Exception as e:
        labels["revenue"] = "UNKNOWN"
        parts.append(f"Revenue ledger: UNKNOWN — {e}.")

    parts.append(
        "DOORSTEP: live Stripe keys, production deploy, and money moves require founder. "
        "Voice will not execute them."
    )

    # Overall
    if not tree_ok and labels["stripe"] == "UNKNOWN":
        status = "UNKNOWN"
    elif labels["stripe"] == "LIVE" and tree_ok:
        status = "PARTIAL"  # still PARTIAL without proven revenue
        labels["factory"] = "PARTIAL"
    else:
        status = "PARTIAL"
        labels["factory"] = "PARTIAL"

    return {
        "truth_class": "HELM_VOICE_FACTORY",
        "status": status,
        "code": "HSF",
        "title": "Hoch Storybook Factory",
        "registry": "DECLARED_OBSERVABLE",
        "observed_at": _now(),
        "speech_text": sanitize_for_speech(" ".join(parts)),
        "labels": labels,
        "data": data,
        "doorstep": ["stripe_live", "deploy_prod", "spend", "move_money"],
    }


def observe_hcf() -> Dict[str, Any]:
    """Cybersecurity factory lens from ConMon + cyber swarm state."""
    pos_p = ROOT / "coordination" / "security" / "helm_control_posture.json"
    cyber_p = ROOT / "data" / "prompt_brain" / "cyber_swarm_state.json"
    ledger_p = ROOT / "coordination" / "security" / "conmon_ledger.jsonl"

    parts = ["HCF — Cybersecurity factory lens (control-plane observe, not full registry)."]
    labels: Dict[str, str] = {"factory": "PARTIAL"}
    data: Dict[str, Any] = {"code": "HCF", "registry": "DECLARED_OBSERVABLE"}

    posture = None
    if pos_p.exists():
        try:
            posture = json.loads(pos_p.read_text(encoding="utf-8"))
            labels["posture"] = _fresh(pos_p.stat().st_mtime)
            pct = posture.get("posture_percent")
            impl = posture.get("implemented")
            assessed = posture.get("controls_assessed")
            open_f = posture.get("open_findings")
            high_f = posture.get("high_findings")
            fw = posture.get("framework") or "NIST"
            parts.append(
                f"{fw} posture {pct}% ({impl}/{assessed} implemented), "
                f"open findings {open_f}, high {high_f} [{labels['posture']}]."
            )
            gaps = []
            for c in posture.get("controls") or []:
                if isinstance(c, dict) and str(c.get("status", "")).upper() not in (
                    "IMPLEMENTED",
                    "PASS",
                ):
                    gaps.append(f"{c.get('control_id')}:{c.get('status')}")
            if gaps:
                parts.append("Control gaps: " + ", ".join(gaps[:8]) + ".")
            data["posture_percent"] = pct
            data["open_findings"] = open_f
            data["high_findings"] = high_f
            data["gaps"] = gaps[:12]
        except Exception as e:
            labels["posture"] = "UNKNOWN"
            parts.append(f"Control posture unreadable: {e}.")
    else:
        labels["posture"] = "UNKNOWN"
        parts.append("Control posture: UNKNOWN — file missing.")

    if cyber_p.exists():
        try:
            cyber = json.loads(cyber_p.read_text(encoding="utf-8"))
            labels["cyber_swarm"] = _fresh(cyber_p.stat().st_mtime)
            parts.append(
                f"Cyber swarm verdict {cyber.get('verdict')}, "
                f"coverage {cyber.get('detection_coverage_pct')}%, "
                f"real HIGH {cyber.get('real_high')} [{labels['cyber_swarm']}]. "
                f"Why: {str(cyber.get('why') or '')[:160]}"
            )
            data["cyber_verdict"] = cyber.get("verdict")
            data["detection_coverage_pct"] = cyber.get("detection_coverage_pct")
        except Exception as e:
            labels["cyber_swarm"] = "UNKNOWN"
            parts.append(f"Cyber swarm state unreadable: {e}.")
    else:
        labels["cyber_swarm"] = "UNKNOWN"
        parts.append("Cyber swarm state: UNKNOWN.")

    if ledger_p.exists():
        try:
            lines = [ln for ln in ledger_p.read_text(encoding="utf-8").splitlines() if ln.strip()]
            last = json.loads(lines[-1]) if lines else {}
            labels["conmon"] = _fresh(ledger_p.stat().st_mtime)
            parts.append(
                f"ConMon ledger rows {len(lines)}; last posture {last.get('posture_percent')}% "
                f"gaps {last.get('gaps')} [{labels['conmon']}]."
            )
            data["conmon_rows"] = len(lines)
            data["conmon_last_gaps"] = last.get("gaps")
        except Exception as e:
            labels["conmon"] = "UNKNOWN"
            parts.append(f"ConMon ledger unreadable: {e}.")
    else:
        labels["conmon"] = "UNKNOWN"

    # Goal critical path
    goal_p = ROOT / "coordination" / "goal" / "goal_state.json"
    if goal_p.exists():
        try:
            g = json.loads(goal_p.read_text(encoding="utf-8"))
            blocker = (g.get("metrics") or {}).get("current_critical_path_blocker")
            if blocker:
                parts.append(f"Goal critical path blocker: {blocker}.")
                data["critical_path_blocker"] = blocker
                if "SECURITY" in str(blocker).upper():
                    parts.append("Security is on the critical path — this is the binding constraint.")
        except Exception:
            pass

    parts.append("Voice will not disable controls or bypass security gates.")
    status = "PARTIAL"
    if labels.get("posture") == "UNKNOWN" and labels.get("cyber_swarm") == "UNKNOWN":
        status = "UNKNOWN"
        labels["factory"] = "UNKNOWN"
    return {
        "truth_class": "HELM_VOICE_FACTORY",
        "status": status,
        "code": "HCF",
        "title": "Hoch Cybersecurity Factory",
        "registry": "DECLARED_OBSERVABLE",
        "observed_at": _now(),
        "speech_text": sanitize_for_speech(" ".join(parts)),
        "labels": labels,
        "data": data,
        "doorstep": ["disable_controls", "bypass_approval", "public_exposure"],
    }


def observe_hff() -> Dict[str, Any]:
    """Finance factory lens — spend + northstar; revenue UNKNOWN without ledger dollars."""
    parts = ["HFF — Finance factory lens."]
    labels: Dict[str, str] = {"factory": "PARTIAL", "spend": "UNKNOWN", "revenue": "UNKNOWN", "northstar": "UNKNOWN"}
    data: Dict[str, Any] = {"code": "HFF", "registry": "DECLARED_OBSERVABLE"}

    try:
        import backend.helm_live_api as helm

        spend = helm.live_spend()
        if isinstance(spend, dict) and spend.get("state") == UNKNOWN:
            parts.append(f"Spend: UNKNOWN — {spend.get('reason')}.")
        else:
            labels["spend"] = "LIVE"
            parts.append(f"Spend observed: {str(spend)[:280]}")
            data["spend"] = spend
    except Exception as e:
        parts.append(f"Spend: UNKNOWN — {e}.")

    try:
        import backend.helm_live_api as helm

        ns = helm.live_northstar()
        if isinstance(ns, dict) and ns.get("state") == UNKNOWN:
            parts.append(f"North-star money metric: UNKNOWN — {ns.get('reason')}.")
        else:
            labels["northstar"] = "LIVE"
            parts.append(f"North-star ledger: {str(ns)[:280]}")
            data["northstar"] = ns
    except Exception as e:
        parts.append(f"North-star ledger: UNKNOWN — {e}.")

    hsf = observe_hsf()
    stripe = (hsf.get("labels") or {}).get("stripe")
    parts.append(f"HSF Stripe env path status: {stripe}.")
    data["hsf_stripe"] = stripe
    try:
        from backend.voice.revenue import observe_revenue

        rev = observe_revenue()
        parts.append(rev.get("speech_text") or "Revenue: UNKNOWN.")
        labels["revenue"] = (rev.get("labels") or {}).get("revenue") or "UNKNOWN"
        labels["earning"] = (rev.get("labels") or {}).get("earning") or "NONE"
        data["revenue"] = rev.get("data")
    except Exception as e:
        labels["revenue"] = "UNKNOWN"
        parts.append(f"Revenue: UNKNOWN — {e}.")
    parts.append("Voice will not move money or flip Stripe live.")

    status = "PARTIAL" if labels["spend"] == "LIVE" or labels["northstar"] == "LIVE" else "UNKNOWN"
    if status == "UNKNOWN":
        labels["factory"] = "UNKNOWN"
    return {
        "truth_class": "HELM_VOICE_FACTORY",
        "status": status,
        "code": "HFF",
        "title": "Hoch Finance Factory",
        "registry": "DECLARED_OBSERVABLE",
        "observed_at": _now(),
        "speech_text": sanitize_for_speech(" ".join(parts)),
        "labels": labels,
        "data": data,
        "doorstep": ["spend", "move_money", "stripe_live"],
    }


def observe_hpf() -> Dict[str, Any]:
    """Prompt factory lens — prompt_brain software domain as proxy."""
    parts = ["HPF — Prompt factory lens (prompt_brain observe)."]
    labels: Dict[str, str] = {"factory": "PARTIAL"}
    data: Dict[str, Any] = {"code": "HPF", "registry": "DECLARED_OBSERVABLE"}
    brain = ROOT / "data" / "prompt_brain"
    paths = {
        "gene_pool": brain / "gene_pool_m0.json",
        "champions": brain / "champion_registry.json",
        "convergence": brain / "convergence_status.json",
        "gap": brain / "gap_analysis.json",
    }
    for name, p in paths.items():
        if not p.exists():
            labels[name] = "UNKNOWN"
            parts.append(f"{name}: UNKNOWN.")
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            labels[name] = _fresh(p.stat().st_mtime)
            if name == "gene_pool":
                g = d.get("genes")
                n = len(g) if isinstance(g, (dict, list)) else UNKNOWN
                parts.append(f"Genes {n} [{labels[name]}].")
                data["gene_count"] = n
            elif name == "champions":
                c = d.get("champions")
                n = len(c) if isinstance(c, (dict, list)) else UNKNOWN
                parts.append(f"Champions {n} [{labels[name]}].")
                data["champion_count"] = n
            elif name == "convergence":
                parts.append(
                    f"Convergence state {d.get('state')}, mean {d.get('mean_score')} [{labels[name]}]."
                )
                data["convergence_state"] = d.get("state")
            elif name == "gap":
                parts.append(f"Gap analysis present [{labels[name]}].")
        except Exception as e:
            labels[name] = "UNKNOWN"
            parts.append(f"{name} unreadable: {e}.")

    status = "PARTIAL" if any(v == "LIVE" for v in labels.values()) else "UNKNOWN"
    return {
        "truth_class": "HELM_VOICE_FACTORY",
        "status": status,
        "code": "HPF",
        "title": "Hoch Prompt Factory",
        "registry": "DECLARED_OBSERVABLE",
        "observed_at": _now(),
        "speech_text": sanitize_for_speech(" ".join(parts)),
        "labels": labels,
        "data": data,
        "doorstep": ["T3_publish"],
    }


def observe_hhf() -> Dict[str, Any]:
    """Home factory — HomeMesh signals if present."""
    parts = ["HHF — Home factory lens."]
    labels: Dict[str, str] = {"factory": "PARTIAL"}
    data: Dict[str, Any] = {"code": "HHF", "registry": "DECLARED_OBSERVABLE"}
    # Tracker file often used for homemesh devices
    dev_p = ROOT / "has_live_project_tracker" / "data" / "homemesh_manual_devices.json"
    if dev_p.exists():
        try:
            d = json.loads(dev_p.read_text(encoding="utf-8"))
            labels["devices"] = _fresh(dev_p.stat().st_mtime)
            n = len(d) if isinstance(d, list) else (len(d.keys()) if isinstance(d, dict) else UNKNOWN)
            parts.append(f"HomeMesh device file observed; entries {n} [{labels['devices']}].")
            data["device_entries"] = n
        except Exception as e:
            labels["devices"] = "UNKNOWN"
            parts.append(f"HomeMesh devices unreadable: {e}.")
    else:
        labels["devices"] = "UNKNOWN"
        parts.append("HomeMesh devices: UNKNOWN — no tracker file.")
    parts.append("Device approvals remain founder/operator gated.")
    status = "PARTIAL" if labels.get("devices") == "LIVE" else "UNKNOWN"
    if status == "UNKNOWN":
        labels["factory"] = "UNKNOWN"
    return {
        "truth_class": "HELM_VOICE_FACTORY",
        "status": status,
        "code": "HHF",
        "title": "Hoch Home Factory",
        "registry": "DECLARED_OBSERVABLE",
        "observed_at": _now(),
        "speech_text": sanitize_for_speech(" ".join(parts)),
        "labels": labels,
        "data": data,
        "doorstep": ["device_trust", "network_expose"],
    }


EXTENDED_OBSERVERS = {
    "HSF": observe_hsf,
    "HCF": observe_hcf,
    "HFF": observe_hff,
    "HPF": observe_hpf,
    "HHF": observe_hhf,
}
