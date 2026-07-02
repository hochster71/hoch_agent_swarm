from backend.michael_ai.synthesizer import synthesize_current_state

def build_next_prompt() -> dict:
    state = synthesize_current_state()
    
    # Constructing a dynamic ready-to-paste prompt for AG
    prompt_lines = [
        "**[AGENT SWARM OPERATOR DIRECTIVE]**",
        "**TO**: HELM",
        f"Mission Lane: {state['current_lane']}",
        f"Active Priority: {state['active_priority']}",
        "",
        "**RELEASE CONSTRAINTS (MANDATORY)**:",
        "1. Stop all irrelevant/decorative local UI and cockpit polish.",
        "2. Do not bypass the Final Verifier.",
        f"3. Active blocker remaining: {state['release_posture']['active_blocker']}.",
        "4. Do not activate MBPro routing or claim production-ready.",
        "",
        "**ACTIONS & TARGET FILES TO CHANGE**:",
        f"- Next Action: {state['next_best_actions'][0]}",
        "- Target Module: backend/michael_ai/",
        "- Target DB: backend/swarm_ledger.db",
        "",
        "**GATES TO RUN**:",
        "- python -m pytest tests/unit/michael_ai",
        "- bash scripts/final_verifier_gate.sh",
        "- bash scripts/anti_fake_gate.sh",
        "",
        "**REQUIRED EVIDENCE OUTPUT**:",
        "- docs/evidence/michael_ai/YYYYMMDD-HHMM-michael-ai-operational-learning-layer.md",
        "",
        "**COMMIT REQUIREMENTS**:",
        "git add backend/michael_ai tests/unit/michael_ai docs/evidence/michael_ai docs/mission/mission-ledger.md backend/main.py",
        "git commit -m \"feat(michael-ai): add operational learning and prompt synthesis layer\"",
        "",
        "**FINAL REPORT FORMAT**:",
        "Produce the final summary report with fields: Mission lane, Mission outcome, What changed, Endpoints added, Current-state output, Next-prompt output, Training corpus output, Tests, Gate results, Evidence path, Mission ledger update, Commit hash, Remaining blockers, Next lane."
    ]

    raw_prompt = "\n".join(prompt_lines)
    return {
        "status": "success",
        "lane": state["current_lane"],
        "prompt": raw_prompt
    }
