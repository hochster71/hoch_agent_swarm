"""Autonomous Swarm Dispatcher.

Discovers new compliance and audit task domains from documentation files (docs/prompt_brain/**/*.md)
and runtime execution logs (data/prompt_brain/runtime_executions.jsonl) that are not yet mapped
in the champion registry or gene pool. Autonomously generates high-discipline seed prompts for them
using the local model, injecting them into the gene pool for convergence.
"""
import sys
import json
import hashlib
import re
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.brain_convergence.local_model_bridge import (
    detect_local_backend, _ollama_generate, _lmstudio_generate,
)
from backend.brain_convergence.champion import load_registry


def scan_docs_for_tasks(root_dir: Path) -> List[Dict[str, str]]:
    docs_dir = root_dir / "docs" / "prompt_brain"
    found = []
    if not docs_dir.exists():
        return found
    for p in docs_dir.glob("**/*.md"):
        try:
            content = p.read_text(encoding="utf-8")
            for line in content.splitlines():
                # Extract bolded task names like **SSP Control Narrative Review**
                matches = re.findall(r"\*\*(.*?)\*\*", line)
                for item in matches:
                    item_clean = item.strip()
                    if 5 < len(item_clean) < 50:
                        # Keywords signifying compliance SOP tasks
                        if any(x in item_clean.lower() for x in ["review", "triage", "audit", "schedule", "control", "commander", "governance", "check"]):
                            found.append({"task_class": item_clean, "source": f"docs/{p.relative_to(docs_dir)}"})
        except Exception:
            pass
    return found


def scan_logs_for_tasks(logs_path: Path) -> List[Dict[str, str]]:
    found = []
    if not logs_path.exists():
        return found
    try:
        with open(logs_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                tc = d.get("task") or d.get("domain") or d.get("prompt_family")
                if tc and 5 < len(tc) < 50:
                    found.append({"task_class": tc, "source": "runtime_executions.jsonl"})
    except Exception:
        pass
    return found


def seed_prompt_for_task(backend: Dict[str, str], task_class: str) -> str:
    instruction = (
        f"You are a master prompt engineering agent seeding a new task class: '{task_class}'.\n"
        f"Write a highly disciplined system prompt for a cybersecurity/compliance agent performing this task.\n"
        f"The prompt must follow this structure:\n\n"
        f"ROLE: [Define agent role]\n"
        f"SCOPE: [Define exact task boundary]\n"
        f"EVIDENCE/VERIFICATION REQUIREMENTS: [Define concrete evidence logs, config files, or outputs to inspect]\n"
        f"ANTI-FAKE-GREEN CHECKS: [Steps to detect and quarantine simulated or invalid indicators]\n"
        f"ROLLBACK CONDITIONS: [Specific stop/abort instructions if conditions are unsafe]\n"
        f"OUTPUT: [Exactly what report or ledger output must be generated]\n\n"
        f"Return ONLY the seeded prompt text (no markdown wrapping code blocks, no comments)."
    )
    if backend["kind"] == "ollama":
        text = _ollama_generate(backend["base"], backend["model"], instruction, timeout=60.0)
    else:
        text = _lmstudio_generate(backend["base"], backend["model"], instruction, timeout=60.0)
    return text


def run(root_dir: Optional[Path] = None):
    ROOT = root_dir or Path(__file__).resolve().parent.parent.parent
    DATA = ROOT / "data" / "prompt_brain"
    GENE_POOL_PATH = DATA / "gene_pool_m0.json"
    CHAMP_REGISTRY_PATH = DATA / "champion_registry.json"
    LOGS_PATH = DATA / "runtime_executions.jsonl"
    DISCOVERED_PATH = DATA / "discovered_tasks.json"

    backend = detect_local_backend()
    if not backend:
        print("swarm_dispatcher: no live local model — cannot seed prompts.")
        return

    # 1. Load existing task classes
    existing_classes = set()
    if CHAMP_REGISTRY_PATH.exists():
        try:
            reg = load_registry(str(CHAMP_REGISTRY_PATH))
            existing_classes.update(reg.get("champions", {}).keys())
        except Exception:
            pass

    if GENE_POOL_PATH.exists():
        try:
            pool = json.loads(GENE_POOL_PATH.read_text(encoding="utf-8"))
            existing_classes.update(pool.get("class_sizes", {}).keys())
        except Exception:
            pass

    # 2. Discover unmapped tasks
    cands = scan_docs_for_tasks(ROOT) + scan_logs_for_tasks(LOGS_PATH)
    unmapped = {}
    for c in cands:
        tc = c["task_class"]
        # Normalize and filter out duplicates / existing classes
        if tc not in existing_classes and tc not in unmapped:
            unmapped[tc] = c["source"]

    if not unmapped:
        print("swarm_dispatcher: no new unmapped tasks discovered.")
        return

    print(f"swarm_dispatcher: discovered {len(unmapped)} new task(s): {list(unmapped.keys())}")

    # 3. Seed new prompts and inject into gene pool
    if GENE_POOL_PATH.exists():
        pool = json.loads(GENE_POOL_PATH.read_text(encoding="utf-8"))
        genes = pool.setdefault("genes", {})
        sizes = pool.setdefault("class_sizes", {})

        ts = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        seeded_count = 0

        for tc, src in unmapped.items():
            print(f"  seeding prompt for '{tc}' (discovered from {src})...")
            try:
                prompt_text = seed_prompt_for_task(backend, tc)
                if not prompt_text:
                    continue
                
                h = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
                gid = f"gen-gapfill-{h[:10]}-{ts[:19].replace(':','').replace('-','')}"
                
                genes[gid] = {
                    "gene_id": gid,
                    "task_class": tc,
                    "industry": "All Industries",
                    "title": f"{tc} Commander",
                    "mission": f"Autonomously handle {tc} tasks.",
                    "outputs": "Structured evidence ledger and reports.",
                    "prompt": prompt_text,
                    "content_hash": h
                }
                sizes[tc] = 1
                seeded_count += 1
            except Exception as e:
                print(f"  failed to seed prompt for {tc}: {e}")

        if seeded_count > 0:
            pool["count"] = len(genes)
            pool["task_classes"] = len(sizes)
            GENE_POOL_PATH.write_text(json.dumps(pool, indent=2), encoding="utf-8")
            
            # Save discovered list to file for UI
            discovered = []
            if DISCOVERED_PATH.exists():
                try:
                    discovered = json.loads(DISCOVERED_PATH.read_text(encoding="utf-8"))
                except Exception:
                    pass
            for tc, src in unmapped.items():
                discovered.append({"task_class": tc, "discovered_at": ts, "source": src})
            DISCOVERED_PATH.write_text(json.dumps(discovered, indent=2), encoding="utf-8")
            
            print(f"swarm_dispatcher: successfully seeded {seeded_count} new genes into {GENE_POOL_PATH.name}")


if __name__ == "__main__":
    run()
