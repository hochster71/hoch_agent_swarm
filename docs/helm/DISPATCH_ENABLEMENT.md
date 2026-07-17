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

## Half 2 — live invoke bodies (POST-VERIFICATION; Builder)
Configured credentials make workers *reachable-ready*, but actual dispatch still
fails closed (`DispatchNotEnabledError`) until each adapter's `invoke/stream/cancel`
body is implemented. Those bodies live in `dispatch_gateway.py` / `provider_router.py`,
which **are** the frozen verification target `d8d5139a…`. Implementing them now would
contaminate the pending audit, so per sequence they are the **first EDR-0002 follow-on
after the independent verdict** — then N6 flips fully to DONE.

## Net
- **You can do Half 1 right now** → workers show CONFIGURED (honest), dispatch still
  fail-closed until Half 2.
- **Half 2 waits for the verdict** (frozen-target discipline).
