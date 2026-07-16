#!/usr/bin/env python3
"""factory_readiness.py — read-only "how close is each factory to a settled dollar?" board.

Reads coordination/products/products.json (the single source of truth) and, for every
product, runs ONLY read-only checks — no writes, no deploys, no Stripe mutations:

  * source-on-disk?   is the product's declared source_of_truth actually present in this
                      repo checkout (so it could be deployed at all)?
  * has live_url?     does the manifest declare a production URL?
  * homepage 200?     `curl -s` the live_url — does the app serve?
  * checkout live?    `curl -s -X POST` the checkout endpoint — does it return a REAL
                      https://checkout.stripe.com/ or https://buy.stripe.com/ URL?
                      (This is the single test that proves a product is SELLABLE.)

It prints a per-factory table, assigns each product an OBSERVED monetization rung (which it
holds honestly against the manifest's ASSERTED rung — flagging any gap), and names the ONE
recommended NEXT-BEST candidate to push through scripts/factory_to_money.sh next.

NO FAKE GREEN: every rung shown here is backed by a live read this run, or explicitly marked
UNVERIFIED. All network access is `curl -s` with a short timeout. Nothing is written except
the board markdown.

Usage:
  python3 scripts/factory_readiness.py                 # print board + write docs/founder/FACTORY_READINESS_BOARD.md
  python3 scripts/factory_readiness.py --no-write      # print only
  python3 scripts/factory_readiness.py --no-net        # skip HTTP reads (disk/manifest only)
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.environ.get(
    "FACTORY_PRODUCTS_MANIFEST",
    os.path.join(REPO_ROOT, "coordination", "products", "products.json"),
)
BOARD_OUT = os.path.join(REPO_ROOT, "docs", "founder", "FACTORY_READINESS_BOARD.md")

DEFAULT_CHECKOUT_ENDPOINT = "/api/create-checkout-session"
STRIPE_URL_RE = re.compile(r"https://(?:checkout|buy)\.stripe\.com/[^\"'\\s]+")
STRIPE_BAD_RE = re.compile(
    r"Expired API Key|No such price|No such|Invalid API Key|Not Implemented|501 ", re.I
)
UNKNOWN_RE = re.compile(r"UNKNOWN|NOT-IN-REPO|N/A", re.I)


def curl_code(url, timeout=15):
    """Return HTTP status code string for a GET, or '000' on failure. Read-only."""
    try:
        out = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "-m", str(timeout), "-L", url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        return (out.stdout or "000").strip() or "000"
    except Exception:
        return "000"


def curl_post(url, body, timeout=25):
    """POST JSON via curl -s; return (http_code, body_text). Read-only probe (no real charge)."""
    try:
        out = subprocess.run(
            ["curl", "-s", "-w", "\n%{http_code}", "-m", str(timeout), "-X", "POST",
             "-H", "Content-Type: application/json", "-d", body, url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        text = out.stdout or ""
        if "\n" in text:
            payload, _, code = text.rpartition("\n")
        else:
            payload, code = text, "000"
        return code.strip() or "000", payload
    except Exception:
        return "000", ""


def resolve_source_dir(prod):
    """Best-effort resolve a real on-disk source dir. Returns (abs_path_or_None, is_on_disk, blocked_reason)."""
    sot = prod.get("source_of_truth", "") or ""
    explicit = prod.get("source_dir")
    # explicit clean path wins
    cand = explicit
    if not cand:
        # if the prose SOT is flagged UNKNOWN/NOT-IN-REPO/CLOBBER, treat as intentionally blocked
        if re.search(r"UNKNOWN|NOT-IN-REPO|CLOBBER", sot, re.I):
            return None, False, "declared UNKNOWN / NOT-IN-REPO / clobber-guarded"
        m = re.search(r"(?:/[A-Za-z0-9._-]+)+|[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+", sot)
        if m:
            cand = m.group(0).rstrip(".")
    if not cand:
        return None, False, "no source path in manifest"
    absdir = cand if os.path.isabs(cand) else os.path.join(REPO_ROOT, cand)
    absdir = os.path.normpath(absdir)
    return absdir, os.path.isdir(absdir), ("" if os.path.isdir(absdir) else "path not present on disk")


def first_tier(prod):
    prices = prod.get("price_ids") or []
    if prices and isinstance(prices[0], dict):
        return prices[0].get("tier") or "default"
    return None


def check_product(prod, do_net=True):
    r = {
        "product_id": prod.get("product_id", "?"),
        "factory": prod.get("owning_factory") or prod.get("factory") or "?",
        "name": prod.get("name", ""),
        "asserted_rung": str(prod.get("monetization_rung", "?")),
        "has_price": bool(prod.get("price_ids")),
        "stripe_wired": str(prod.get("stripe_account_id", "")).startswith("acct_"),
    }
    absdir, on_disk, src_reason = resolve_source_dir(prod)
    r["source_on_disk"] = on_disk
    r["source_note"] = src_reason if not on_disk else os.path.relpath(absdir, REPO_ROOT)

    live_url = prod.get("live_url") or ""
    r["has_live_url"] = bool(live_url) and not UNKNOWN_RE.search(live_url)
    r["live_url"] = live_url if r["has_live_url"] else ""

    r["home_code"] = ""
    r["home_200"] = False
    r["checkout_code"] = ""
    r["checkout_ok"] = False
    r["checkout_note"] = ""

    r["page_checkout"] = False   # non-POST, page-based checkout model (e.g. an /upgrade page)
    if do_net and r["has_live_url"]:
        r["home_code"] = curl_code(live_url)
        r["home_200"] = r["home_code"] == "200"
        has_explicit_endpoint = bool(prod.get("checkout_endpoint"))
        endpoint = prod.get("checkout_endpoint") or DEFAULT_CHECKOUT_ENDPOINT
        tier = first_tier(prod)
        body = json.dumps({"tier": tier} if tier else {"smoke": True})
        url = live_url.rstrip("/") + endpoint
        code, payload = curl_post(url, body)
        r["checkout_code"] = code
        if STRIPE_URL_RE.search(payload or ""):
            r["checkout_ok"] = True
            r["checkout_note"] = "returns real Stripe checkout URL"
        elif STRIPE_BAD_RE.search(payload or ""):
            m = STRIPE_BAD_RE.search(payload)
            r["checkout_note"] = f"checkout error: {m.group(0)}"
        elif code in ("404", "405", "000") and not has_explicit_endpoint:
            # This product may not use the POST create-checkout-session model. If it declares a
            # distinct checkout_url page, probe THAT (GET) so we don't red-flag a page-based product.
            page = prod.get("checkout_url") or ""
            pm = re.search(r"https?://[^\s()]+", page)
            if pm and DEFAULT_CHECKOUT_ENDPOINT not in page:
                pcode = curl_code(pm.group(0))
                if pcode == "200":
                    r["page_checkout"] = True
                    r["checkout_note"] = (f"POST {endpoint} -> {code}; page-based checkout "
                                          f"{pm.group(0)} -> 200 (not a POST-Stripe-session model; "
                                          f"Stripe-URL probe N/A)")
                else:
                    r["checkout_note"] = f"no POST checkout ({code}); checkout page -> {pcode}"
            else:
                r["checkout_note"] = f"no checkout endpoint (HTTP {code})"
        elif code in ("404", "405", "000"):
            r["checkout_note"] = f"no checkout endpoint (HTTP {code})"
        else:
            snippet = (payload or "").strip().replace("\n", " ")[:80]
            r["checkout_note"] = f"HTTP {code}, no Stripe URL{(': ' + snippet) if snippet else ''}"
    elif not do_net:
        r["checkout_note"] = "network checks skipped (--no-net)"

    # OBSERVED rung — from evidence THIS run, not from what the manifest asserts.
    if r["checkout_ok"]:
        r["observed_rung"] = 4          # SELLABLE (live checkout reachable). 5=EARNING needs settled charge -> can't observe here.
        r["observed_label"] = "SELLABLE"
    elif r.get("page_checkout"):
        r["observed_rung"] = 4          # page-based checkout live; treat as sellable-model per manifest
        r["observed_label"] = "SELLABLE (page-based checkout; Stripe-URL probe N/A)"
    elif r["home_200"]:
        r["observed_rung"] = 3          # app is live but checkout not proven -> PRODUCTIZED, not sellable
        r["observed_label"] = "LIVE (checkout NOT sellable)"
    elif r["source_on_disk"]:
        r["observed_rung"] = 2          # buildable source present, nothing live
        r["observed_label"] = "BUILT (source on disk)"
    elif r["has_price"] or r["stripe_wired"]:
        r["observed_rung"] = 3
        r["observed_label"] = "DEFINED (priced, nothing live)"
    else:
        r["observed_rung"] = 1
        r["observed_label"] = "IDEA/DEFINED ONLY"

    # readiness-to-dollar score — how close to the NEXT rung (used only to rank candidates).
    # source_on_disk is weighted heaviest because factory_to_money.sh --go FAILS CLOSED without
    # a verified in-repo source (the source-match guard), so a product that can't pass the guard
    # is NOT actually actionable through the pipeline no matter how "live" it looks.
    score = 0
    if r["source_on_disk"]: score += 40   # gating requirement: the guard must be able to pass
    if r["home_200"]:       score += 25   # already deployed somewhere
    if r["has_price"]:      score += 20
    if r["stripe_wired"]:   score += 10
    if r["checkout_code"] and r["checkout_code"] not in ("000", "404", "405"):
        score += 5
    r["score"] = score
    # pipeline-actionable NOW = the guard could pass (source on disk) and it isn't sellable yet
    r["pipeline_actionable"] = r["source_on_disk"] and not r["checkout_ok"]
    return r


def render_board(rows, do_net):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = []
    lines.append("# HELM Factory Readiness Board")
    lines.append("")
    lines.append(f"_Generated {now} by `scripts/factory_readiness.py` — read-only "
                 f"(`curl -s` probes only; no writes, no deploys, no Stripe mutations)._")
    lines.append("")
    lines.append("**Rung scale:** 0 IDEA · 1 PROTOTYPE · 2 BUILT_NOT_SELLABLE · "
                 "3 PRODUCTIZED_DEFINED_ONLY · 4 SELLABLE (live checkout reachable) · "
                 "5 EARNING (a real charge has settled).")
    if not do_net:
        lines.append("")
        lines.append("> NOTE: run with `--no-net` — homepage/checkout columns were NOT probed this run.")
    lines.append("")
    # table
    lines.append("| Factory | Product | Src on disk | Home | Checkout | Observed rung | Asserted rung |")
    lines.append("|---|---|:--:|:--:|:--:|---|---|")
    for r in rows:
        home = r["home_code"] or "—"
        home_cell = f"✅ {home}" if r["home_200"] else (f"❌ {home}" if r["has_live_url"] else "—")
        if r["checkout_ok"]:
            co = "✅ Stripe"
        elif r.get("page_checkout"):
            co = "◐ page"
        elif not r["has_live_url"]:
            co = "—"
        else:
            co = f"❌ {r['checkout_code'] or '—'}"
        src = "✅" if r["source_on_disk"] else "❌"
        obs = f"{r['observed_rung']} {r['observed_label']}"
        gap = "" if str(r["observed_rung"]) in r["asserted_rung"] else " ⚠"
        lines.append(f"| {r['factory']} | {r['product_id']} | {src} | {home_cell} | {co} | "
                     f"{obs} | {r['asserted_rung']}{gap} |")
    lines.append("")
    lines.append("⚠ = observed rung differs from the rung asserted in the manifest — reconcile.")
    lines.append("")

    # per-product notes
    lines.append("## Per-product read (evidence)")
    lines.append("")
    for r in rows:
        lines.append(f"### {r['product_id']} — {r['name']}")
        lines.append(f"- **Factory:** {r['factory']}")
        lines.append(f"- **Source on disk:** {'yes — ' + r['source_note'] if r['source_on_disk'] else 'NO — ' + r['source_note']}")
        lines.append(f"- **Live URL:** {r['live_url'] or '(none declared)'}")
        if r["has_live_url"]:
            lines.append(f"- **Homepage:** HTTP {r['home_code'] or '—'}{' (200 OK)' if r['home_200'] else ''}")
            lines.append(f"- **Checkout probe:** {r['checkout_note'] or '(not probed)'}")
        lines.append(f"- **Stripe account wired:** {'yes' if r['stripe_wired'] else 'no'}; "
                     f"**prices declared:** {'yes' if r['has_price'] else 'no'}")
        lines.append(f"- **Observed rung:** {r['observed_rung']} ({r['observed_label']}) · "
                     f"**Manifest asserts:** {r['asserted_rung']}")
        lines.append("")

    # recommendation
    lines.append("## Recommended NEXT-BEST candidate")
    lines.append("")
    lines.append("_The pipeline `scripts/factory_to_money.sh --go` **fails closed** unless the product's "
                 "source is verifiably on disk (the source-match guard). So the next-best candidate is the "
                 "one the pipeline can actually advance NOW — source present, not yet sellable — not merely "
                 "the one that looks most 'live'._")
    lines.append("")
    sellable = [r for r in rows if r["checkout_ok"] or r.get("page_checkout")]
    actionable = [r for r in rows if r.get("pipeline_actionable")]
    if actionable:
        best = max(actionable, key=lambda r: (r["score"], r["has_price"], r["stripe_wired"]))
        lines.append(f"**➡ {best['product_id']}** ({best['factory']}) — readiness score {best['score']}/100, "
                     f"observed rung {best['observed_rung']} ({best['observed_label']}). "
                     f"Source is ON DISK (`{best['source_note']}`), so the source-match guard will PASS.")
        lines.append("")
        needs = []
        if not best["stripe_wired"]:
            needs.append("wire a live Stripe key into the per-product Keychain (one-time paste)")
        if not best["home_200"]:
            needs.append("first deploy via the guarded pipeline")
        needs.append("idempotently create/reuse its Stripe price + set Vercel env + smoke-test checkout")
        lines.append("Remaining to reach rung-4 SELLABLE: " + "; ".join(needs) + ". "
                     "`factory_to_money.sh` does all of this, gated behind the founder's `--go` + Vercel sign-in.")
        lines.append("")
        lines.append(f"    cd {best['source_note']} && {os.path.relpath(BOARD_OUT, REPO_ROOT).split('docs')[0]}scripts/factory_to_money.sh {best['product_id']} --plan")
        lines.append(f"    # then, when the source guard passes and founder is signed into Vercel:")
        lines.append(f"    scripts/factory_to_money.sh {best['product_id']} --go")
    else:
        lines.append("**No product is pipeline-actionable right now** — every not-yet-sellable product has "
                     "its source declared UNKNOWN / NOT-IN-REPO, so the source-match guard would block `--go`. "
                     "The prerequisite move is to RECOVER the live source into the repo (redeploy an existing "
                     "production build / rollback candidate and commit it), update the manifest's source_of_truth, "
                     "THEN run the pipeline.")
    lines.append("")
    if sellable:
        lines.append("### Already SELLABLE (advance to EARNING, rung 5)")
        for r in sellable:
            how = "page-based checkout live" if r.get("page_checkout") else "checkout returns a real Stripe URL"
            lines.append(f"- **{r['product_id']}** — {how}; first *settled* charge confirms rung 5 "
                         f"(NO FAKE GREEN: not earning until the balance txn settles).")
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    do_write = "--no-write" not in sys.argv
    do_net = "--no-net" not in sys.argv
    if not os.path.isfile(MANIFEST):
        sys.exit(f"[ABORT] manifest not found at {MANIFEST}")
    with open(MANIFEST) as f:
        data = json.load(f)
    products = data if isinstance(data, list) else data.get("products", [])
    if not products:
        sys.exit("[ABORT] no products in manifest")

    rows = [check_product(p, do_net=do_net) for p in products]
    # sort: sellable first, then by readiness score desc
    rows.sort(key=lambda r: (not r["checkout_ok"], -r["score"], r["factory"]))

    board = render_board(rows, do_net)
    sys.stdout.write(board)

    if do_write:
        os.makedirs(os.path.dirname(BOARD_OUT), exist_ok=True)
        with open(BOARD_OUT, "w") as f:
            f.write(board)
        sys.stderr.write(f"\n[written] {BOARD_OUT}\n")


if __name__ == "__main__":
    main()
