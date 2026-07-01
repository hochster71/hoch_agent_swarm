#!/usr/bin/env python3
# scripts/project_revenue_readiness_audit.py
# Automated Revenue Readiness Audit Scanner for Hoch projects.

import os
import json
import re
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY_PATH = os.path.join(PROJECT_ROOT, "has_live_project_tracker/data/project_inventory.json")
RESULTS_PATH = os.path.join(PROJECT_ROOT, "has_live_project_tracker/data/project_revenue_readiness_results.json")
REPORT_PATH = os.path.join(PROJECT_ROOT, "docs/evidence/business/project-revenue-readiness-audit.md")

IGNORE_DIRS = [".git", "node_modules", ".next", "dist", "build", "__pycache__", ".venv", "venv"]

def run_audit():
    print("==================================================")
    print("RUNNING MULTI-PROJECT REVENUE READINESS AUDIT")
    print("==================================================")
    
    if not os.path.exists(REGISTRY_PATH):
        print(f"[ERROR] Registry file {REGISTRY_PATH} not found!")
        return

    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        projects = json.load(f)

    audit_timestamp = "2026-07-01T21:00:00+00:00Z"
    findings = []
    
    for proj in projects:
        repo_path = proj.get("repo_path", "")
        print(f"Auditing project: {proj['name']} ({repo_path})")
        
        # Base check: Does the repository path exist?
        if not os.path.exists(repo_path):
            print(f"  [WARN] Repository path does not exist: {repo_path}")
            proj["revenue_readiness_score"] = 0
            proj["security_readiness_score"] = 0
            proj["deployment_readiness_score"] = 0
            proj["freshness_status"] = "DEGRADED"
            proj["last_verified_at"] = audit_timestamp
            
            # Keep predefined blockers, or add path blocker
            if "Project repository path does not exist" not in proj["blockers"]:
                proj["blockers"].append("Project repository path does not exist on disk")
            
            findings.append({
                "project": proj["name"],
                "status": "MISSING_REPO",
                "details": f"Repository directory not found at: {repo_path}"
            })
            continue

        # Initialize scanning metrics
        has_build_files = False
        has_deploy_config = False
        has_stripe = False
        has_env_example = False
        has_readme = False
        has_tests = False
        has_cicd = False
        has_auth = False
        has_unmasked_secret = False
        
        # Scan files
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for file in files:
                # Build files
                if file in ["package.json", "Cargo.toml", "pyproject.toml", "requirements.txt", "go.mod", "setup.py"]:
                    has_build_files = True
                
                # Deploy configs
                if file in ["vercel.json", "Dockerfile", "docker-compose.yml", "docker-compose.dev.yml", "fly.toml", "app.yaml"] or file.endswith(".sh"):
                    if "deploy" in file.lower() or "setup" in file.lower() or file in ["vercel.json", "Dockerfile", "docker-compose.yml", "fly.toml", "app.yaml"]:
                        has_deploy_config = True
                
                # README
                if file.lower() in ["readme.md", "launch.md"]:
                    has_readme = True

                # Tests
                if "test" in file.lower() or "spec" in file.lower():
                    has_tests = True
                
                # CI/CD
                if ".github/workflows" in root or ".gitlab-ci.yml" in file:
                    has_cicd = True

                # Read code content for deeper analysis
                if file.endswith((".ts", ".tsx", ".js", ".jsx", ".py", ".sh", ".env", ".example", ".template")):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as code_f:
                            content = code_f.read()
                            if "stripe" in content.lower() or "sk_test" in content or "sk_live" in content:
                                has_stripe = True
                            if "auth" in content.lower() or "login" in content.lower() or "supabase.auth" in content:
                                has_auth = True
                            
                            # Real secret exposure check (non-placeholder sk_live_ or sk_test_)
                            secret_matches = re.findall(r'(sk_live_[a-zA-Z0-9_]+|sk_test_[a-zA-Z0-9_]+)', content)
                            for match in secret_matches:
                                suffix = match[8:]
                                is_placeholder = "_" in suffix or len(suffix) < 24 or "xxx" in suffix or "key" in suffix.lower() or "epic_fury" in suffix
                                if not is_placeholder:
                                    has_unmasked_secret = True
                    except Exception:
                        pass
                        
            # Check for env example files explicitly in folder
            if ".env.example" in files or ".env.template" in files or "env.example" in files:
                has_env_example = True

        # Check tests folder
        if os.path.isdir(os.path.join(repo_path, "tests")) or os.path.isdir(os.path.join(repo_path, "test")):
            has_tests = True

        # Calculate Scores
        # 1. Revenue Readiness
        rev_score = 100
        if proj["stripe_required"] and not has_stripe:
            rev_score -= 40
            if "Stripe integration code is missing or unverified" not in proj["blockers"]:
                proj["blockers"].append("Stripe integration code is missing or unverified")
        if not has_build_files:
            rev_score -= 20
            if "Missing project build manifests/package descriptors" not in proj["blockers"]:
                proj["blockers"].append("Missing project build manifests/package descriptors")
        if not has_env_example:
            rev_score -= 10
        # Reduce by dynamic blockers
        rev_score -= len(proj["blockers"]) * 10
        rev_score = max(0, min(100, rev_score))

        # 2. Security Readiness
        sec_score = 100
        if has_unmasked_secret:
            sec_score -= 50
            if "Active unmasked secret key exposure risk detected" not in proj["blockers"]:
                proj["blockers"].append("Active unmasked secret key exposure risk detected")
        if proj["auth_required"] and not has_auth:
            sec_score -= 20
            if "Authentication flow is not implemented" not in proj["blockers"]:
                proj["blockers"].append("Authentication flow is not implemented")
        if not has_env_example:
            sec_score -= 10
        sec_score = max(0, min(100, sec_score))

        # 3. Deployment Readiness
        dep_score = 100
        if not has_deploy_config:
            dep_score -= 30
            if "Deployment descriptor (vercel.json, Dockerfile) is missing" not in proj["blockers"]:
                proj["blockers"].append("Deployment descriptor (vercel.json, Dockerfile) is missing")
        if not has_readme:
            dep_score -= 10
        if not has_tests:
            dep_score -= 20
            if "No automated test suite discovered" not in proj["blockers"]:
                proj["blockers"].append("No automated test suite discovered")
        if not has_cicd:
            dep_score -= 10
        dep_score = max(0, min(100, dep_score))

        # Assign updated metrics
        proj["revenue_readiness_score"] = rev_score
        proj["security_readiness_score"] = sec_score
        proj["deployment_readiness_score"] = dep_score
        proj["last_verified_at"] = audit_timestamp
        proj["freshness_status"] = "FRESH"
        
        # Clean up duplicates in blockers list
        proj["blockers"] = list(set(proj["blockers"]))
        
        # Determine next critical action based on blockers
        if proj["blockers"]:
            proj["next_critical_action"] = f"Resolve critical blocker: {proj['blockers'][0]}"
        else:
            proj["next_critical_action"] = "Ready for live release / staging stage"

        findings.append({
            "project": proj["name"],
            "status": "ACTIVE",
            "rev_score": rev_score,
            "sec_score": sec_score,
            "dep_score": dep_score,
            "blockers_count": len(proj["blockers"])
        })

    # Save results
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2)
    print(f"Saved audit JSON results to: {RESULTS_PATH}")

    # Generate Markdown Report
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# Multi-Project Revenue Readiness Report (RC45)\n\n")
        f.write(f"**Date**: {datetime.utcnow().strftime('%Y-%m-%d')}  \n")
        f.write("**Auditor**: Antigravity Multi-Project Integrity Scanner  \n")
        f.write(f"**Timestamp**: {audit_timestamp}  \n\n")
        
        f.write("## 1. Executive Summary\n")
        f.write("This report audits the monetization readiness, security posture, and deployment capabilities across all registered launch assets.\n\n")
        
        f.write("## 2. Launch Asset Scores\n")
        f.write("| Project Name | Revenue Readiness | Security Score | Deployment Score | Active Blockers | Next Critical Action |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for proj in projects:
            f.write(f"| {proj['name']} | **{proj['revenue_readiness_score']}%** | {proj['security_readiness_score']}% | {proj['deployment_readiness_score']}% | {len(proj['blockers'])} | {proj['next_critical_action']} |\n")
        f.write("\n")
        
        f.write("## 3. Detailed Findings by Project\n")
        for proj in projects:
            f.write(f"### {proj['name']}\n")
            f.write(f"- **Category**: `{proj['category']}`\n")
            f.write(f"- **Repository Path**: `{proj['repo_path']}`\n")
            f.write(f"- **Deployment Target**: `{proj['deployment_target']}`\n")
            f.write(f"- **Business Model**: `{proj['business_model']}`\n")
            
            if proj["blockers"]:
                f.write("- **Active Blockers**:\n")
                for blk in proj["blockers"]:
                    f.write(f"  - ❌ {blk}\n")
            else:
                f.write("- **Active Blockers**: None (Ready)\n")
                
            f.write(f"- **Next Action**: {proj['next_critical_action']}\n\n")

    print(f"Saved Markdown report to: {REPORT_PATH}")
    print("==================================================")
    print("AUDIT COMPLETE")
    print("==================================================")

if __name__ == "__main__":
    run_audit()
