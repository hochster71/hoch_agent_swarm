"""HRF citation verifier — the anti-hallucination gate ($0, keyless public APIs).

Research's deadly failure is fabricated citations. This verifier resolves a citation against REAL
public records and FAILS CLOSED: a citation that cannot be confirmed to exist is BLOCKED, never
assumed real. Sources (all free, no API key):
  - DOI   -> Crossref     (https://api.crossref.org/works/{doi})
  - PMID  -> NCBI eutils  (esummary.fcgi?db=pubmed&id={pmid})

Design contract:
  - Network-only against those endpoints; no LLM, no fabrication.
  - verify_citation() returns VERIFIED / NOT_FOUND / UNCHECKABLE(network) — and callers must treat
    anything other than VERIFIED as BLOCKED (fail-closed). A hallucinated DOI resolves to NOT_FOUND.
  - Runs autonomously on the operator's machine (which has outbound network). In a restricted
    sandbox with no egress it returns UNCHECKABLE — which is still fail-closed (not VERIFIED).
"""
import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List

_UA = {"User-Agent": "HOCH-HRF-citation-verifier/1.0 (mailto:michael.b.hoch@gmail.com)"}
_DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
_PMID_RE = re.compile(r"^\d{4,9}$")
# arXiv: modern (2312.00752 / 2312.00752v3) or legacy (hep-th/9901001). Prefixed forms handled too.
_ARXIV_RE = re.compile(r"^(?:arxiv:)?(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7})$", re.I)


def _get(url: str, timeout: float = 8.0) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def verify_doi(doi: str) -> Dict[str, Any]:
    doi = doi.strip().replace("https://doi.org/", "").replace("doi:", "").strip()
    if not _DOI_RE.match(doi):
        return {"status": "NOT_FOUND", "reason": "malformed DOI", "id": doi}
    try:
        d = _get(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")
        msg = d.get("message", {})
        title = (msg.get("title") or [""])[0]
        return {"status": "VERIFIED", "id": doi, "title": title,
                "year": (msg.get("issued", {}).get("date-parts", [[None]])[0][0])}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"status": "NOT_FOUND", "reason": "DOI not in Crossref", "id": doi}
        return {"status": "UNCHECKABLE", "reason": f"HTTP {e.code}", "id": doi}
    except Exception as e:
        return {"status": "UNCHECKABLE", "reason": str(e), "id": doi}


def verify_pmid(pmid: str) -> Dict[str, Any]:
    pmid = pmid.strip()
    if not _PMID_RE.match(pmid):
        return {"status": "NOT_FOUND", "reason": "malformed PMID", "id": pmid}
    try:
        d = _get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                 f"?db=pubmed&id={pmid}&retmode=json")
        res = d.get("result", {})
        if pmid in res and not res[pmid].get("error"):
            return {"status": "VERIFIED", "id": pmid, "title": res[pmid].get("title", "")}
        return {"status": "NOT_FOUND", "reason": "PMID not in PubMed", "id": pmid}
    except Exception as e:
        return {"status": "UNCHECKABLE", "reason": str(e), "id": pmid}


def verify_citation(cit: str) -> Dict[str, Any]:
    """Verify one citation token (DOI or PMID). Anything not VERIFIED is to be treated as BLOCKED."""
    c = cit.strip()
    if _DOI_RE.match(c.replace("https://doi.org/", "").replace("doi:", "").strip()):
        return {**verify_doi(c), "kind": "doi"}
    if _PMID_RE.match(c):
        return {**verify_pmid(c), "kind": "pmid"}
    return {"status": "NOT_FOUND", "reason": "unrecognized citation format", "id": c}


def gate(citations: List[str]) -> Dict[str, Any]:
    """Fail-closed gate over a list of citations. PASS only if EVERY citation is VERIFIED."""
    results = [verify_citation(c) for c in citations]
    verified = [r for r in results if r["status"] == "VERIFIED"]
    blocked = [r for r in results if r["status"] != "VERIFIED"]
    return {
        "decision": "PASS" if citations and not blocked else "BLOCK",
        "verified": len(verified), "blocked": len(blocked),
        "results": results,
        "note": "fail-closed: NOT_FOUND and UNCHECKABLE both block; only VERIFIED passes",
    }


if __name__ == "__main__":
    import sys
    ids = sys.argv[1:] or ["10.1016/j.ebiom.2019.08.069", "31542391", "10.9999/fake.doi.12345"]
    print(json.dumps(gate(ids), indent=2))
