from backend.michael_ai.store import get_db_conn

def export_training_corpus() -> dict:
    conn = get_db_conn()
    examples = []
    try:
        rows = conn.execute("SELECT * FROM michael_training_examples").fetchall()
        for r in rows:
            # Map database records to structured training corpus format
            examples.append({
                "request": r["input_text"],
                "desired_output_pattern": r["desired_output"],
                "avoid_output_pattern": "Chasing local UI polish or bypassing secure gates without explicit verification.",
                "operating_doctrine": "Enforce strict local baseline protection, keep git working tree clean, run anti-fake checks, do not skip Final Verifier.",
                "lane": r["lane"] or "General",
                "evidence_requirement": "Generate YYYYMMDD-HHMM evidence markdown documentation and run visual compliance audits."
            })
    finally:
        conn.close()

    # Provide a default example if database is empty
    if not examples:
        examples.append({
            "request": "I need warp speed on the Michael AI Model because I am drowning and cannot push this and code at the same time.",
            "desired_output_pattern": "Acknowledge the Michael AI Model / Operator Twin lane, build persistent database schemas, populate seed truths, write E2E unit tests, and provide a synthesized prompt builder endpoint.",
            "avoid_output_pattern": "Continuing to polish local UI components, changing flexbox styling, or running release candidates without confirming HOCH-200 relay posture.",
            "operating_doctrine": "Absolute priority is security and cognitive load reduction for the operator. Only work on designated lanes.",
            "lane": "Michael AI Model / Operator Twin / Continuous Learning Layer",
            "evidence_requirement": "docs/evidence/michael_ai/YYYYMMDD-HHMM-michael-ai-operational-learning-layer.md"
        })

    return {
        "status": "success",
        "count": len(examples),
        "corpus": examples
    }
