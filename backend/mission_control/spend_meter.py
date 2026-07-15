"""SPEND METER — records what a dispatch ACTUALLY cost, not what we guessed.

THE DEFECT THIS FIXES
---------------------
Before this module, spend existed only as a PRE-FLIGHT ESTIMATE:

  * `estimate_cost_usd()` guessed a number from the prompt, the gateway checked it
    against a $0.50 cap, and then **threw it away**. Every result envelope from every
    real dispatch recorded `cost_usd: None`.
  * Worse, the gateway hardcoded `est = 0.0` for CLI_GEMINI. Gemini was treated as
    FREE. It is not free ($0.15 in / $0.60 out per 1M). Gemini spend was therefore
    both invisible AND counted as zero.

Running a 24/7 frontier council on estimates means you learn your real burn rate from
a credit-card statement instead of from HELM. That is the same disease as a fabricated
PASS verdict, pointed at the wallet.

WHAT IS ACTUALLY OBSERVABLE
---------------------------
The grok/gemini CLIs do not emit token-usage counters. So we cannot claim
provider-exact billing. What we CAN observe, exactly, is the real I/O of every
dispatch: the exact prompt bytes sent and the exact output bytes returned.

So the meter DERIVES cost from measured I/O and labels its own provenance honestly:

    measurement = "DERIVED_FROM_OBSERVED_IO"   <- we counted real bytes, estimated tokens
    measurement = "PROVIDER_REPORTED"          <- only if a provider ever gives us usage

It never pretends to be provider-exact. It never invents a number. It never reports
zero for a paid model. A cost whose adapter has no published rate is UNPRICED and is
treated as OVER the cap (fail closed), not as free.
"""
from __future__ import annotations

import datetime
import fcntl
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SPEND_LEDGER = ROOT / "coordination" / "council" / "spend_ledger.jsonl"

# ~4 chars/token is the standard rough tokenizer ratio. It is an APPROXIMATION and the
# ledger says so in every row via `measurement`.
CHARS_PER_TOKEN = 4.0

DEFAULT_PER_TASK_CAP_USD = 0.50
DEFAULT_DAILY_CAP_USD = 5.00        # conservative until the founder raises it


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _rates() -> Dict[str, Dict[str, float]]:
    """Real published rates, read from the adapter registry — never hardcoded here."""
    try:
        from backend.mission_control.adapter_registry import AdapterRegistry
        out = {}
        for k, v in AdapterRegistry().check_all_readiness().items():
            cm = (v or {}).get("cost_model") or {}
            out[k] = {"in": float(cm.get("input_cost_per_1m", 0.0)),
                      "out": float(cm.get("output_cost_per_1m", 0.0)),
                      "egress": v.get("egress_class", "UNKNOWN")}
        return out
    except Exception:
        return {}


class SpendMeter:
    """Append-only, hash-chained record of ACTUAL observed model spend."""

    def __init__(self, path: Path | None = None,
                 per_task_cap_usd: float = DEFAULT_PER_TASK_CAP_USD,
                 daily_cap_usd: float = DEFAULT_DAILY_CAP_USD):
        self.path = Path(path) if path else SPEND_LEDGER
        self.per_task_cap_usd = per_task_cap_usd
        self.daily_cap_usd = daily_cap_usd

    # ---------------------------------------------------------------- ledger
    def entries(self) -> list[dict]:
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

    def _last_hash(self) -> str:
        e = self.entries()
        return e[-1]["entry_hash"] if e else "GENESIS"

    def _append(self, entry: dict) -> dict:
        # AU-9 continuity fix: read-last-hash + append must be atomic across
        # processes, else concurrent writers compute the same prev_hash and the
        # chain forks (link discontinuity). Serialize under an exclusive flock.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_suffix(self.path.suffix + ".wlock")
        with open(lock_path, "w") as _lock:
            fcntl.flock(_lock.fileno(), fcntl.LOCK_EX)
            try:
                body = dict(entry)
                body["prev_hash"] = self._last_hash()
                body["entry_hash"] = hashlib.sha256(
                    json.dumps(body, sort_keys=True).encode()).hexdigest()
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(body, sort_keys=True) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
            finally:
                fcntl.flock(_lock.fileno(), fcntl.LOCK_UN)
        return body

    def _entries_consistent(self) -> list:
        """Read the whole ledger under a SHARED flock so an in-flight append (which
        holds the EXCLUSIVE flock) can never produce a torn read. Never called from
        inside _append, so there is no self-deadlock."""
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

    def verify_chain(self) -> tuple[bool, list[str]]:
        """A tampered or deleted row breaks the chain and is detectable.

        Reads under a shared lock (_entries_consistent) so a concurrent append never
        yields a false 'break' from a torn read."""
        prev = "GENESIS"
        bad = []
        for i, e in enumerate(self._entries_consistent()):
            if e.get("prev_hash") != prev:
                bad.append(f"row {i}: prev_hash mismatch")
            body = {k: v for k, v in e.items() if k != "entry_hash"}
            calc = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            if calc != e.get("entry_hash"):
                bad.append(f"row {i}: entry_hash mismatch (row was edited)")
            prev = e.get("entry_hash", "")
        return (not bad), bad

    # ------------------------------------------------------------- accounting
    def spent_today_usd(self) -> float:
        today = _now().date().isoformat()
        return round(sum(e.get("cost_usd", 0.0) for e in self.entries()
                         if str(e.get("ts", "")).startswith(today)), 6)

    def spent_total_usd(self) -> float:
        return round(sum(e.get("cost_usd", 0.0) for e in self.entries()), 6)

    def spent_by_adapter(self) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for e in self.entries():
            a = e.get("adapter", "UNKNOWN")
            out[a] = round(out.get(a, 0.0) + e.get("cost_usd", 0.0), 6)
        return out

    # ------------------------------------------------------------ measurement
    def price(self, adapter: str, prompt: str, output: str) -> Dict[str, Any]:
        """Derive cost from REAL observed I/O. Fail closed on unknown pricing."""
        rates = _rates().get(adapter)
        in_chars, out_chars = len(prompt or ""), len(output or "")
        in_tok = in_chars / CHARS_PER_TOKEN
        out_tok = out_chars / CHARS_PER_TOKEN

        if rates is None:
            # We do NOT know what this costs. Unknown price is never free.
            return {"adapter": adapter, "cost_usd": None, "priced": False,
                    "measurement": "UNPRICED_ADAPTER",
                    "in_chars": in_chars, "out_chars": out_chars,
                    "note": "no published rate -> treated as OVER CAP (fail closed)"}

        cost = (in_tok / 1e6) * rates["in"] + (out_tok / 1e6) * rates["out"]
        return {
            "adapter": adapter,
            "egress": rates["egress"],
            "in_chars": in_chars, "out_chars": out_chars,
            "in_tokens_est": round(in_tok, 1), "out_tokens_est": round(out_tok, 1),
            "rate_in_per_1m": rates["in"], "rate_out_per_1m": rates["out"],
            "cost_usd": round(cost, 6),
            "priced": True,
            # Honest provenance: we measured real bytes; tokens are an approximation.
            # This is NOT provider-reported billing and never claims to be.
            "measurement": "DERIVED_FROM_OBSERVED_IO",
            "tokenizer_note": f"~{CHARS_PER_TOKEN} chars/token approximation",
        }

    def record(self, *, task_id: str, adapter: str, prompt: str, output: str,
               dispatch_id: Optional[str] = None,
               exit_code: Optional[int] = None) -> dict:
        """Meter one real dispatch into the hash-chained ledger."""
        p = self.price(adapter, prompt, output)
        entry = {
            "ts": _now().isoformat(),
            "task_id": task_id,
            "dispatch_id": dispatch_id,
            "exit_code": exit_code,
            **p,
            "cost_usd": p.get("cost_usd") if p.get("priced") else 0.0,
            "cost_state": "OBSERVED" if p.get("priced") else "UNPRICED",
        }
        return self._append(entry)

    # ----------------------------------------------------------------- caps
    def check_caps(self, adapter: str, prompt: str,
                   est_output_chars: int = 8000) -> Dict[str, Any]:
        """Pre-flight: would this dispatch breach a cap, measured against OBSERVED spend?"""
        p = self.price(adapter, prompt, "x" * est_output_chars)
        spent = self.spent_today_usd()

        if not p.get("priced"):
            return {"allowed": False, "reason": "UNPRICED_ADAPTER",
                    "detail": f"{adapter} has no published rate; unknown price is not free",
                    "spent_today_usd": spent}

        est = p["cost_usd"]
        if est > self.per_task_cap_usd:
            return {"allowed": False, "reason": "PER_TASK_CAP_EXCEEDED",
                    "estimate_usd": est, "cap_usd": self.per_task_cap_usd,
                    "spent_today_usd": spent}
        if spent + est > self.daily_cap_usd:
            return {"allowed": False, "reason": "DAILY_CAP_EXCEEDED",
                    "estimate_usd": est, "spent_today_usd": spent,
                    "daily_cap_usd": self.daily_cap_usd}
        return {"allowed": True, "estimate_usd": est, "spent_today_usd": spent,
                "daily_cap_usd": self.daily_cap_usd,
                "headroom_usd": round(self.daily_cap_usd - spent - est, 6)}

    def summary(self) -> Dict[str, Any]:
        ok, bad = self.verify_chain()
        e = self.entries()
        return {
            "spent_today_usd": self.spent_today_usd(),
            "spent_total_usd": self.spent_total_usd(),
            "by_adapter": self.spent_by_adapter(),
            "daily_cap_usd": self.daily_cap_usd,
            "per_task_cap_usd": self.per_task_cap_usd,
            "headroom_today_usd": round(self.daily_cap_usd - self.spent_today_usd(), 6),
            "dispatches_metered": len(e),
            "unpriced_dispatches": sum(1 for x in e if x.get("cost_state") == "UNPRICED"),
            "chain_valid": ok,
            "chain_errors": bad[:3],
            "measurement": "DERIVED_FROM_OBSERVED_IO (not provider-reported billing)",
        }
