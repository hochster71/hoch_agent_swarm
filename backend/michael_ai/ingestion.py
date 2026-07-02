import re
import uuid
from datetime import datetime, timezone
from backend.michael_ai.store import get_db_conn
from backend.runtime_truth.state_store import now_iso

def parse_heuristics(text: str) -> dict:
    # Heuristic lane detection
    lane = "General"
    low_text = text.lower()
    if "michael ai" in low_text or "twin" in low_text or "learning" in low_text:
        lane = "Michael AI Model / Operator Twin / Continuous Learning Layer"
    elif "vps" in low_text or "relay" in low_text or "hoch-200" in low_text or "3012" in low_text:
        lane = "HOCH-200 Relay & Runtime Truth"
    elif "ui" in low_text or "cockpit" in low_text or "display" in low_text:
        lane = "UI/Cockpit Operations"
    elif "qa" in low_text or "test" in low_text or "spec" in low_text:
        lane = "QA/Verification"

    # Urgency signal
    urgency = "medium"
    if any(w in low_text for w in ["warp speed", "immediately", "drowning", "critical", "urgent", "stop"]):
        urgency = "high"
    elif any(w in low_text for w in ["later", "maybe", "when possible", "noncritical", "polish"]):
        urgency = "low"

    # Sentiment/Frustration
    sentiment = "neutral"
    if any(w in low_text for w in ["drowning", "cannot", "overloaded", "frustrated", "stop", "fail"]):
        sentiment = "frustrated"
    elif any(w in low_text for w in ["good", "great", "success", "resolved", "pass"]):
        sentiment = "positive"

    # Files mentioned
    files = re.findall(r'[a-zA-Z0-9_\-\./]+\.[a-zA-Z0-9]{2,4}', text)
    # Filter out common false positives like IP addresses or URLs
    files = [f for f in files if not re.match(r'^\d+\.', f) and "http" not in f]

    # Commands mentioned (starts with git, python, bash, npx, curl, cd)
    commands = re.findall(r'(?:bash|python[3]?|git|curl|npx|jq|cd)\s+[a-zA-Z0-9_\-\./\s"\'&\|=<>]+', text)

    # Evidence paths mentioned
    evidence = [f for f in files if "evidence/" in f]

    # Commits mentioned
    commits = re.findall(r'\b[0-9a-fA-F]{7,40}\b', text)

    # Goals extraction
    goal = "Synthesized operator task"
    goal_match = re.search(r'(?:goal|priority|need to|build|run|archive|lock)\s+([^.\n]+)', text, re.IGNORECASE)
    if goal_match:
        goal = goal_match.group(1).strip()
    else:
        # Fallback to the first sentence or first 80 chars
        first_part = text.split(".")[0].split("\n")[0].strip()
        if len(first_part) > 80:
            goal = first_part[:77] + "..."
        else:
            goal = first_part or "Synthesized operator task"
    
    # Decisions (accepted/rejected)
    accepted_states = []
    rejected_states = []
    if "accepted" in low_text or "conditional_go" in low_text or "pass" in low_text:
        accepted_states = ["CONDITIONAL_GO", "PASS"]
    if "rejected" in low_text or "blocked" in low_text or "fail" in low_text:
        rejected_states = ["BLOCKED", "FAIL"]

    # Frustration and avoided actions
    avoid = []
    if "do not" in low_text:
        matches = re.findall(r'do not\s+([^.\n]+)', text, re.IGNORECASE)
        avoid.extend([m.strip() for m in matches])
    if "avoid repeating" in low_text:
        matches = re.findall(r'avoid repeating\s+([^.\n]+)', text, re.IGNORECASE)
        avoid.extend([m.strip() for m in matches])

    return {
        "lane": lane,
        "urgency": urgency,
        "sentiment": sentiment,
        "goal": goal,
        "files": list(set(files)),
        "commands": list(set(commands)),
        "evidence": list(set(evidence)),
        "commits": list(set(commits)),
        "accepted_states": accepted_states,
        "rejected_states": rejected_states,
        "avoid": avoid
    }

def ingest_michael_prompt(source: str, raw_text: str) -> dict:
    parsed = parse_heuristics(raw_text)
    prompt_id = str(uuid.uuid4())
    ts = now_iso()
    
    conn = get_db_conn()
    try:
        # 1. Store prompt
        conn.execute("""
            INSERT INTO michael_prompts 
            (id, timestamp, source, raw_text, normalized_text, detected_lane, urgency, sentiment, goal, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prompt_id, ts, source, raw_text, raw_text.strip(),
            parsed["lane"], parsed["urgency"], parsed["sentiment"], parsed["goal"], ts
        ))

        # 2. Store decisions if detected
        decision_desc = ""
        if "lock" in raw_text.lower() or "commit" in raw_text.lower():
            decision_desc = f"Operator locked/committed state via prompt: {parsed['goal']}"
            conn.execute("""
                INSERT INTO michael_decisions
                (id, timestamp, decision, rationale, accepted_state, rejected_state, related_prompt_id, evidence_ref, commit_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), ts, decision_desc, raw_text,
                ",".join(parsed["accepted_states"]), ",".join(parsed["rejected_states"]),
                prompt_id, ",".join(parsed["evidence"]), ",".join(parsed["commits"])
            ))

        # 3. Update active workflow state
        conn.execute("""
            INSERT OR REPLACE INTO michael_workflows
            (id, lane, status, current_goal, blockers, next_action, evidence_refs, commit_refs, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "active_workflow", parsed["lane"], "IN_PROGRESS", parsed["goal"],
            "NO_ACTIVE_RELEASE_GO" if "no_active_release_go" in raw_text.lower() else "",
            parsed["goal"], ",".join(parsed["evidence"]), ",".join(parsed["commits"]), ts
        ))

        # 4. Extract lessons
        if parsed["avoid"]:
            for av in parsed["avoid"]:
                conn.execute("""
                    INSERT INTO michael_lessons
                    (id, lesson_type, lesson, trigger_text, do_next_time, avoid_next_time, confidence, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()), "avoid", av, raw_text[:200], "", av, 0.8, ts
                ))

        # 5. Build training example
        conn.execute("""
            INSERT INTO michael_training_examples
            (id, input_text, desired_output, lane, quality_score, source_refs, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()), raw_text, f"Execute changes for lane: {parsed['lane']}, target goal: {parsed['goal']}",
            parsed["lane"], 1.0, prompt_id, ts
        ))

        conn.commit()
    finally:
        conn.close()

    return {
        "prompt_id": prompt_id,
        "lane": parsed["lane"],
        "goal": parsed["goal"],
        "urgency": parsed["urgency"],
        "sentiment": parsed["sentiment"],
        "files": parsed["files"],
        "commands": parsed["commands"],
        "evidence": parsed["evidence"],
        "commits": parsed["commits"]
    }

def ingest_ag_run(agent_role: str, task_description: str, status: str, result: str = None, raw_prompt: str = None) -> dict:
    run_id = str(uuid.uuid4())
    ts = now_iso()
    parsed_prompt = parse_heuristics(raw_prompt or task_description)
    parsed_result = parse_heuristics(result or "")

    conn = get_db_conn()
    try:
        # 1. Update run history in agent_runs if exists or log as training example
        conn.execute("""
            INSERT INTO michael_training_examples
            (id, input_text, desired_output, lane, quality_score, source_refs, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, raw_prompt or task_description, result or "",
            parsed_prompt["lane"], 0.9 if status == "SUCCESS" else 0.4, f"agent_run:{agent_role}", ts
        ))

        # 2. Store decisions if run resulted in a git commit
        if parsed_result["commits"]:
            conn.execute("""
                INSERT INTO michael_decisions
                (id, timestamp, decision, rationale, accepted_state, rejected_state, related_prompt_id, evidence_ref, commit_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), ts, f"AG Agent Run committed changes", task_description,
                "PASS", "FAIL", None, ",".join(parsed_result["evidence"]), ",".join(parsed_result["commits"])
            ))

        conn.commit()
    finally:
        conn.close()

    return {
        "run_id": run_id,
        "lane": parsed_prompt["lane"],
        "status": status,
        "commits": parsed_result["commits"],
        "evidence": parsed_result["evidence"]
    }
