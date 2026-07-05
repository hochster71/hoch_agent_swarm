"""M1 self-improvement loop — the live brain actually getting better ($0, local model).

Now that a local model can GENERATE (local_model_bridge), the loop can create improved prompt
candidates instead of only selecting existing ones. The Goodhart trap: the mechanical scorer
rewards discipline *keywords*, so generate→mechanical-score→promote would learn to keyword-stuff.

Defense (dual gate): a candidate is promoted ONLY if
  (a) an LLM judge (same local model) picks it over the champion on quality, AND
  (b) the mechanical score does not REGRESS.
So a keyword-stuffed-but-worse candidate (mech likes it, judge rejects it) is NOT promoted, and a
genuinely-better candidate the mech scorer undervalues still needs judge approval. Honest tier:
with a small local model the judge is real but modest/noisy — a frontier judge (Rung 2) is stronger.
"""
import re
from typing import Dict, Any, List, Optional

from backend.brain_convergence.local_model_bridge import (
    detect_local_backend, generate_candidates, _ollama_generate, _lmstudio_generate,
)
from backend.brain_convergence.scorer import score_prompt


def _model_call(backend: Dict[str, str], prompt: str, timeout: float = 60.0) -> str:
    if backend["kind"] == "ollama":
        return _ollama_generate(backend["base"], backend["model"], prompt, timeout)
    return _lmstudio_generate(backend["base"], backend["model"], prompt, timeout)


def llm_judge(backend: Dict[str, str], champion_text: str, candidate_text: str,
              task_class: str, timeout: float = 60.0) -> Dict[str, Any]:
    """Ask the local model which prompt is better. Returns {winner: 'A'|'B'|'TIE', raw}."""
    q = (
        f"You are judging two agent prompts for the task class '{task_class}'. Pick the one that is "
        f"MORE disciplined and effective: clearer scope, stronger evidence/verification requirements, "
        f"anti-fake-green controls, rollback conditions, and structured output. Do NOT reward mere "
        f"keyword stuffing — judge real quality.\n\n"
        f"PROMPT A:\n{champion_text}\n\nPROMPT B:\n{candidate_text}\n\n"
        f"Answer with exactly one token: A or B (or TIE)."
    )
    raw = _model_call(backend, q, timeout)
    up = (raw or "").strip().upper()
    m = re.search(r"\b(A|B|TIE)\b", up)
    winner = m.group(1) if m else "TIE"
    return {"winner": winner, "raw": raw[:200]}


def improve_champion(champion: Dict[str, Any], task_class: str, n: int = 2,
                     rubric_path: Optional[str] = None,
                     backend: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """Try to beat the champion via generate + dual-gate judge. Returns a new champion dict or None.

    champion: {gene_id, prompt, score?}. Returns {prompt, source, judge, mech_score, beats} or None.
    """
    backend = backend or detect_local_backend()
    if not backend:
        return None  # no live brain — mechanical selection only (handled by run_m0)
    champ_prompt = champion.get("prompt", "")
    champ_mech = score_prompt(champ_prompt, rubric_path)["overall"]

    cands = generate_candidates(champ_prompt, task_class, n=n, backend=backend)
    for c in cands:
        cand_text = c["text"]
        cand_mech = score_prompt(cand_text, rubric_path)["overall"]
        if cand_mech < champ_mech:            # gate (b): no mechanical regression
            continue
        judged = llm_judge(backend, champ_prompt, cand_text, task_class)
        if judged["winner"] == "B":            # gate (a): judge prefers candidate
            return {
                "prompt": cand_text,
                "source": c["source"],
                "judge": "LOCAL_LLM_JUDGE",
                "judge_raw": judged["raw"],
                "mech_score": cand_mech,
                "beats_mech": round(cand_mech - champ_mech, 2),
                "state": "GENERATED_AND_JUDGED",  # not VERIFIED_ON_HELDOUT — a live-model win, Rung 1
            }
    return None
