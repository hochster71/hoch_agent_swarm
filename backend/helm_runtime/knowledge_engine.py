"""EDR-0004 Knowledge Engine — Governed Retrieval (v1).

Implements EDR-0004 (`docs/helm/edr/EDR-0004-knowledge-engine.md`) v1 scope:
**Governed Retrieval, not long-term memory**. It gives every worker — Claude,
ChatGPT, Grok, Ollama, LM Studio — a shared, authoritative answer to
governance-provenance questions so nothing depends on hidden chat history:

  * Which Constitution article governs this?
  * Which EDR changed this behavior?
  * What verification evidence supports this implementation?
  * Which runtime docs / cyber mappings apply?

Design (inherits Constitution Article II via EDR-0004):

  * **Derived/provenanced, never invented** — every item traces to a real file
    on disk plus a git commit; nothing is fabricated. Missing/absent → reported
    as ``UNKNOWN``, stale → reported as ``STALE`` (:data:`Freshness`), never faked.
  * **Retrieval is read-only** — :func:`retrieve` and friends never write truth,
    never emit events, never mutate the corpus. They index existing governed
    files; they do not replace them.
  * **Policy-bound** — every candidate path is routed through
    :class:`RetrievalPolicy`, which fails closed: only paths inside the declared
    corpus roots are eligible and any secret/credential-shaped path is denied so
    a query can never surface a key.
  * **Cross-model neutrality** — one corpus, one contract; no model's private
    context is authoritative. Any valid actor role may read.
  * **Governed ingestion** — the *only* state-changing entrypoint,
    :func:`ingest`, is wired through the frozen ``governance_engine`` (role +
    founder-gate checks) and emits an Event Bus ``KNOWLEDGE_INGESTED`` event, so
    the timeline records what knowledge changed and when.

This module changes **no architecture**: it imports only frozen read-surfaces
(`governance_engine`, `event_bus`) and reads governed files. It is a runtime
projection for readers and a governed, evidence-linked door for writers — it is
NOT part of the frozen verification target.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.helm_runtime import governance_engine as gov
from backend.helm_runtime.event_bus import publish_event

ROOT = Path(__file__).resolve().parents[2]

# --------------------------------------------------------------------------- #
# Corpus definition — the governed files the engine indexes (never replaces).
# EDR-0004: "the existing governed files are the source of record; the Knowledge
# Engine indexes them." Roots are bounded so a scan stays fast and predictable.
# --------------------------------------------------------------------------- #
CORPUS_ROOTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    # (relative root, allowed suffixes)
    ("docs/helm", (".md",)),
    ("docs/evidence", (".md",)),
    ("coordination/goal", (".json",)),
)

# A document is STALE once it is older than this. Governance docs age slowly, so
# the default is generous; callers may override per query.
DEFAULT_STALE_AFTER_SECONDS: int = 180 * 24 * 3600  # 180 days

# --------------------------------------------------------------------------- #
# Retrieval policy — fail-closed. Anything secret-shaped is denied so a query
# can never surface a credential; anything outside the corpus roots is denied.
# --------------------------------------------------------------------------- #
_SECRET_MARKERS: Tuple[str, ...] = (
    "secret",
    "secrets",
    "credential",
    "password",
    "passwd",
    ".env",
    "id_rsa",
    "id_ed25519",
    ".ssh",
    "keychain",
    "private_key",
    "privatekey",
    "token",
    "api_key",
    "apikey",
    ".pem",
    ".key",
)


class RetrievalPolicy:
    """Policy-bound gate every candidate path must pass. Fails closed."""

    def __init__(
        self,
        roots: Tuple[Tuple[str, Tuple[str, ...]], ...] = CORPUS_ROOTS,
        root: Path = ROOT,
    ) -> None:
        self.root = root
        self._roots = [(root / r, sfx) for (r, sfx) in roots]

    def _within_roots(self, abspath: Path) -> Optional[Tuple[str, ...]]:
        try:
            resolved = abspath.resolve()
        except OSError:
            return None
        for base, sfx in self._roots:
            try:
                resolved.relative_to(base.resolve())
                return sfx
            except ValueError:
                continue
        return None

    def allows(self, abspath: Path) -> Tuple[bool, str]:
        """Return (allowed, reason). Denies secrets and out-of-corpus paths."""
        low = str(abspath).lower()
        for marker in _SECRET_MARKERS:
            if marker in low:
                return False, f"DENIED_SECRET_SHAPED:{marker}"
        sfx = self._within_roots(abspath)
        if sfx is None:
            return False, "DENIED_OUTSIDE_CORPUS"
        if not any(low.endswith(s) for s in sfx):
            return False, "DENIED_SUFFIX"
        return True, "ALLOWED"


# --------------------------------------------------------------------------- #
# Kind classification — provenance-question buckets from EDR-0004's corpus.
# --------------------------------------------------------------------------- #
def classify_kind(rel_path: str) -> str:
    p = rel_path.replace("\\", "/")
    name = p.rsplit("/", 1)[-1]
    up = p.upper()
    upname = name.upper()
    if "CONSTITUTION" in upname:
        return "constitution"
    if "/edr/" in p.lower() or upname.startswith("EDR-"):
        return "edr"
    if any(k in up for k in ("NIST", "RMF", "ZERO_TRUST", "ZERO-TRUST", "REV5", "REV.5", "CYBER")):
        return "cyber_mapping"
    if "RUNBOOK" in up or "/runbooks/" in p.lower():
        return "runbook"
    if "/evidence/" in p.lower() or "VERIFICATION" in up or "CONFORMANCE" in up:
        return "evidence"
    if "LESSON" in up:
        return "lessons"
    if p.startswith("coordination/goal"):
        return "mission_history"
    if "ARCHITECTURE" in up or "CHARTER" in up or "RUNTIME" in up:
        return "runtime_doc"
    return "doc"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _git_commit_for(rel_path: str, root: Path = ROOT) -> Optional[str]:
    """Short commit that last touched the file. None if untracked / not a repo."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%h", "--", rel_path],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = out.stdout.strip()
    return commit or None


@dataclass
class Freshness:
    status: str  # FRESH | STALE | UNKNOWN
    mtime: Optional[str]
    age_seconds: Optional[float]
    stale_after_seconds: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "mtime": self.mtime,
            "age_seconds": self.age_seconds,
            "stale_after_seconds": self.stale_after_seconds,
        }


@dataclass
class KnowledgeItem:
    path: str  # repo-relative source of record
    kind: str
    title: str
    provenance: Dict[str, Any]  # {source_path, commit, exists}
    freshness: Dict[str, Any]
    score: float = 0.0
    snippet: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "title": self.title,
            "provenance": self.provenance,
            "freshness": self.freshness,
            "score": round(self.score, 4),
            "snippet": self.snippet,
        }


def _freshness_for(abspath: Path, stale_after_seconds: int) -> Freshness:
    if not abspath.exists():
        return Freshness("UNKNOWN", None, None, stale_after_seconds)
    mtime = datetime.fromtimestamp(abspath.stat().st_mtime, tz=timezone.utc)
    age = (_now() - mtime).total_seconds()
    status = "STALE" if age > stale_after_seconds else "FRESH"
    return Freshness(status, mtime.strftime("%Y-%m-%dT%H:%M:%SZ"), age, stale_after_seconds)


def _title_of(text: str, fallback: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip() or fallback
        if s:
            return s[:120]
    return fallback


def _iter_corpus_paths(policy: RetrievalPolicy) -> List[Path]:
    paths: List[Path] = []
    for base, sfx in policy._roots:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            ok, _reason = policy.allows(p)
            if ok:
                paths.append(p)
    return paths


def _index_item(
    abspath: Path,
    *,
    root: Path,
    stale_after_seconds: int,
    text: Optional[str] = None,
) -> KnowledgeItem:
    rel = str(abspath.resolve().relative_to(root.resolve()))
    if text is None:
        try:
            text = abspath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
    kind = classify_kind(rel)
    fresh = _freshness_for(abspath, stale_after_seconds)
    provenance = {
        "source_path": rel,
        "commit": _git_commit_for(rel, root),
        "exists": abspath.exists(),
        "derived": True,
    }
    return KnowledgeItem(
        path=rel,
        kind=kind,
        title=_title_of(text, rel),
        provenance=provenance,
        freshness=fresh.to_dict(),
        snippet="",
    )


# --------------------------------------------------------------------------- #
# Manifest — a derived list of every governed document with provenance+freshness.
# Read-only; building it never mutates anything.
# --------------------------------------------------------------------------- #
def build_manifest(
    *,
    root: Path = ROOT,
    policy: Optional[RetrievalPolicy] = None,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
    resolve_commits: bool = False,
) -> Dict[str, Any]:
    """Index the governed corpus. ``resolve_commits=False`` skips per-file git
    (fast path for listing); retrieval resolves commits only for returned hits."""
    policy = policy or RetrievalPolicy(root=root)
    items: List[Dict[str, Any]] = []
    by_kind: Dict[str, int] = {}
    for abspath in _iter_corpus_paths(policy):
        rel = str(abspath.resolve().relative_to(root.resolve()))
        kind = classify_kind(rel)
        by_kind[kind] = by_kind.get(kind, 0) + 1
        fresh = _freshness_for(abspath, stale_after_seconds)
        prov = {
            "source_path": rel,
            "commit": _git_commit_for(rel, root) if resolve_commits else None,
            "exists": True,
            "derived": True,
        }
        items.append(
            {
                "path": rel,
                "kind": kind,
                "provenance": prov,
                "freshness": fresh.to_dict(),
            }
        )
    items.sort(key=lambda d: d["path"])
    return {
        "kind": "knowledge_manifest",
        "corpus_root": str(root),
        "document_count": len(items),
        "by_kind": by_kind,
        "documents": items,
        "doctrine": "derived from governed files; read-only; missing=UNKNOWN, stale=STALE",
    }


# --------------------------------------------------------------------------- #
# Retrieval — read-only, policy-bound, honest. Keyword/manifest ranking (v1);
# semantic/embedding retrieval is a later, founder-gated increment (EDR-0004).
# --------------------------------------------------------------------------- #
def _score(text_lower: str, title_lower: str, path_lower: str, terms: List[str]) -> Tuple[float, int]:
    score = 0.0
    matched = 0
    for t in terms:
        in_path = t in path_lower
        in_title = t in title_lower
        body = text_lower.count(t)
        if in_path or in_title or body:
            matched += 1
        # filename/title matches weigh far more than incidental body mentions
        score += (4.0 if in_path else 0.0) + (2.0 if in_title else 0.0) + min(body, 10) * 0.2
    return score, matched


def _snippet_for(text: str, terms: List[str], width: int = 200) -> str:
    low = text.lower()
    for t in terms:
        i = low.find(t)
        if i >= 0:
            start = max(0, i - width // 2)
            end = min(len(text), i + width // 2)
            frag = text[start:end].replace("\n", " ").strip()
            return ("…" if start > 0 else "") + frag + ("…" if end < len(text) else "")
    return text.strip().replace("\n", " ")[:width]


def retrieve(
    q: str,
    *,
    kind: Optional[str] = None,
    limit: int = 8,
    role: Optional[str] = None,
    root: Path = ROOT,
    policy: Optional[RetrievalPolicy] = None,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> Dict[str, Any]:
    """Read-only governed retrieval. Never writes, never emits, never fabricates.

    Returns ranked documents with provenance + freshness. If nothing matches,
    returns an honest ``UNKNOWN`` result rather than an invented answer.
    """
    # Cross-model neutrality: any valid actor may read; only fabricated/non-actor
    # roles (Truth/Runtime) are rejected — reads are otherwise open to all.
    if role is not None:
        r = gov.normalize_role(role)
        if r.startswith("INVALID_"):
            return {
                "kind": "knowledge_retrieval",
                "query": q,
                "status": "ROLE_REJECTED",
                "reason": f"{role!r} is not an actor role (Truth/Runtime are not roles)",
                "results": [],
            }

    policy = policy or RetrievalPolicy(root=root)
    terms = [t for t in "".join(c.lower() if c.isalnum() or c.isspace() else " " for c in q).split() if t]

    hits: List[KnowledgeItem] = []
    if terms:
        for abspath in _iter_corpus_paths(policy):
            rel = str(abspath.resolve().relative_to(root.resolve()))
            k = classify_kind(rel)
            if kind and k != kind:
                continue
            try:
                text = abspath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            title = _title_of(text, rel)
            score, matched = _score(text.lower(), title.lower(), rel.lower(), terms)
            if matched == 0:
                continue
            item = _index_item(
                abspath, root=root, stale_after_seconds=stale_after_seconds, text=text
            )
            item.score = score
            item.snippet = _snippet_for(text, terms)
            hits.append(item)

    hits.sort(key=lambda it: it.score, reverse=True)
    top = hits[:limit]
    status = "OK" if top else "UNKNOWN"
    return {
        "kind": "knowledge_retrieval",
        "query": q,
        "kind_filter": kind,
        "status": status,
        "result_count": len(top),
        "results": [it.to_dict() for it in top],
        "doctrine": (
            "read-only; provenanced (source_path+commit) + freshness; "
            "UNKNOWN when no governed document matches — never fabricated"
        ),
    }


def governed_load_constitution_and_edrs(
    *,
    root: Path = ROOT,
    policy: Optional[RetrievalPolicy] = None,
    stale_after_seconds: int = DEFAULT_STALE_AFTER_SECONDS,
) -> Dict[str, Any]:
    """AC: a worker retrieves the Constitution + applicable EDRs in ONE call.

    Read-only. Reports honestly if the ratified Constitution is absent (UNKNOWN).
    """
    policy = policy or RetrievalPolicy(root=root)
    constitution: List[KnowledgeItem] = []
    edrs: List[KnowledgeItem] = []
    for abspath in _iter_corpus_paths(policy):
        rel = str(abspath.resolve().relative_to(root.resolve()))
        k = classify_kind(rel)
        if k == "constitution":
            constitution.append(
                _index_item(abspath, root=root, stale_after_seconds=stale_after_seconds)
            )
        elif k == "edr":
            edrs.append(
                _index_item(abspath, root=root, stale_after_seconds=stale_after_seconds)
            )
    constitution.sort(key=lambda it: it.path)
    edrs.sort(key=lambda it: it.path)
    return {
        "kind": "knowledge_session_load",
        "status": "OK" if constitution else "UNKNOWN",
        "constitution": [it.to_dict() for it in constitution],
        "edrs": [it.to_dict() for it in edrs],
        "note": (
            "Standard Session Flow 'Load Constitution / Load EDRs' resolves here so "
            "every provider reads identically (EDR-0004 cross-model access)."
        ),
    }


# --------------------------------------------------------------------------- #
# Ingestion — the ONLY state-changing entrypoint. Governed: role/founder checks
# via the frozen governance_engine, then an Event Bus event. Never writes truth.
# --------------------------------------------------------------------------- #

# Which actor roles may register which knowledge kinds. Constitution changes are
# founder-gated (charter ratification); everything else follows delegated roles.
_INGEST_POLICY: Dict[str, Tuple[str, ...]] = {
    "founder": ("constitution", "edr", "runtime_doc", "cyber_mapping", "runbook",
                "evidence", "mission_history", "lessons", "doc"),
    "builder": ("edr", "runtime_doc", "evidence", "runbook", "doc"),
    "auditor": ("evidence", "cyber_mapping", "runbook", "doc"),
    "orchestrator": ("runbook", "mission_history", "lessons", "doc"),
}


def ingest(
    role: str,
    source_path: str,
    *,
    mission_id: str = "EPIC-FURY-2026",
    correlation_id: Optional[str] = None,
    note: str = "",
    root: Path = ROOT,
    policy: Optional[RetrievalPolicy] = None,
    founder_token_present: bool = False,
    emit: bool = True,
) -> Dict[str, Any]:
    """Register a governed document into the corpus timeline.

    Governance-bound:
      * ``role`` must be a valid actor (Truth/Runtime rejected).
      * ``constitution`` ingestion is a founder gate — requires founder + token.
      * the role must be permitted the document's kind (:data:`_INGEST_POLICY`).
    On success emits a ``KNOWLEDGE_INGESTED`` Event Bus event with the document's
    provenance as evidence. It does NOT copy or move the file — the governed file
    on disk stays the source of record (retrieval is read-only).
    """
    r = gov.normalize_role(role)
    if r.startswith("INVALID_") or r not in _INGEST_POLICY:
        return {"ok": False, "status": "ROLE_REJECTED",
                "reason": f"{role!r} may not ingest knowledge"}

    policy = policy or RetrievalPolicy(root=root)
    abspath = (root / source_path).resolve()
    allowed, reason = policy.allows(abspath)
    if not allowed:
        return {"ok": False, "status": "POLICY_DENIED", "reason": reason,
                "source_path": source_path}
    if not abspath.exists():
        # No fake green: cannot ingest a document that is not on disk.
        return {"ok": False, "status": "SOURCE_ABSENT", "source_path": source_path}

    rel = str(abspath.relative_to(root.resolve()))
    kind = classify_kind(rel)

    # Founder-gate the Constitution (charter ratification is founder-only).
    if kind == "constitution":
        if r != "founder":
            return {"ok": False, "status": "FOUNDER_GATE",
                    "reason": "constitution ingestion is founder-gated"}
        if not founder_token_present:
            return {"ok": False, "status": "FOUNDER_GATE",
                    "reason": "constitution ingestion requires founder authorization token"}

    if kind not in _INGEST_POLICY[r]:
        return {"ok": False, "status": "ROLE_NOT_PERMITTED_KIND",
                "reason": f"role {r!r} may not ingest kind {kind!r}"}

    commit = _git_commit_for(rel, root)
    fresh = _freshness_for(abspath, DEFAULT_STALE_AFTER_SECONDS)
    provenance = {"source_path": rel, "commit": commit, "kind": kind, "derived": True}

    event = None
    if emit:
        # HELM-GOV | extends: N5 emitter (knowledge ingestion) | edr: EDR-0006-R5 | why: a governed
        #          | ingestion is a material operation — carry a Proof Record (OBSERVED: it happened).
        try:
            from backend.helm_runtime.governed_emit import build_proof_record as _bpr
            from backend.helm_runtime.extensions.constitutional_gate import govern_decision as _gd
            _pr = _bpr(authority="knowledge_engine.governed_ingest", decision_id=correlation_id or rel,
                       explanation=f"ingest {kind}: {rel}", inputs={"source_path": rel, "commit": commit},
                       proof_command="knowledge_engine.ingest (governed retrieval, EDR-0004)",
                       evidence_class="OBSERVED", environment="knowledge_engine",
                       correlation_id=correlation_id or rel)
            _pr["governance_state"] = _gd(_pr).governance_state
        except Exception:
            _pr = None
        from backend.helm_runtime.extensions.constitutional_gate import publish_governed_event as _pge
        event = _pge(
            type="KNOWLEDGE_INGESTED",
            producer=r,
            mission_id=mission_id,
            correlation_id=correlation_id,
            proof_record=_pr,
            evidence=[rel] + ([f"commit:{commit}"] if commit else []),
            payload={
                "kind": kind,
                "source_path": rel,
                "provenance": provenance,
                "freshness": fresh.to_dict(),
                "note": note,
            },
        )

    return {
        "ok": True,
        "status": "INGESTED",
        "role": r,
        "kind": kind,
        "provenance": provenance,
        "freshness": fresh.to_dict(),
        "event_id": getattr(event, "event_id", None),
        "doctrine": "governed ingestion emits an event; the file stays the source of record",
    }
