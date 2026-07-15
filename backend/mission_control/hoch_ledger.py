"""HOCH LEDGER — the missing half of the North Star.

WHY THIS EXISTS
---------------
The canonical North Star optimizes:

        verified_founder_minutes_per_shipped_dollar     (MINIMIZE)

That metric has THREE terms. Before this module, only one of them had an instrument:

    dollars OUT (spend)     -> metered, hash-chained            (spend_meter.py)
    dollars IN  (revenue)   -> NEVER MEASURED. 0 rows, every table.
    founder MINUTES         -> NEVER MEASURED.

Two of the three terms in the founder's own primary metric had no instrument, so the
metric has never once been computable. HELM could tell you it burned $0.02 and produced
a validated poem. It could not tell you whether it made a cent, or what it cost you in
your own time. A factory that cannot see revenue is a hobby with good paperwork.

DOCTRINE (identical to spend_meter)
-----------------------------------
  * Revenue is OBSERVED, never projected. A forecast is not income.
  * Every entry is append-only and hash-chained -> you cannot quietly invent a sale.
  * If revenue is zero, the North Star metric is UNDEFINED, not "infinity" and not a
    flattering placeholder. Dividing by zero dollars is exactly as dishonest as a
    fabricated PASS.
  * Founder minutes are logged at the DOORSTEP -- every time Michael had to appear.
    That number going UP is the system failing at its actual purpose.

DOMAINS
-------
Michael runs three books, and they must never be silently mixed:
    BUSINESS  -- products intended to be sold. The only domain that may produce revenue.
    PERSONAL  -- household, finance, life admin. Cost centre. Never "revenue".
    HOBBY     -- music, stories, experiments. May become BUSINESS by explicit promotion.
"""
from __future__ import annotations

import datetime
import fcntl
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

REVENUE_LEDGER = ROOT / "coordination" / "council" / "revenue_ledger.jsonl"
FOUNDER_LEDGER = ROOT / "coordination" / "council" / "founder_minutes.jsonl"

DOMAINS = ("BUSINESS", "PERSONAL", "HOBBY")

# Revenue only counts when money actually arrived. Anything else is a SIGNAL, not income.
REVENUE_STATES = (
    "SETTLED",      # money is in the account. This is the ONLY state that counts.
    "PENDING",      # charged, not yet settled. Counted separately, never as cash.
    "REFUNDED",     # negative.
)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class _Chain:
    """Append-only, hash-chained JSONL. Editing a row breaks the chain."""

    def __init__(self, path: Path):
        self.path = path

    def entries(self) -> List[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text().splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        return out

    def append(self, entry: dict) -> dict:
        # AU-9 continuity fix: the read-last + append must be atomic across
        # processes, else concurrent writers fork the chain (link discontinuity).
        # Serialize the critical section under an exclusive cross-process flock.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_suffix(self.path.suffix + ".wlock")
        with open(lock_path, "w") as _lock:
            fcntl.flock(_lock.fileno(), fcntl.LOCK_EX)
            try:
                e = self.entries()
                body = dict(entry)
                body["prev_hash"] = e[-1]["entry_hash"] if e else "GENESIS"
                body["entry_hash"] = hashlib.sha256(
                    json.dumps(body, sort_keys=True).encode()).hexdigest()
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(body, sort_keys=True) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
            finally:
                fcntl.flock(_lock.fileno(), fcntl.LOCK_UN)
        return body

    def _entries_consistent(self) -> List[dict]:
        """Read under a SHARED flock so a concurrent append (holding the EXCLUSIVE
        flock) cannot cause a torn-read false break. Not called inside append()."""
        if not self.path.exists():
            return []
        lock_path = self.path.with_suffix(self.path.suffix + ".wlock")
        with open(lock_path, "a") as _lock:
            fcntl.flock(_lock.fileno(), fcntl.LOCK_SH)
            try:
                text = self.path.read_text()
            finally:
                fcntl.flock(_lock.fileno(), fcntl.LOCK_UN)
        out = []
        for line in text.splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
        return out

    def verify(self) -> tuple[bool, List[str]]:
        prev, bad = "GENESIS", []
        for i, e in enumerate(self._entries_consistent()):
            if e.get("prev_hash") != prev:
                bad.append(f"row {i}: prev_hash mismatch")
            body = {k: v for k, v in e.items() if k != "entry_hash"}
            if hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() \
                    != e.get("entry_hash"):
                bad.append(f"row {i}: entry_hash mismatch (row was edited)")
            prev = e.get("entry_hash", "")
        return (not bad), bad


class HochLedger:
    """Revenue + founder-minutes, per domain. The other half of the P&L."""

    def __init__(self):
        self.revenue = _Chain(REVENUE_LEDGER)
        self.founder = _Chain(FOUNDER_LEDGER)

    # ------------------------------------------------------------- revenue
    def record_revenue(self, *, product: str, domain: str, amount_usd: float,
                       state: str, source: str, buyer_ref: Optional[str] = None,
                       evidence: Optional[str] = None) -> dict:
        """Record money that ACTUALLY arrived. `evidence` must point at a real receipt."""
        if domain not in DOMAINS:
            raise ValueError(f"domain must be one of {DOMAINS}, got {domain!r}")
        if state not in REVENUE_STATES:
            raise ValueError(f"state must be one of {REVENUE_STATES}, got {state!r}")
        if domain != "BUSINESS" and amount_usd > 0:
            # A hobby does not have customers until you promote it. Say so out loud.
            raise ValueError(
                f"revenue recorded against {domain}; only BUSINESS may earn. "
                "Promote the product to BUSINESS first (explicit founder decision).")
        return self.revenue.append({
            "ts": _now().isoformat(), "product": product, "domain": domain,
            "amount_usd": round(float(amount_usd), 4), "state": state,
            "source": source, "buyer_ref": buyer_ref,
            "evidence": evidence or "NONE",
            # Provenance: a sale with no evidence is a claim, not income.
            "verified": bool(evidence),
        })

    def revenue_settled_usd(self) -> float:
        return round(sum(e["amount_usd"] for e in self.revenue.entries()
                         if e.get("state") == "SETTLED" and e.get("verified")), 4)

    def revenue_by_product(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for e in self.revenue.entries():
            if e.get("state") == "SETTLED" and e.get("verified"):
                out[e["product"]] = round(out.get(e["product"], 0.0) + e["amount_usd"], 4)
        return out

    # ------------------------------------------------- founder minutes (DOORSTEP)
    def record_founder_minutes(self, *, minutes: float, reason: str,
                               category: str, product: Optional[str] = None) -> dict:
        """Every minute Michael had to appear. Rising = the system is failing him."""
        return self.founder.append({
            "ts": _now().isoformat(), "minutes": round(float(minutes), 2),
            "reason": reason, "category": category, "product": product,
        })

    def founder_minutes_total(self) -> float:
        return round(sum(e["minutes"] for e in self.founder.entries()), 2)

    # ------------------------------------------------------------ north star
    def north_star(self) -> Dict[str, Any]:
        """verified_founder_minutes_per_shipped_dollar — computed, or honestly UNDEFINED."""
        try:
            from backend.mission_control.spend_meter import SpendMeter
            spend = SpendMeter().spent_total_usd()
        except Exception:
            spend = None

        rev = self.revenue_settled_usd()
        mins = self.founder_minutes_total()
        ok_r, bad_r = self.revenue.verify()
        ok_f, bad_f = self.founder.verify()

        if rev <= 0:
            metric: Any = "UNDEFINED"
            reason = ("no verified settled revenue exists, so minutes-per-dollar has no "
                      "denominator. This is NOT infinity and NOT zero -- it is undefined, "
                      "and the factory has not yet done the thing it exists to do.")
        else:
            metric = round(mins / rev, 3)
            reason = "founder minutes divided by verified settled dollars"

        return {
            "metric": "verified_founder_minutes_per_shipped_dollar",
            "value": metric,
            "reason": reason,
            "founder_minutes_total": mins,
            "revenue_settled_usd": rev,
            "revenue_by_product": self.revenue_by_product(),
            "spend_total_usd": spend if spend is not None else "UNKNOWN",
            "net_usd": (round(rev - spend, 4) if spend is not None else "UNKNOWN"),
            "revenue_chain_valid": ok_r,
            "founder_chain_valid": ok_f,
            "chain_errors": (bad_r + bad_f)[:3],
            "lifetime_sales": len([e for e in self.revenue.entries()
                                   if e.get("state") == "SETTLED"]),
            "doctrine": "revenue is OBSERVED and evidenced; a forecast is never income",
        }

    def summary(self) -> Dict[str, Any]:
        ns = self.north_star()
        by_domain: Dict[str, float] = {d: 0.0 for d in DOMAINS}
        for e in self.revenue.entries():
            if e.get("state") == "SETTLED" and e.get("verified"):
                by_domain[e["domain"]] = round(
                    by_domain.get(e["domain"], 0.0) + e["amount_usd"], 4)
        return {**ns, "by_domain": by_domain}
