#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
src/hoch_agent_swarm/operator_launcher.py — Unified Operator Launch & Health Verification Script for RC7.
"""

import os
import sys
import time
import socket
import subprocess
import urllib.request
import urllib.error
import json

# ANSI Color Codes for premium CLI aesthetics
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_compliance_notice():
    print(f"\n{YELLOW}{'='*80}{RESET}")
    print(f"{YELLOW}{BOLD}ATO-SUPPORTING EVIDENCE PACKAGE: READY FOR REVIEW{RESET}")
    print(f"{YELLOW}The system has ATO-supporting evidence prepared for review.")
    print(f"Actual ATO has not been granted. No authorization claim is being made.")
    print(f"Risks are not fully eliminated.{RESET}")
    print(f"{YELLOW}{'='*80}{RESET}\n")

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def fetch_json(url):
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) OperatorLauncher/0.1"}
        )
        with urllib.request.urlopen(req, timeout=2) as r:
            if r.getcode() == 200:
                return json.loads(r.read().decode('utf-8'))
    except Exception:
        pass
    return None

def verify_route(url, name):
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=2) as r:
            if r.getcode() == 200:
                print(f"  [{GREEN}PASS{RESET}] Route: {name} ({url})")
                return True
            else:
                print(f"  [{RED}FAIL{RESET}] Route: {name} (HTTP {r.getcode()})")
                return False
    except Exception as e:
        print(f"  [{RED}FAIL{RESET}] Route: {name} ({str(e)})")
        return False

def print_checklist(port):
    print(f"\n{CYAN}{BOLD}========================================================================{RESET}")
    print(f"{CYAN}{BOLD}                    OPERATOR REVIEW CHECKLIST / RUNBOOK                {RESET}")
    print(f"{CYAN}{BOLD}========================================================================{RESET}")
    print(" 1. [ ] Start the Operator Launch system (Command: uv run operator_launch).")
    print(f" 2. [ ] Open the Cockpit web browser interface at: http://localhost:{port}")
    print(" 3. [ ] Verify that all 6 subsystems report HEALTHY on the Operator tab.")
    print(" 4. [ ] Run direct IPTV stream diagnostics via the 'Run Connection Diagnostics' button.")
    print(" 5. [ ] Simulate a configuration drift by enabling the ConMon toggle.")
    print(" 6. [ ] Assert that the global compliance alarm banner activates instantly.")
    print(" 7. [ ] Click 'Compliance Bundle' under Prompt QA to download the audit evidence archive.")
    print(" 8. [ ] Review evidence.db and verify all QA lineage runs are recorded correctly.")
    print(f"{CYAN}{'='*72}{RESET}\n")

def main():
    print_compliance_notice()
    port = int(os.environ.get("SWARM_UI_PORT", "8085"))
    
    server_already_running = False
    proc = None
    
    if is_port_in_use(port):
        # Check if it's our dashboard
        health_data = fetch_json(f"http://127.0.0.1:{port}/api/v1/operator/health")
        if health_data:
            print(f"[{GREEN}INFO{RESET}] Dashboard server is already running on port {port}.")
            server_already_running = True
        else:
            print(f"[{RED}ERROR{RESET}] Port {port} is in use by another conflicting process.")
            print("Please terminate the conflicting process and try again.")
            sys.exit(1)
    else:
        # Start server as a background subprocess
        env = os.environ.copy()
        env["SWARM_UI_PORT"] = str(port)
        proc = subprocess.Popen(
            [sys.executable, "-u", "-m", "hoch_agent_swarm.ui_server"],
            env=env
        )
        
        # Wait for spin-up
        success = False
        for i in range(30):
            time.sleep(0.5)
            if is_port_in_use(port):
                health_data = fetch_json(f"http://127.0.0.1:{port}/api/v1/operator/health")
                if health_data:
                    success = True
                    break
        
        if not success:
            print(f"[{RED}ERROR{RESET}] Dashboard server failed to start or respond on port {port} in time.")
            if proc:
                proc.terminate()
            sys.exit(1)
            
        print(f"[{GREEN}SUCCESS{RESET}] Dashboard server running successfully.")
        
    print(f"\n{BOLD}Running key route verification suite...{RESET}")
    base_url = f"http://127.0.0.1:{port}"
    r1 = verify_route(f"{base_url}/", "Home Page")
    r2 = verify_route(f"{base_url}/api/v1/promptbrain/prompts", "Prompt Registry API")
    r3 = verify_route(f"{base_url}/api/v1/brain/query?q=compliance", "Evidence Query API")
    r4 = verify_route(f"{base_url}/api/v1/promptqa/lineage", "Prompt QA Lineage API")
    r5 = verify_route(f"{base_url}/api/v1/operator/health", "Operator Health Status API")
    r6 = verify_route(f"{base_url}/api/tv/health", "HOCH TV IPTV Health API")
    
    # Fetch final health status
    health_data = fetch_json(f"{base_url}/api/v1/operator/health")
    if not health_data:
        print(f"\n[{RED}ERROR{RESET}] Failed to extract runtime health data.")
        if proc:
            proc.terminate()
        sys.exit(1)
        
    print(f"\n{BOLD}Subsystem Health Audit Results:{RESET}")
    components = health_data.get("components", {})
    for comp_name, comp_info in components.items():
        status = comp_info.get("status", "UNKNOWN")
        status_color = GREEN if status == "HEALTHY" else RED
        details = ""
        if comp_name == "PromptBrain":
            details = f"({comp_info.get('prompts_count', 0)} prompts registered)"
        elif comp_name == "PromptQA":
            details = f"(avg quality score: {comp_info.get('average_score', 0)}%)"
        elif comp_name == "EvidenceBrain":
            details = f"({comp_info.get('nodes_count', 0)} nodes, {comp_info.get('edges_count', 0)} relationships)"
        elif comp_name == "HOCH TV":
            details = f"({comp_info.get('channels_count', 0)} cached channels)"
            
        print(f"  • {comp_name:<15}: {status_color}{status}{RESET} {details}")
        
    print(f"\n{GREEN}{BOLD}URL to access the Dashboard: http://localhost:{port}{RESET}")
    
    print_checklist(port)
    
    if server_already_running:
        print(f"[{GREEN}INFO{RESET}] Done. Server remains active on port {port}.")
        sys.exit(0)
    else:
        print(f"{YELLOW}Dashboard is running in the background. Press Ctrl+C to terminate server.{RESET}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n[{CYAN}INFO{RESET}] Gracefully shutting down dashboard server...")
            if proc:
                proc.terminate()
                proc.wait()
            print(f"[{GREEN}SUCCESS{RESET}] Server stopped. Clean exit.")
            sys.exit(0)

if __name__ == "__main__":
    main()
