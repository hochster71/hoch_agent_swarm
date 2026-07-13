"""founder_model.py — FOUNDER DOCTRINE ENGINE (not a "founder model").

TERMINOLOGY (corrected): this does NOT reproduce Michael's judgment as a person. It
retrieves his RATIFIED decisions, classifies authority, applies explicit policy, detects
conflict/uncertainty, prepares decisions, and REFUSES unsupported inference. Its job is
governance, not impersonation.

THE GOAL (North Star, verbatim)
-------------------------------
"Convert Michael Hoch's judgment into shipped, monetized products, while minimizing
founder time." Everything else in HELM is the FACTORY. This module is the FOUNDER MODEL:
it inherits what Michael decided, acts within his authority, and hands him ONLY the
decisions that are genuinely his.

It does three things, and refuses to do a fourth:

  1. ROUTE every proposed action against the authority matrix
       -> AUTONOMOUS    : do it, log it
       -> PROPOSE_ONLY  : prepare + prove + HOLD for the founder button
       -> FOUNDER_ONLY  : BLOCKED_FOUNDER_ACTION, never performed
  2. ANSWER from the decision corpus before asking (inherit, don't re-ask)
  3. ESCALATE only in the founder-contract shape, and ONLY when it cannot prove the answer

The fourth thing it refuses: escalating something it could have verified. Escalation is
for judgment, not for laziness. That refusal is what actually reduces founder minutes.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "coordination" / "founder" / "authority_matrix.json"
CORPUS = ROOT / "coordination" / "founder" / "decision_corpus.jsonl"
QUEUE = ROOT / "coordination" / "founder" / "escalation_queue.jsonl"


class Authority(str, Enum):
    AUTONOMOUS = "AUTONOMOUS"
    PREAUTHORIZED_PLAYBOOK = "PREAUTHORIZED_PLAYBOOK"  # urgent+predictable, pre-approved
    PROPOSE_ONLY = "PROPOSE_ONLY"
    FOUNDER_ONLY = "FOUNDER_ONLY"
    PROHIBITED = "PROHIBITED"        # never allowed, even by a founder tap
    CONFLICTED = "CONFLICTED"        # ratified decisions disagree -> withhold
    UNKNOWN = "UNKNOWN"


# Keyword signatures per class. FOUNDER_ONLY is checked FIRST and wins — fail closed:
# anything touching money, credentials, or legal attestation is founder-only even if it
# also looks routine.
# PROHIBITED: HELM must never do these, and the founder gate must never offer them as an
# APPROVE tap either. Distinct from FOUNDER_ONLY (which Michael may do himself, elsewhere).
_PROHIBITED = (
    "read secret", "read the secret", "secret into", "key into model", "into model context",
    "expose private key", "expose the key", "print the secret", "log the secret",
    "exfiltrate", "disable the gate", "bypass the authority", "bypass classification",
)
# PREAUTHORIZED_PLAYBOOK: urgent+predictable ops HELM may self-execute without asking, per
# an approved playbook (bounded, reversible, notified).
# signatures are stored PRE-NORMALIZED (no articles) to match _normalize() output
_PLAYBOOK = (
    "restart failed daemon", "quarantine adapter", "revoke expired local lease",
    "rollback failed deployment", "rollback failed deploy", "disable compromised integration",
)
_FOUNDER_ONLY = (
    "rotate", "roll key", "delete key", "roll the key", "revoke", "password", "ssn", "bank",
    "credential", "api key", "secret key", "accept terms", "terms of service",
    "attestation", "submit to apple", "app store connect", "refund", "transfer",
    "trade", "purchase", "move money", "wire ", "charge the", "sign the",
)
_PROPOSE_ONLY = (
    "deploy", "merge to main", "publish", "change price", "change the price",
    "new product", "enable factory", "promote", "send email", "paid frontier",
    "grok", "gemini", "openai dispatch", "scheduled task", "go live", "production",
)


@dataclass
class Ruling:
    authority: Authority
    reason: str
    matched: str = ""


_EVASION = ("just ", "quietly ", "simply ", "as cleanup", "for cleanup", "routine ",
            "minor ", "quick ", "no big deal", "temporarily ", "as a workaround")


def _normalize(text: str) -> str:
    """POLICY-BYPASS-CONTROL: remove evasion wrappers so a disguised action still routes
    on its true verb. 'quietly delete the key as cleanup' -> classifies on 'delete key'."""
    t = text.lower()
    for e in _EVASION:
        t = t.replace(e, " ")
    # strip articles so 'delete the key' matches the 'delete key' signature
    toks = [w for w in t.split() if w not in ("the", "a", "an")]
    return " ".join(toks)


def classify_action(text: str) -> Ruling:
    """Route a proposed action. Order = fail closed: PROHIBITED > FOUNDER_ONLY >
    PROPOSE_ONLY > PLAYBOOK > AUTONOMOUS. Classification runs on the NORMALIZED text so an
    action cannot be renamed or wrapped in 'cleanup' to dodge the gate."""
    t = _normalize(text)
    for kw in _PROHIBITED:
        if kw in t:
            return Ruling(Authority.PROHIBITED, "never permitted, even by founder tap", kw)
    for kw in _FOUNDER_ONLY:
        if kw in t:
            return Ruling(Authority.FOUNDER_ONLY, "matches a founder-only signature", kw)
    for kw in _PLAYBOOK:
        if kw in t:
            return Ruling(Authority.PREAUTHORIZED_PLAYBOOK, "urgent+predictable, pre-approved", kw)
    for kw in _PROPOSE_ONLY:
        if kw in t:
            return Ruling(Authority.PROPOSE_ONLY, "spends, publishes, or binds", kw)
    return Ruling(Authority.AUTONOMOUS, "reversible and bounded", "")


def load_corpus() -> list[dict[str, Any]]:
    if not CORPUS.exists():
        return []
    out = []
    for line in CORPUS.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def answer_from_corpus(question: str) -> dict[str, Any] | None:
    """Inherit Michael's ratified judgment. If a prior decision covers this, DON'T ask.

    AUTHORITY-CONFLICT + SUPERSESSION: only RATIFIED decisions authorize. If two RATIFIED
    decisions on the same topic disagree and neither supersedes the other, return a
    CONFLICTED marker rather than silently picking whichever was found first."""
    q = question.lower()
    scored = []
    for d in load_corpus():
        if str(d.get("status", "RATIFIED")).upper() != "RATIFIED":
            continue  # only RATIFIED may authorize
        hay = f"{d.get('topic','')} {d.get('decision','')} {d.get('id','')}".lower()
        score = sum(1 for w in set(q.split()) if len(w) > 3 and w in hay)
        if score >= 2:
            scored.append((score, d))
    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    top = [d for s_, d in scored if s_ == scored[0][0]]
    if len(top) > 1:
        topics = {d.get("topic") for d in top}
        superseded = {sid for d in top for sid in d.get("supersedes", [])}
        live = [d for d in top if d.get("id") not in superseded]
        if len(topics) > 1 and len(live) > 1:
            return {"id": "CONFLICTED", "status": "CONFLICTED",
                    "decision": "Ratified decisions disagree; withhold and escalate.",
                    "candidates": [d.get("id") for d in live]}
        return live[0] if live else top[0]
    return top[0]


# The only shape allowed to reach the founder.
ESCALATION_FIELDS = (
    "decision_id", "one_sentence_question", "why_it_needs_you", "options",
    "recommendation_and_why", "evidence_sanitized", "cost_of_delay", "reversible",
)


@dataclass
class Escalation:
    one_sentence_question: str
    why_it_needs_you: str
    options: list[str]
    recommendation_and_why: str
    evidence_sanitized: str
    cost_of_delay: str
    reversible: bool
    decision_id: str = field(default_factory=lambda: f"DEC-{int(time.time())}")

    def valid(self) -> tuple[bool, list[str]]:
        d = self.__dict__
        missing = [f for f in ESCALATION_FIELDS if not d.get(f) and d.get(f) is not False]
        if len(self.options) < 2:
            missing.append("options(>=2)")
        return (not missing, missing)


def escalate(esc: Escalation, *, can_prove_answer: bool) -> tuple[bool, str]:
    """Enforce the hard rule: if the model can PROVE the answer, it must NOT escalate."""
    if can_prove_answer:
        return False, "SUPPRESSED: the model can prove this answer; escalation is for judgment, not verification"
    ok, missing = esc.valid()
    if not ok:
        return False, f"REJECTED: escalation not in founder-contract shape; missing {missing}"
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUEUE, "a", encoding="utf-8") as f:
        f.write(json.dumps({**esc.__dict__, "queued_at": time.time()}) + "\n")
    return True, f"ESCALATED: {esc.decision_id}"
