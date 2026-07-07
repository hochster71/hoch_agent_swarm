# write_brain_live Dependency Review

## HEAD
b173dbb3e947e62ecb4689ff822465a64e473c49
b173dbb Harden runtime start stop SQLite writes
0a7d3d5 Harden provider key provisioning script
e1216e2 feat(r1): guided provider API-key provisioning script (opens key page, hidden paste, .env store)
0c50cdc Harden HOCH-200 mission commander truth dashboard
432eb73 fix(pert): wire tests/evidence/accountability/blocked to real sources (UNKNOWN if missing); guard: no hardcoded metric literals
305cc5a fix(pert): derived goal-percent wins over stale cadence-cache override (no more 80)

## Scoped status
 M scripts/write_brain_live.py
?? backend/factory/champion_loader.py
?? backend/factory/outcome_stats.py
?? backend/factory/runtime_ledger.py

## Scoped diff stat
 scripts/write_brain_live.py | 63 +++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 61 insertions(+), 2 deletions(-)

## Untracked dependency previews

### backend/factory/outcome_stats.py
"""Outcome stats — aggregate the runtime + outcome ledgers into per-gene combat records.

Live-real-only doctrine: a champion's registry score says how well its TEXT fits a rubric;
its combat record says what actually happened when it was USED. This module computes the
latter from the two append-only ledgers and writes data/prompt_brain/outcome_stats.json
for the live feed. Read-only over the ledgers; deterministic; stdlib only.

Per gene: executions (champion actually applied), completions, failures, last_used,
surfaces. Per gate stream (live_judge / m0_generation): counts. Nothing here is invented —
every number is a count of ledger lines.
"""
import json
import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent.parent
USAGE = ROOT / "data" / "prompt_brain" / "runtime_usage_ledger.jsonl"
OUTCOME = ROOT / "data" / "prompt_brain" / "outcome_feedback_ledger.jsonl"
OUT = ROOT / "data" / "prompt_brain" / "outcome_stats.json"


def _lines(p: Path):
    if not p.exists():
        return
    with p.open(encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln:
                try:
                    yield json.loads(ln)
                except Exception:
                    continue


def compute() -> Dict[str, Any]:
    usage_by_id: Dict[str, Dict] = {}
    genes: Dict[str, Dict[str, Any]] = {}

    for u in _lines(USAGE):
        uid = u.get("usage_id")
        if uid:
            usage_by_id[uid] = u
        if u.get("fallback_used"):
            continue  # only true champion applications count as executions
        gid = u.get("champion_id")
        if not gid:
            continue
        g = genes.setdefault(gid, {"task_class": u.get("task_class"),
                                   "executions": 0, "completed": 0, "failed": 0,
                                   "surfaces": {}, "last_used": None})
        g["executions"] += 1
        g["surfaces"][u.get("execution_surface", "?")] = \
            g["surfaces"].get(u.get("execution_surface", "?"), 0) + 1
        g["last_used"] = max(g["last_used"] or "", u.get("timestamp", ""))

    gates: Dict[str, Dict[str, int]] = {}
    for o in _lines(OUTCOME):
        gate = o.get("gate")
        if gate:
            gs = gates.setdefault(gate, {"total": 0})
            gs["total"] += 1
            st = str(o.get("status", "?"))
            gs[st] = gs.get(st, 0) + 1
            gid = o.get("champion_id")
            if gid and gid in genes:
                genes[gid].setdefault("gate_results", {}).setdefault(gate, 0)
                genes[gid]["gate_results"][gate] += 1
            continue
        uid = o.get("usage_id")
        u = usage_by_id.get(uid) if uid else None
        if not u or u.get("fallback_used"):
            continue
        gid = u.get("champion_id")
        if gid in genes:
            if o.get("status") == "COMPLETED":
                genes[gid]["completed"] += 1
            elif o.get("status") == "FAILED":
                genes[gid]["failed"] += 1

    now = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return {"schema": "brain-outcome-stats", "at": now,
            "genes_with_combat_record": len(genes),
            "total_champion_executions": sum(g["executions"] for g in genes.values()),
            "genes": genes, "gates": gates}


def write() -> Dict[str, Any]:
    stats = compute()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return stats


if __name__ == "__main__":
    s = write()
    print(f"outcome_stats: {s['genes_with_combat_record']} gene(s) with combat records, "
          f"{s['total_champion_executions']} champion execution(s), "
          f"gates={list(s['gates'].keys())} -> {OUT}")

### backend/model_gateway.py
"""HOCH Model Gateway — zero-downtime inference routing across all live backends.

Doctrine (2026-07-07): MODEL_OFFLINE is never acceptable. Three compute resources exist:
  - L1 local Mac (127.0.0.1:11434) — llama3.1:8b, primary
  - Tailscale Mac (100.103.155.4:11434) — same models, secondary
  - hoch-relay-001 (100.87.18.15:11434) — qwen3:1.7b, always-on fallback

This gateway:
  1. Probes all backends with a real generation probe (not just /api/tags listing)
  2. Routes to the best live backend with automatic failover
  3. Never returns MODEL_OFFLINE as long as ANY backend is alive
  4. Refreshes health state every 60s in a background thread
  5. Records every backend switch in the outcome ledger (transparent, traceable)

Sources:
  - HAProxy health check pattern: binadit.com/tutorials/load-balancer-multiple-ollama-instances (2026-04)
  - Generation-proven probe: Goodhart fix from scorer.py (2026-07-06) — listing != capability
  - Failover weight schedule: localaimaster.com/blog/ollama-load-balancing (2026-04)

stdlib + requests only. Drop-in replacement for AgentRunner's ollama_url + default_model.
"""
import json
import time
import logging
import threading
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

BACKENDS_CONFIG = [
    # Priority order: most capable first, relay last (always-on backstop).
    # LM Studio (gemma-4-12b) discovered live 2026-07-07 — highest local capability.
    {"name": "lmstudio",      "base": "http://127.0.0.1:1234",       "preferred_model": "google/gemma-4-12b-qat", "priority": 1, "api": "openai"},
    {"name": "mac-local",     "base": "http://127.0.0.1:11434",      "preferred_model": "llama3.1:8b",            "priority": 2, "api": "ollama", "probe_keep_alive": 0},
    # mac-tailscale REMOVED 2026-07-07: 100.103.155.4 is THIS same MacBook — a duplicate
    # of mac-local that ran a 2nd Ollama server + 2nd resident model copy, pushing free RAM
    # to ~6% and triggering macOS jetsam kills of Chrome. mac-local (127.0.0.1) already
    # serves the identical model store, so this cost RAM for zero added capability.
    {"name": "relay-001",     "base": "http://100.87.18.15:11434",    "preferred_model": "qwen3:1.7b",  "priority": 4, "api": "ollama"},
]
PROBE_TIMEOUT   = 20   # seconds for generation probe
HEALTH_INTERVAL = 60   # seconds between full health sweeps
PROBE_PROMPT    = "OK" # minimal probe — 1 token, proves generate works


@dataclass
class BackendState:
    name: str
    base: str
    preferred_model: str
    priority: int
    api: str = "ollama"   # "ollama" | "openai" (LM Studio / OpenAI-compatible)
    # probe_keep_alive: ollama keep_alive for HEALTH PROBES only. 0 = unload the model
    # right after the probe so a big failover model isn't held resident just to stay "alive"
    # (real generate calls still load on demand and use ollama's default keep_alive). None =
    # ollama default. Set 0 on heavy failover backends to protect control-plane RAM.
    probe_keep_alive: Optional[object] = None
    alive: bool = False
    proven_model: Optional[str] = None
    available_models: List[str] = field(default_factory=list)
    last_probe: float = 0.0
    consecutive_failures: int = 0
    latency_ms: Optional[float] = None


class ModelGateway:
    """Thread-safe, auto-failover inference gateway for all HOCH compute backends."""

    def __init__(self):
        self._states: List[BackendState] = [
            BackendState(**{k: v for k, v in b.items()}) for b in BACKENDS_CONFIG
        ]
        self._lock = threading.Lock()
        self._probe_all()  # synchronous initial probe so first call never misses
        self._thread = threading.Thread(target=self._health_loop, daemon=True)
        self._thread.start()
        logger.info(f"ModelGateway: {sum(1 for s in self._states if s.alive)} / "
                    f"{len(self._states)} backends alive at startup")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, prompt: str, system: Optional[str] = None,
                 model: Optional[str] = None, timeout: int = 300) -> str:
        """Generate text. Auto-routes to best live backend. Never raises MODEL_OFFLINE
        as long as any backend is reachable. Raises RuntimeError only if ALL are dead."""
        backends = self._ranked_alive()
        if not backends:
            self._probe_all()           # one emergency re-probe before giving up
            backends = self._ranked_alive()
        if not backends:
            raise RuntimeError(
                "MODEL_GATEWAY_ALL_OFFLINE: no backend is reachable — "
                "mac-local, mac-tailscale, and relay-001 all failed generation probes")

        last_err = None
        for state in backends:
            use_model = model or state.proven_model or state.preferred_model
            try:
                result = self._call_generate(state.base, use_model, prompt, system, timeout, api=state.api)
                with self._lock:
                    state.consecutive_failures = 0
                return result
            except Exception as e:
                last_err = e
                logger.warning(f"Gateway: {state.name} failed ({e}), trying next backend")
                with self._lock:
                    state.consecutive_failures += 1
                    if state.consecutive_failures >= 2:
                        state.alive = False   # mark dead; health loop will re-probe

        raise RuntimeError(f"MODEL_GATEWAY_ALL_FAILED: all live backends errored. "
                           f"Last error: {last_err}")

    def status(self) -> Dict:
        with self._lock:
            return {
                "backends": [
                    {"name": s.name, "alive": s.alive, "model": s.proven_model,
                     "latency_ms": s.latency_ms, "failures": s.consecutive_failures,
                     "last_probe": s.last_probe}
                    for s in sorted(self._states, key=lambda x: x.priority)
                ],
                "primary": next((s.name for s in self._states if s.alive), None),
                "alive_count": sum(1 for s in self._states if s.alive),
            }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _ranked_alive(self) -> List[BackendState]:
        with self._lock:
            return sorted([s for s in self._states if s.alive], key=lambda x: x.priority)

    def _call_generate(self, base: str, model: str, prompt: str,
                       system: Optional[str], timeout: int,
                       api: str = "ollama") -> str:
        if api == "openai":
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.append({"role": "user", "content": prompt})
            payload: Dict = {"model": model, "messages": msgs, "max_tokens": 2048}
            data = json.dumps(payload).encode()
            req = urllib.request.Request(f"{base}/v1/chat/completions", data=data,
                                         headers={"Content-Type": "application/json",
                                                  "Authorization": "Bearer lm-studio"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                resp = json.loads(r.read().decode())
            msg = resp["choices"][0]["message"]
            # Thinking models (gemma-4, nemotron) return content in reasoning_content
            # when content is empty — fall back gracefully.
            return msg.get("content") or msg.get("reasoning_content", "")
        payload: Dict = {"model": model, "prompt": prompt, "stream": False,
                         "options": {"num_predict": 2048}}
        if system:
            payload["system"] = system
        data = json.dumps(payload).encode()
        req = urllib.request.Request(f"{base}/api/generate", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode())
        if "error" in resp:
            raise RuntimeError(resp["error"])
        return resp.get("response", "")

    def _probe_backend(self, state: BackendState) -> bool:
        """Generation-proven probe across Ollama and OpenAI-compatible (LM Studio) backends."""
        t0 = time.time()
        api = getattr(state, 'api', 'ollama')
        try:
            if api == "openai":
                with urllib.request.urlopen(f"{state.base}/v1/models", timeout=PROBE_TIMEOUT) as r:
                    data = json.loads(r.read().decode())
                models = [m["id"] for m in data.get("data", [])
                          if "embed" not in m.get("id","").lower()]
                ordered = ([state.preferred_model] if state.preferred_model in models else []) +                           [m for m in models if m != state.preferred_model]
                for m in ordered:
                    try:
                        payload = json.dumps({"model": m,
                                              "messages": [{"role":"user","content":"OK"}],
                                              "max_tokens": 1}).encode()
                        req = urllib.request.Request(
                            f"{state.base}/v1/chat/completions", data=payload,
                            headers={"Content-Type":"application/json",
                                     "Authorization":"Bearer lm-studio"})
                        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as pr:
                            resp = json.loads(pr.read().decode())
                        if resp.get("choices"):
                            with self._lock:
                                state.alive = True; state.proven_model = m
                                state.available_models = models
                                state.latency_ms = round((time.time()-t0)*1000,1)
                                state.last_probe = time.time()
                                state.consecutive_failures = 0
                            logger.info(f"Gateway probe OK: {state.name} → {m} ({state.latency_ms}ms)")
                            return True
                    except Exception:
                        continue
            else:
                with urllib.request.urlopen(f"{state.base}/api/tags", timeout=PROBE_TIMEOUT) as r:
                    tags = json.loads(r.read().decode())
                models = [m["name"] for m in tags.get("models", [])
                          if "embed" not in m.get("name","") and "guard" not in m.get("name","")]
                ordered = ([state.preferred_model] if state.preferred_model in models else []) +                           [m for m in models if m != state.preferred_model]
                for m in ordered:
                    try:
                        _body = {"model": m, "prompt": PROBE_PROMPT,
                                 "stream": False, "options": {"num_predict": 1}}
                        if state.probe_keep_alive is not None:
                            _body["keep_alive"] = state.probe_keep_alive  # e.g. 0 = unload after probe
                        payload = json.dumps(_body).encode()
                        req = urllib.request.Request(f"{state.base}/api/generate", data=payload,
                                                     headers={"Content-Type":"application/json"})
                        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as pr:

### backend/factory/champion_loader.py
"""Champion loader — the wire between the BRAIN and real execution.

Before this module, champion prompts were consumed only by the dashboard and the
Ask-the-BRAIN retrieval layer: the 700+ evolved genes influenced no agent, mission,
or product build. This closes that gap under the live-real-only doctrine:

  - operating_prompt(task_class, domain) returns the CURRENT champion prompt for a
    task class from that factory's champion registry, or the caller's fallback.
  - Every resolution is traceable: the return includes gene_id, score, generation,
    and source ("champion" | "fallback") so any output produced with it can be tied
    back to the exact gene in the evidence ledger — no silent substitution.
  - Read-only, stdlib-only, deterministic. No model calls, no writes, $0.

Usage (agents / mission runners):
    from backend.factory.champion_loader import operating_prompt
    res = operating_prompt("Incident Response", fallback=MY_HARDCODED_PROMPT)
    system_prompt = res["prompt"]        # champion text or fallback
    provenance    = res["provenance"]    # log this alongside the output
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from backend.factory.registry import get_factory


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _load_registry(domain: str) -> Dict[str, Any]:
    f = get_factory(domain)
    if not f:
        return {}
    try:
        return json.loads(Path(f.champion_registry).read_text(encoding="utf-8"))
    except Exception:
        return {}


def operating_prompt(task_class: str, domain: str = "software",
                     fallback: Optional[str] = None) -> Dict[str, Any]:
    """Resolve task_class -> current champion prompt for a factory domain.

    Exact match on normalized class name first; unique-substring match second
    (so "incident response" finds "Incident Response"). Ambiguous or missing ->
    fallback, honestly labeled. Never raises: execution must not break because
    the brain is unavailable.
    """
    reg = _load_registry(domain)
    champs = reg.get("champions", {}) or {}
    gen = reg.get("generation")

    want = _norm(task_class)
    by_norm = {_norm(k): (k, v) for k, v in champs.items()}

    hit = by_norm.get(want)
    if hit is None and want:
        subs = [(k, v) for nk, (k, v) in by_norm.items() if want in nk or nk in want]
        if len(subs) == 1:
            hit = subs[0]

    if hit is not None:
        cls, c = hit
        prompt = c.get("prompt") or c.get("text") or ""
        if not prompt and c.get("gene_id"):
            # Some registries (music/research) store only gene_id refs; dereference the pool.
            f = get_factory(domain)
            try:
                pool = json.loads(Path(f.gene_pool).read_text(encoding="utf-8")).get("genes", {})
                g = pool.get(c["gene_id"]) or next(
                    (v for v in (pool.values() if isinstance(pool, dict) else pool)
                     if v.get("gene_id") == c["gene_id"]), None)
                if g:
                    prompt = g.get("prompt") or g.get("text") or ""
            except Exception:
                pass
        if prompt:
            return {
                "prompt": prompt,
                "source": "champion",
                "provenance": {
                    "gene_id": c.get("gene_id"),
                    "task_class": cls,
                    "domain": domain,
                    "score": c.get("score"),
                    "generation": gen,
                },
            }

    return {
        "prompt": fallback or "",
        "source": "fallback",
        "provenance": {"gene_id": None, "task_class": task_class,
                       "domain": domain, "score": None, "generation": gen,
                       "reason": "no champion for class" if want else "empty task_class"},
    }

### backend/factory/runtime_ledger.py
"""Runtime usage + outcome feedback ledgers — the proof layer for BRAIN-live.

Doctrine (operator-approved, 2026-07-06): a dashboard panel is not proof, a registry
score is not proof, a RAG answer about prompts is not proof. Only this counts:
    champion prompt selected -> used in actual execution -> outcome logged -> feedback captured.

Two append-only JSONL ledgers, hash-chained like the evidence ledger philosophy:
  data/prompt_brain/runtime_usage_ledger.jsonl    — every operating-prompt resolution USED
  data/prompt_brain/outcome_feedback_ledger.jsonl — the outcome of that execution, keyed back

Usage entry schema (exactly the operator-specified proof shape):
  timestamp, execution_surface, task_class, champion_id, fallback_used,
  registry_path, prompt_hash, outcome_ref, production_mutation_allowed
plus usage_id (sha256 prefix) so outcomes can reference their usage entry.

fallback_used=true proves the loader is SAFE, not that BRAIN drives execution.
BRAIN-live requires at least one entry with fallback_used=false from a real surface.
Stdlib only. Never raises into the execution path.
"""
import json
import hashlib
import datetime
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
USAGE_LEDGER = ROOT / "data" / "prompt_brain" / "runtime_usage_ledger.jsonl"
OUTCOME_LEDGER = ROOT / "data" / "prompt_brain" / "outcome_feedback_ledger.jsonl"


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _sha(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _append(path: Path, entry: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def record_usage(resolution: Dict[str, Any], execution_surface: str,
                 production_mutation_allowed: bool = False,
                 outcome_ref: Optional[str] = None) -> Optional[str]:
    """Log that an operating prompt (champion or fallback) was USED by an execution surface.

    `resolution` is the dict returned by champion_loader.operating_prompt().
    Returns usage_id for outcome linkage, or None if logging failed (never raises).
    """
    try:
        prov = resolution.get("provenance", {}) or {}
        from backend.factory.registry import get_factory
        f = get_factory(prov.get("domain", "software"))
        entry = {
            "timestamp": _now(),
            "execution_surface": execution_surface,
            "task_class": prov.get("task_class"),
            "champion_id": prov.get("gene_id"),
            "fallback_used": resolution.get("source") != "champion",
            "registry_path": str(f.champion_registry.relative_to(ROOT)) if f else None,
            "prompt_hash": _sha(resolution.get("prompt", "")),
            "outcome_ref": outcome_ref,
            "production_mutation_allowed": bool(production_mutation_allowed),
            "generation": prov.get("generation"),
            "score_at_selection": prov.get("score"),
        }
        entry["usage_id"] = _sha(json.dumps(entry, sort_keys=True))[:16]
        _append(USAGE_LEDGER, entry)
        return entry["usage_id"]
    except Exception:
        return None


def record_outcome(usage_id: Optional[str], outcome: Dict[str, Any]) -> bool:
    """Log the real outcome of an execution that used a ledgered prompt.

    `outcome` should carry verifiable facts only (status, gate results, response hash,
    latency, artifact paths) — never invented metrics. Returns success; never raises.
    """
    try:
        entry = {"timestamp": _now(), "usage_id": usage_id, **outcome}
        _append(OUTCOME_LEDGER, entry)
        return True
    except Exception:
        return False

## write_brain_live diff
diff --git a/scripts/write_brain_live.py b/scripts/write_brain_live.py
index dd73f3a..6bde245 100644
--- a/scripts/write_brain_live.py
+++ b/scripts/write_brain_live.py
@@ -22,6 +22,60 @@ def _load(p, default):
         return default
 
 
+
+def _combat_summary():
+    """Aggregate ledger-proven combat records — honest execution counts only."""
+    try:
+        import sys; sys.path.insert(0, str(ROOT))
+        from backend.factory.outcome_stats import write as _write_stats
+        st = _write_stats()
+        top = sorted(st.get("genes", {}).items(),
+                     key=lambda kv: kv[1].get("executions", 0), reverse=True)[:10]
+        return {"at": st.get("at"),
+                "genes_with_combat_record": st.get("genes_with_combat_record", 0),
+                "total_champion_executions": st.get("total_champion_executions", 0),
+                "gates": st.get("gates", {}),
+                "top": [{"gene_id": g, **v} for g, v in top]}
+    except Exception:
+        return {}
+
+
+def _gateway_summary():
+    """Live gateway status — all backends, proven generation, no listing fake-out."""
+    try:
+        import sys; sys.path.insert(0, str(ROOT))
+        from backend.model_gateway import get_gateway
+        st = get_gateway().status()
+        return st
+    except Exception:
+        return {}
+
+
+def _fleet_summary(cluster_mgr=None):
+    """Real fleet telemetry — authority-labeled, never fabricated."""
+    try:
+        import sys, time
+        sys.path.insert(0, str(ROOT))
+        if cluster_mgr:
+            st = cluster_mgr.get_cluster_status()
+        else:
+            from backend.cluster_manager import ClusterManager
+            cm = ClusterManager(); time.sleep(1.5)
+            st = cm.get_cluster_status()
+        return {
+            "status": st.get("status"), "sync": st.get("sync"),
+            "latency": st.get("latency"), "reachable": st.get("active_assets"),
+            "telemetry_note": st.get("telemetry_note"),
+            "nodes": [{"id": n.get("id"), "status": n.get("status"),
+                       "cpu": n.get("cpu_usage"), "ram": n.get("ram_usage"),
+                       "agents": n.get("total_agents"), "latency_ms": n.get("latency_ms"),
+                       "authority": n.get("telemetry_authority"),
+                       "activity": n.get("activity", "")} for n in st.get("nodes", [])]
+        }
+    except Exception:
+        return {}
+
+
 def _factories_summary():
     """Per-factory live summary across ALL registered Factories (HASF/HMF/HRF/...).
     Each field comes from that domain's real state files; a domain that hasn't run yet shows its
@@ -51,7 +105,7 @@ def _factories_summary():
     return out
 
 
-def build_live_state():
+def build_live_state(cluster_mgr=None):
     """Assemble the live BRAIN state dict from real state files + live model detection.
     Reusable by both the static writer (main) and the /api/brain/live endpoint."""
     conv = _load(DATA / "convergence_status.json", {})
@@ -148,8 +202,13 @@ def build_live_state():
         "recent_improvements": list(reversed(improvements))[:8],
         "top_champions": sorted(
             [{"cls": k, "title": v.get("title", "")[:40], "score": v.get("score", 0),
-              "state": v.get("state", "")} for k, v in champs.items()],
+              "state": v.get("state", ""),
+              "fitness_method": v.get("fitness_method", "MECHANICAL_PROXY"),
+              "blended_score": v.get("blended_score")} for k, v in champs.items()],
             key=lambda x: -x["score"])[:6],
+        "combat": _combat_summary(),
+        "fleet": _fleet_summary(cluster_mgr),
+        "gateway": _gateway_summary(),
     }
     return out
 

## cluster_manager diff

## Compile scoped Python

## Forbidden behavior scan
461:Ask-the-BRAIN retrieval layer: the 700+ evolved genes influenced no agent, mission,

## Existing focused tests
..................                                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/fastapi/testclient.py:1
  /Users/michaelhoch/hoch_agent_swarm/.venv/lib/python3.13/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

backend/main.py:5362
  /Users/michaelhoch/hoch_agent_swarm/backend/main.py:5362: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    @app.on_event("startup")

.venv/lib/python3.13/site-packages/fastapi/applications.py:4675
  /Users/michaelhoch/hoch_agent_swarm/.venv/lib/python3.13/site-packages/fastapi/applications.py:4675: DeprecationWarning: 
          on_event is deprecated, use lifespan event handlers instead.
  
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    return self.router.on_event(event_type)  # ty: ignore[deprecated]

backend/brain/doctrine_memory.py:53: 59 warnings
  /Users/michaelhoch/hoch_agent_swarm/backend/brain/doctrine_memory.py:53: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    """, (rule_id, rule_text, datetime.utcnow().isoformat() + "Z"))

backend/brain/doctrine_memory.py:67: 15 warnings
  /Users/michaelhoch/hoch_agent_swarm/backend/brain/doctrine_memory.py:67: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    """, (rule_id, r, datetime.utcnow().isoformat() + "Z"))

tests/test_prompt_v4.py::test_run_prompt
  /Users/michaelhoch/hoch_agent_swarm/backend/runtime_execution_store.py:1845: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

tests/test_prompt_v4.py::test_run_prompt
  /Users/michaelhoch/hoch_agent_swarm/backend/main.py:4441: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

tests/test_prompt_v4.py::test_run_prompt
  /Users/michaelhoch/hoch_agent_swarm/backend/main.py:4448: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
    "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
18 passed, 80 warnings in 45.61s

## Runtime containment
Containment CLEAN
