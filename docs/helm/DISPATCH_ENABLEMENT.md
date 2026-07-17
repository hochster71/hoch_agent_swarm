# Dispatch Enablement — teed to the founder's last click

PERT node **N6_DISPATCH** is BLOCKED_FOUNDER on provider credentials. Here is the
exact, fail-closed path to enable it. Two halves — the credential half is yours now;
the adapter-body half is post-verification (touches the frozen audit target).

## Half 1 — credentials (FOUNDER, now; safe)
```bash
mkdir -p ~/.helm && cp deploy/helm.env.template ~/.helm/helm.env && chmod 600 ~/.helm/helm.env
# edit ~/.helm/helm.env and paste your real keys (your action; never through Claude)
set -a; . ~/.helm/helm.env; set +a
python3 scripts/helm_validate_credentials.py --live      # confirms CONFIGURED/VALID; prints NO key values
```
The moment those env vars are present when the HELM server runs, the existing adapters'
`credential_present()` flips each worker from BLOCKED → configured, and `/command` +
`/pert-live` reflect it live. **No repo file changes; the frozen audit target is untouched.**

Secret discipline: `~/.helm/helm.env` is gitignored and founder-controlled. Claude never
reads/stores/echoes the values — only presence (and optional HTTP-200 validity) is reported.

## Half 2 — live invoke bodies (BUILT; new files, frozen target untouched)
The real call bodies are implemented in **`backend/dispatch/`** (`live_adapters.py`,
`live_gateway.py`) — they **subclass** the frozen `ProviderAdapter` and are **injected**
into the existing `DispatchGateway` by composition, so the frozen verification target
`d8d5139a…` is **byte-unchanged** (verified). `HELM fires the models`, e.g.
`scripts/helm_fire_verification.py` dispatches Grok itself.

**Founder money-gate (fail-closed):** no provider is ever called unless BOTH
`HELM_DISPATCH_ENABLED=1` **and** the key are present. Enable once:
```bash
set -a; . ~/.helm/helm.env; set +a       # keys
export HELM_DISPATCH_ENABLED=1            # master switch (money gate)
python3 scripts/helm_fire_verification.py # HELM fires Grok; verdict -> GROK_VERDICT_<UTC>/
```

## Net — HELM fires the models, not the founder
- **Founder enables ONCE** (keys + `HELM_DISPATCH_ENABLED=1`). That is not you running
  Grok by hand — it is you unlocking HELM to run it.
- After that, `dispatch(role=…, capability=…, prompt=…)` calls the bound provider
  (Grok for audit, ChatGPT for orchestration, local for cheap tasks) autonomously.
- Until enabled, every call fails closed (`DispatchNotEnabledError`) — no fake success.
