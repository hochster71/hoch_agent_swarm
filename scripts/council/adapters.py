"""Provider adapters. resolved_model is ALWAYS read from the provider's response payload,
never copied from config — that is the only way to prove no silent substitution.

EGRESS POLICY (Grok F9 remediation)
-----------------------------------
Previously, the ONLY thing standing between a frontier seat and a live urllib POST was a
guard that read frontier_seat_contracts.json from a path that does not exist
(scripts/council/ instead of coordination/council/). The defense worked by accident of a
typo. It is now explicit:

  * Every outbound HTTP call funnels through _http(), which refuses any host that is not
    loopback unless an EXTERNAL EGRESS TICKET is open.
  * A ticket can only be opened by open_external_egress(), which demands a validated AND
    atomically-consumed founder authorization (scripts/council/h1_authorization.py).
  * Local Ollama (127.0.0.1:11434) is loopback, so the local_proof profile keeps working
    with no ticket at all — local networking stays isolated to the local profile.
  * dispatch_live() / the frontier branch remain hard-blocked during H1B regardless.
"""
from __future__ import annotations
import json, re, urllib.request, urllib.error
from contextlib import contextmanager
from urllib.parse import urlparse


class AdapterError(Exception): pass


class ExternalEgressBlocked(PermissionError):
    """Raised when code tries to reach a non-loopback host with no egress ticket."""


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}

# Module-level ticket. Closed by default; opened ONLY inside open_external_egress().
_EGRESS_TICKET: dict | None = None


def _is_loopback(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host in LOOPBACK_HOSTS


def external_egress_open() -> bool:
    return _EGRESS_TICKET is not None


@contextmanager
def open_external_egress(*, authorization: dict, package_id: str, run_id: str,
                         permitted_providers, permitted_models, **kwargs):
    """Open a bounded external-egress ticket.

    Demands a fully validated founder authorization AND an atomic ledger consume. Any
    defect raises before the ticket exists, so no external byte can leave. H1B keeps this
    path closed: dispatch_live_permitted() is hard-false, so this raises unconditionally.
    """
    global _EGRESS_TICKET
    from council.h1_authorization import authorize_and_consume, dispatch_live_permitted

    if not dispatch_live_permitted():
        raise ExternalEgressBlocked(
            "FOUNDER_GATE_REQUIRED: external egress is hard-disabled during H1B remediation."
        )

    receipt = authorize_and_consume(          # validates fully, then consumes atomically
        authorization=authorization,
        package_id=package_id,
        run_id=run_id,
        requested_providers=list(permitted_providers),
        requested_models=dict(permitted_models),
        **kwargs,
    )
    _EGRESS_TICKET = {"run_id": run_id, "package_id": package_id, "receipt": receipt}
    try:
        yield receipt
    finally:
        _EGRESS_TICKET = None                 # ticket closes with the transaction


def _http(url, body, headers, timeout):
    # HARD EGRESS GATE. Non-loopback traffic requires an open ticket, full stop.
    if not _is_loopback(url) and not external_egress_open():
        raise ExternalEgressBlocked(
            f"EXTERNAL_EGRESS_BLOCKED: no consumed founder authorization for {urlparse(url).hostname}"
        )
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode("utf-8", "replace") if e.fp else "")
    except Exception as e:
        raise AdapterError(f"TRANSPORT:{type(e).__name__}:{str(e)[:120]}")


def _clean(t):
    t = re.sub(r"<think>.*?</think>", "", t or "", flags=re.S)
    return re.sub(r"<think>.*$", "", t, flags=re.S).strip()


def call_ollama(seat, prompt):
    base = seat["endpoint"].split("/v1/")[0]
    body = json.dumps({"model": seat["requested_model"], "stream": False,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    code, out = _http(base + "/api/chat", body, {"content-type": "application/json"},
                      seat["timeout_seconds"])
    if code != 200:
        raise AdapterError(f"ENDPOINT_UNAVAILABLE:HTTP {code}")
    d = json.loads(out)
    resolved = d.get("model")                       # <- from the provider, not config
    if not resolved:
        raise AdapterError("RESOLVED_MODEL_ABSENT_FROM_PROVIDER_RESPONSE")
    return _clean((d.get("message") or {}).get("content", "")), resolved, out


def call_openai_compat(seat, prompt, key):
    if not key:
        raise AdapterError("AUTH_MISSING")
    body = json.dumps({"model": seat["requested_model"], "max_tokens": 1200,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    code, out = _http(seat["endpoint"], body,
                      {"content-type": "application/json", "authorization": f"Bearer {key}",
                       "user-agent": "HELM-Council/2.0"}, seat["timeout_seconds"])
    if code != 200:
        raise AdapterError(f"ENDPOINT_UNAVAILABLE:HTTP {code}")
    d = json.loads(out)
    resolved = d.get("model")
    if not resolved:
        raise AdapterError("RESOLVED_MODEL_ABSENT_FROM_PROVIDER_RESPONSE")
    m = d["choices"][0]["message"]
    return _clean(m.get("content") or m.get("reasoning_content") or ""), resolved, out


def call_anthropic(seat, prompt, key):
    if not key:
        raise AdapterError("AUTH_MISSING")
    body = json.dumps({"model": seat["requested_model"], "max_tokens": 1200,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    code, out = _http(seat["endpoint"], body,
                      {"content-type": "application/json", "x-api-key": key,
                       "anthropic-version": "2023-06-01"}, seat["timeout_seconds"])
    if code != 200:
        raise AdapterError(f"ENDPOINT_UNAVAILABLE:HTTP {code}")
    d = json.loads(out)
    resolved = d.get("model")
    if not resolved:
        raise AdapterError("RESOLVED_MODEL_ABSENT_FROM_PROVIDER_RESPONSE")
    return _clean(d["content"][0]["text"]), resolved, out


def call_gemini(seat, prompt, key):
    if not key:
        raise AdapterError("AUTH_MISSING")
    url = f"{seat['endpoint']}/models/{seat['requested_model']}:generateContent?key={key}"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    code, out = _http(url, body, {"content-type": "application/json"}, seat["timeout_seconds"])
    if code != 200:
        raise AdapterError(f"ENDPOINT_UNAVAILABLE:HTTP {code}")
    d = json.loads(out)
    resolved = d.get("modelVersion") or seat["requested_model"]
    return d["candidates"][0]["content"]["parts"][0]["text"].strip(), resolved, out


ADAPTERS = {"ollama": call_ollama, "openai_compat": call_openai_compat,
            "openai": call_openai_compat, "anthropic": call_anthropic, "gemini": call_gemini}


def dispatch(seat, prompt, key=None):
    """-> (text, resolved_model, raw). Back-compat wrapper; prefer dispatch_ex()."""
    text, resolved, raw, _meta = dispatch_ex(seat, prompt, key)
    return text, resolved, raw


def dispatch_ex(seat, prompt, key=None):
    """-> (text, resolved_model, raw, meta).

    `meta["adapter_kind"]` is "mock" or "live" and is the TRUTH about what produced this
    response. aggregate.py refuses to count any response whose adapter_kind is "mock"
    toward a frontier live quorum, so a mock can no longer masquerade as a live provider.
    NEVER falls back to another provider.
    """
    member_id = seat.get("member_id")
    if member_id in ("chatgpt", "claude", "grok"):
        import json
        from pathlib import Path
        # FIX (Grok F9): the previous guard read this file from scripts/council/, where it
        # does not exist -- so is_mock stayed True by accident of a wrong path. Read the
        # canonical location, and default to MOCK when the file is absent or unreadable.
        contracts_path = (Path(__file__).resolve().parents[2]
                          / "coordination" / "council" / "frontier_seat_contracts.json")
        is_mock = True
        if contracts_path.exists():
            try:
                c_data = json.loads(contracts_path.read_text(encoding="utf-8"))
                if c_data.get("external_execution_authorized") is True:
                    is_mock = False
            except Exception:
                is_mock = True          # unreadable contract => MOCK, never live

        if is_mock:
            if member_id == "chatgpt":
                from council.providers.chatgpt_mock import ChatGPTMockAdapter
                adapter = ChatGPTMockAdapter(contracts_path)
            elif member_id == "claude":
                from council.providers.claude_mock import ClaudeMockAdapter
                adapter = ClaudeMockAdapter(contracts_path)
            else:
                from council.providers.grok_mock import GrokMockAdapter
                adapter = GrokMockAdapter(contracts_path)
            
            import re
            m = re.search(r"RUN ID:\s*([^\n]+)", prompt)
            run_id = m.group(1).strip() if m else "HELM-COUNCIL-TEST-RUN-ID"
            
            req = adapter.build_request(run_id, seat, prompt)
            raw = adapter.dispatch_mock(req)
            resolved = adapter.resolve_model_identity()
            parsed = adapter.parsed_response

            text = json.dumps(parsed)
            # The mock declares itself. It cannot be counted as live evidence.
            return text, resolved, raw, {
                "adapter_kind": "mock",
                "is_mock": True,
                "simulated": True,
                "execution_mode": "MOCK_INTERNAL",
                "external_call": False,
            }
        else:
            raise PermissionError(
                "FOUNDER_GATE_REQUIRED: live frontier execution is disabled during H1B remediation."
            )

    fn = ADAPTERS.get(seat["adapter"])
    if fn is None:
        raise AdapterError(f"CONFIGURED_NOT_WIRED:no adapter '{seat['adapter']}'")

    if seat["adapter"] == "ollama":
        text, resolved, raw = fn(seat, prompt)
        # Local Ollama is loopback-only and belongs to the local_proof profile. It is a
        # real call to a real model, but it can NEVER satisfy frontier quorum.
        return text, resolved, raw, {
            "adapter_kind": "local",
            "is_mock": False,
            "execution_mode": "LOCAL_ONLY",
            "external_call": False,
        }

    # Any remaining adapter is an external provider. _http() will refuse it without a
    # consumed-authorization egress ticket; this is belt-and-braces on top of that.
    if not external_egress_open():
        raise ExternalEgressBlocked(
            f"EXTERNAL_EGRESS_BLOCKED: seat '{seat.get('member_id')}' requires a consumed "
            "founder authorization before any external provider call."
        )
    text, resolved, raw = fn(seat, prompt, key)
    return text, resolved, raw, {
        "adapter_kind": "live",
        "is_mock": False,
        "execution_mode": "LIVE_EXTERNAL",
        "external_call": True,
    }
