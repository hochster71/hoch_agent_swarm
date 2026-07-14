# HELM PROMPT PLAYBOOK
### How to ask so the AI stops looping — for Michael Hoch

You are not looping because the models are weak. You are looping because most prompts let
the model return a **claim** instead of **evidence**, and a claim that turns out false
sends you around again. Every loop today had the same shape: "I see passes" vs. "the API
returned 200." The whole fix is: **make every request end in a check the machine runs, not
a sentence the model writes.**

---

## 1. THE ANATOMY OF A REQUEST THAT DOESN'T LOOP

Weak (loops): *"set up the supabase key."*
Strong (lands): the five parts below. Miss one and you get a loop.

| Part | Ask it as | Example |
|---|---|---|
| **GOAL** | the observable end state | "the Stripe webhook can grant a paid user access" |
| **MECHANISM** | *how*, if you know it | "via `supabase login` + `projects api-keys`, not the dashboard" |
| **PROOF** | the exact test that = done | "a real admin API call returns HTTP 200" |
| **CONSTRAINTS** | what must not happen | "key never printed, never in shell history" |
| **DONE** | one sentence, binary | "done = re-running the proof after deploy returns 200" |

> **The magic word is PROVE.** "Do X **and prove it worked with a command whose output you
> show me**" converts the model from a storyteller into an instrument. Almost every loop
> you hit today would have died on the first try if the original ask had ended in "…and
> prove it with a live check, not a description."

**The exact prompt you should have used for the Supabase key:**

> "Write a bash script that logs into Supabase via the CLI, pulls the `service_role` key
> for the project in `NEXT_PUBLIC_SUPABASE_URL`, **proves it works with a real admin API
> call before saving anything**, writes it to `.env.local` (chmod 600) and Vercel, redeploys,
> and **re-proves** it. The key must never print to screen or shell history. Done = the
> post-deploy admin call returns 200. If you can't do any step, say so — don't substitute."

That last line — **"if you can't, say so, don't substitute"** — is what stops a model from
handing you a paste-the-key workaround when you asked for a login flow. (I did exactly that
to you; that sentence would have caught me.)

---

## 2. THE FOUR SENTENCES THAT KILL LOOPS

Paste these verbatim when an answer smells like a claim:

1. **"Prove it. Show me the command and its raw output, not a summary."**
2. **"Did the API return that, or did you infer it? If inferred, go verify."**
3. **"What would this look like if it were broken? Run that check now."**
4. **"You said PASS — re-run the exact check and paste the output. I don't trust the word, I trust the 200."**

Every one of these came up today. Every time I ran the real check instead of asserting,
we found the actual bug (the empty service key, the expired key still at HTTP 200, the
fake "0 users"). That's not me being careful — that's the *question* being shaped so a
lie can't survive it.

---

## 3. HELM QA & AUDIT PROMPT LIBRARY

Reusable. Aimed at landing HELM + the factories on evidence, per your own doctrine
("no fake green, no unevidenced completion, EARNING=$0 until a stranger pays").

### A. Truth / anti-fake-green (run these constantly)
- "For every field on the HELM board, tell me its **source**: observed at request time, cached, or asserted. Anything not observed, mark UNKNOWN and show why."
- "Show me one thing HELM currently reports as GREEN that you have **not** verified in the last hour. Verify it now or downgrade it."
- "Find the most recent PASS in the ledger and re-derive it from raw evidence. If you can't reproduce it, it's not a PASS."
- "Where in the codebase does a check pass by matching the wrong thing (a glob, a fallback, a default)? Prove each check fails when it should."

### B. The money path (the only metric that counts)
- "Trace one real dollar end to end: checkout → Stripe → webhook signature → entitlement flip → access. Which links are **proven** and which are **assumed**? Prove the assumed ones."
- "Is any factory reporting a rung it can't prove? Show the evidence for every rung above DECLARED."
- "What is `verified_founder_minutes_per_shipped_dollar` right now, and what are the raw numbers behind it? If revenue = 0, say EARNING = $0 and stop pretending otherwise."

### C. Factory census (where are they, are they real)
- "List every factory: declared / ran / produced an artifact / has a named+priced product / has a reachable checkout / earned a real dollar. One row each, evidence per column."
- "Which factories are config entries pretending to be factories? A factory that never dispatched a mission is not a factory — name them."
- "For each 'producing' factory: is the artifact a **product a stranger can buy**, or a test file? If nobody can buy it, it's a cost, not an asset."

### D. Security / credentials (today's graveyard)
- "Scan for any credential in git history, shell history, `.env*`, or committed files. For each, prove it's revoked (HTTP 401) or rotate it."
- "For every secret the app needs, prove the **production** value works with a live call — don't trust that it's set, prove it's valid."
- "Which env vars exist in `.env.local` but NOT in the deployed environment (or vice versa)? A working local ≠ a working prod."

### E. Runtime liveness (the '3012 fish' problem)
- "Boot HELM cold and show me it recovering from a killed lease-holder — LIVE, not a structural claim. If you can't do it live, label it STRUCTURAL_PROOF and say so."
- "Every animated node on the wall: is it moving from **observed runtime events** or from a timer? Prove each one is event-driven."

### F. The closing question (run at the end of every session)
- **"What am I about to believe that isn't proven? List every open UNKNOWN, every 'should work', every check that passed on the model's word instead of a machine's output. That list is my real backlog."**

---

## 4. THE ONE HABIT

End every HELM request with: **"…and prove it with a live check whose output you paste. If
you can't, say so — don't substitute a workaround."**

That single sentence would have removed 80% of today's loops. It turns four frontier
models from four storytellers into four instruments — which is what you needed them to be
all along.
