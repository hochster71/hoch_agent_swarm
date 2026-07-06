"""AI Michael (founder orchestrator) — decision-loop invariants. Reads real state but asserts only
invariants that must hold regardless of the exact numbers, so it stays honest and non-brittle."""


def test_brief_structure_and_doctrine():
    from backend.orchestrator.founder_orchestrator import decide, DOCTRINE
    b = decide()
    assert b["persona"].startswith("AI Michael")
    assert b["doctrine"] == DOCTRINE and len(DOCTRINE) == 6
    assert b["portfolio"], "portfolio must cover the registered factories"
    assert "no fake-green — a factory reads only what it earned" in b["doctrine"]


def test_escalations_are_t3_and_autonomous_are_free():
    from backend.orchestrator.founder_orchestrator import decide
    b = decide()
    # everything the orchestrator flags for the operator must be an ESCALATE-tier item
    esc_codes = {n["code"] for n in b["needs_operator"]}
    auto_codes = {a["code"] for a in b["autonomous_now"]}
    for a in b["portfolio"]:
        if a["tier"] == "ESCALATE":
            assert a["code"] in esc_codes
        if a["tier"] == "AUTONOMOUS":
            assert a["code"] in auto_codes
    # the chosen next move, if any, prefers an autonomous $0 action over escalating to the human
    if b["autonomous_now"]:
        assert b["next_move"]["tier"] == "AUTONOMOUS"


def test_money_publish_deploy_never_autonomous():
    # doctrine invariant: no frontier action tagged cost/strategic is ever AUTONOMOUS
    from backend.orchestrator.founder_orchestrator import decide
    b = decide()
    for a in b["portfolio"]:
        if a.get("cost") in ("cost", "strategic", "cost/strategic"):
            assert a["tier"] == "ESCALATE"
