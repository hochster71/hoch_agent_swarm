# HRF M2 + M3 — Live Grounding & Anti-Hallucination Proof

**Date:** 2026-07-06 · **Domain:** research (HRF) · **Cost:** $0 (keyless public APIs)

## What was proven (with real data, not a mock)

### M2 — Literature grounding (live)
The seed agenda *"Senolytic Combination vs Frailty"* (Longevity) was grounded in **real, verifiable
clinical-trial literature** pulled live from PubMed:

- **Hickson et al. 2019**, *EBioMedicine* — "Senolytics decrease senescent cells in humans"
  — [DOI 10.1016/j.ebiom.2019.08.069](https://doi.org/10.1016/j.ebiom.2019.08.069) — PMID 31542391
  — trial NCT02848131 ("Senescence, Frailty, and Mesenchymal Stem Cell Functionality").
- **Justice et al. 2019**, *EBioMedicine* — "Senolytics in idiopathic pulmonary fibrosis:
  first-in-human, open-label pilot" — [DOI 10.1016/j.ebiom.2018.12.052](https://doi.org/10.1016/j.ebiom.2018.12.052)
  — PMID 30616998 — reported significant improvement in physical function (6-min walk, gait speed,
  chair-stands). *(Source: PubMed.)*

These citations are now attached to the agenda gene in `data/prompt_brain/research/gene_pool.json`.

### M3 — Citation-verification gate (live, fail-closed)
`citation_verifier.py` resolved a batch of two real citations + one fabricated DOI against Crossref
and NCBI eutils:

| citation | result |
|---|---|
| `10.1016/j.ebiom.2019.08.069` (DOI) | **VERIFIED** (title returned) |
| `31542391` (PMID) | **VERIFIED** (title returned) |
| `10.9999/fake.doi.12345` (hallucinated DOI) | **NOT_FOUND** |
| **batch decision** | **BLOCK** |

The gate is **fail-closed**: one unverifiable citation blocks the whole batch. A hallucinated DOI
cannot pass. `UNCHECKABLE` (no network) also blocks — it is never treated as VERIFIED.

## Why this matters

Research's deadly failure mode is fabricated citations and invented results. HRF's defining gate
catches exactly that, **at $0**, using the research MCPs' underlying public data (Crossref + NCBI).
This is the anti-hallucination analogue of HMF's originality gate — and unlike HMF's costly
render+judge poles, HRF's grounding+verification is free and working today.

## Honest scope

- Verification covers **DOIs (Crossref)**, **PMIDs (NCBI)**, and **arXiv IDs (arXiv API)** — biomedical
  domains (Longevity, Neurotech, SynBio) AND physics/AI/space domains (Fusion, AI Safety, Space).
  Live-proven: arXiv `1706.03762` ("Attention Is All You Need") VERIFIED, fake `2999.99999` NOT_FOUND,
  mixed DOI+PMID+arXiv batch with one fake → BLOCK. The earlier arXiv gap is now CLOSED.
- This proves **agendas can be grounded and citations verified**. It does NOT execute studies or
  establish that any finding is true — that is M4 (execution) and M5 (novelty/reproducibility judge).

## GO status

M0 VERIFIED · **M2 + M3 demonstrated live** on the Longevity domain · M6 production GO remains NO-GO
until M4/M5 evidence exists. No fake-green.
