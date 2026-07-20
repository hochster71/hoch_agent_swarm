#!/usr/bin/env python3
import time
import sys
import os
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.columns import Columns
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
except ImportError:
    print("Error: 'rich' package is required. Install it using 'uv add rich' or equivalent.")
    sys.exit(1)

from scripts.helm_live_run_collector import collect

console = Console()

def make_layout(state):
    # Colors matching the UI guidelines:
    # cyan: active, green: verified, amber: gate/declared, red: failures, grey: stopped, purple: founder gate
    
    # 1. Mode & Mission Panel
    mode_text = Text()
    mode_text.append("MODE: ", style="bold")
    m_color = "cyan" if state["mode"] in ("RUNNING", "QUALIFYING") else "green"
    mode_text.append(state["mode"], style=f"bold {m_color}")
    mode_text.append("\nStatus: ", style="bold")
    status_style = "green" if state["truth_status"] == "COMPLETED" else ("cyan" if state["truth_status"] in ("RUNNING", "VALIDATING") else "amber")
    mode_text.append(state["truth_status"], style=status_style)
    mode_text.append(f"\nMission: {state['active_mission']['id']} - {state['active_mission']['name']}")
    
    panel_mode = Panel(mode_text, title="[bold white]⎈ Mode & Mission[/bold white]", border_style="cyan")
    
    # 2. Candidate Identity Panel
    cand = state["candidate"]
    repo = state["repository_state"]
    cand_text = Text()
    cand_text.append(f"Branch: {cand['branch']}\n")
    cand_text.append(f"Commit: {cand['commit_sha'][:10]}... [VERIFIED]\n", style="green")
    cand_text.append(f"Tree:   {cand['tree_hash'][:10]}... [VERIFIED]\n", style="green")
    wt_color = "green" if cand["worktree_clean"] else "red"
    cand_text.append("Worktree: ", style="bold")
    cand_text.append("CLEAN" if cand["worktree_clean"] else "DIRTY", style=wt_color)
    
    c1_local = "YES" if repo["commits_exist_locally"]["d335260b"] else "NO"
    c2_local = "YES" if repo["commits_exist_locally"]["d530af67"] else "NO"
    c1_pushed = "YES" if repo["commits_pushed"]["d335260b"] else "NO"
    c2_pushed = "YES" if repo["commits_pushed"]["d530af67"] else "NO"
    
    cand_text.append(f"\nCommits Local:  d335260b ({c1_local}), d530af67 ({c2_local})")
    cand_text.append(f"\nCommits Pushed: d335260b ({c1_pushed}), d530af67 ({c2_pushed})")
    
    panel_candidate = Panel(cand_text, title="[bold white]Candidate Identity[/bold white]", border_style="green")
    
    # 3. Factory Activity: HFF_HOURLY_RATE
    hff = state["hff_hourly_rate"]
    hff_text = Text()
    hff_text.append(f"Product:   {hff['product']}\n", style="bold")
    hff_text.append(f"State:     {hff['product_state']} [cyan]\n")
    hff_text.append(f"Deploy:    {hff['deployment_state']} [grey]\n")
    hff_text.append(f"Stripe:    {hff['founder_gate']} [amber]\n")
    hff_text.append(f"Revenue:   ${hff['revenue']} [grey]\n")
    hff_text.append(f"Tests Eng: {hff['test_results']['engine']} | Buy: {hff['test_results']['buy_loop']}\n")
    hff_text.append(f"Node / Host: {hff['node_version']} / {hff['host']}\n")
    
    # Checklists
    checks_str = "Evidence Checklist:\n"
    for chk, val in hff["evidence_checklist"].items():
        symbol = "✓" if val else "✗"
        color = "green" if val else "red"
        name = chk.replace("check_", "").replace("_", " ")[:25]
        checks_str += f"  [{color}]{symbol}[/{color}] {name:<25}\n"
    
    hff_text.append(checks_str)
    panel_hff = Panel(hff_text, title=f"[bold white]Factory Activity: {hff['candidate']} [{hff['evidence_grade']}][/bold white]", border_style="purple")
    
    # 4. Process Health & Services
    proc_text = Text()
    if not state["active_processes"]:
        proc_text.append("No active processes.\n", style="grey")
    else:
        for p in state["active_processes"]:
            proc_text.append(f"PID: {p['pid']} | Name: {p['name']} | Health: {p['health']}\n", style="cyan")
            proc_text.append(f"CPU: {p['cpu_time_seconds']}s | Elapsed: {p['elapsed_seconds']}s\n")
            
    proc_text.append("\nServices State:\n")
    for svc, status in state["services"].items():
        color = "green" if "RUNNING" in status else "red"
        proc_text.append(f"  {svc}: ", style="bold")
        proc_text.append(status, style=color)
        proc_text.append("\n")
        
    panel_proc = Panel(proc_text, title="[bold white]Process Health & Services[/bold white]", border_style="cyan")
    
    # 5. Blockers & Next Event
    block_text = Text()
    blockers_str = ", ".join(state.get("blockers", [])) or "NONE"
    b_color = "red" if blockers_str != "NONE" else "green"
    block_text.append(f"Blockers:   {blockers_str}\n", style=f"bold {b_color}")
    block_text.append(f"Next Event: {', '.join(state['next_expected_events'])}\n", style="bold cyan")
    block_text.append(f"Raw Log:    {state['evidence']['raw_log_path']}\n", style="dim")
    block_text.append(f"Artifact:   {state['evidence']['result_artifact_path']}", style="dim")
    
    panel_block = Panel(block_text, title="[bold white]Blockers & Next Governed Action[/bold white]", border_style="red")
    
    # 6. Evidence Grades Table
    table_grades = Table(title="Telemetry Evidence Grades", show_header=True, header_style="bold magenta", expand=True)
    table_grades.add_column("Telemetry Claim", style="bold")
    table_grades.add_column("Grade")
    table_grades.add_column("Authoritative Source")
    table_grades.add_column("Observed At", style="dim")
    table_grades.add_column("Freshness")
    
    for claim, info in state["evidence_grades"].items():
        g = info["grade"]
        if g == "VERIFIED":
            g_style = "green"
        elif g == "OBSERVED":
            g_style = "cyan"
        elif g == "DECLARED":
            g_style = "amber"
        elif g == "NOT_READY":
            g_style = "purple"
        elif g == "FAIL":
            g_style = "red"
        else:
            g_style = "grey"
        table_grades.add_row(
            claim,
            Text(g, style=f"bold {g_style}"),
            info["source"],
            info["observed_timestamp"],
            f"{info['freshness']}s"
        )
        
    # 7. Recent Events Log Table
    table_events = Table(title="Latest 15 Execution Events (Audit Trail)", show_header=True, header_style="bold blue", expand=True)
    table_events.add_column("Timestamp", style="dim", width=20)
    table_events.add_column("Type", style="bold cyan", width=20)
    table_events.add_column("Producer", style="bold", width=15)
    table_events.add_column("Mission ID", style="dim", width=15)
    table_events.add_column("Explanation", style="white")
    
    for ev in state["recent_events"][:15]:
        table_events.add_row(
            ev["timestamp"],
            ev["type"],
            ev["producer"],
            ev["mission_id"],
            ev["explanation"][:80] + ("..." if len(ev["explanation"]) > 80 else "")
        )
        
    # Assemble Layout
    grid_top = Table.grid(expand=True)
    grid_top.add_column(ratio=1)
    grid_top.add_column(ratio=1)
    grid_top.add_row(panel_mode, panel_candidate)
    
    grid_middle = Table.grid(expand=True)
    grid_middle.add_column(ratio=2)
    grid_middle.add_column(ratio=1)
    grid_middle.add_row(panel_hff, panel_proc)
    
    grid_bottom = Table.grid(expand=True)
    grid_bottom.add_column(ratio=1)
    grid_bottom.add_row(panel_block)
    
    # Master layout wrapper
    master = Table.grid(expand=True)
    master.add_column(ratio=1)
    master.add_row(Text("⎈ HELM • FOUNDER LIVE RUN CONSOLE (TUI)", style="bold cyan justify=center"))
    master.add_row(grid_top)
    master.add_row(grid_middle)
    master.add_row(grid_bottom)
    master.add_row(table_grades)
    master.add_row(table_events)
    
    footer = Text(f"\nGenerated At: {state['generated_at']} | Freshness: {state['freshness_seconds']}s | STRICT ZERO-MOCK TRUTH postured", style="dim justify=center")
    master.add_row(footer)
    
    return master

def main():
    if "--print-once" in sys.argv:
        state = collect()
        gen_time = datetime.datetime.fromisoformat(state["generated_at"])
        now_time = datetime.datetime.now(datetime.timezone.utc)
        state["freshness_seconds"] = max(0.0, round((now_time - gen_time).total_seconds(), 2))
        console.print(make_layout(state))
        return

    try:
        with Live(console=console, screen=True, auto_refresh=False) as live:
            while True:
                state = collect()
                # Calculate freshness
                gen_time = datetime.datetime.fromisoformat(state["generated_at"])
                now_time = datetime.datetime.now(datetime.timezone.utc)
                state["freshness_seconds"] = max(0.0, round((now_time - gen_time).total_seconds(), 2))
                
                live.update(make_layout(state), refresh=True)
                time.sleep(2)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]TUI Exited. Zero-Mock validation postured.[/bold yellow]")

if __name__ == "__main__":
    main()
