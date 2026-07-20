#!/usr/bin/env python3
"""actor_f3_custody.py — ACTOR-F3 key custody and impersonation inventory.

Performs a read-only audit of credential and key custody locations to determine
isolation boundaries and impersonation vulnerability.
Does NOT read or output any secret contents.
"""
import os
import sys
import subprocess
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "coordination" / "governance" / "actor_f3_custody_report.json"

def _run(*a):
    try:
        r = subprocess.run(list(a), capture_output=True, text=True, timeout=5)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return -1, "", str(e)

def main():
    report = {
        "artifact": "ACTOR-F3-CUSTODY",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "context_label": os.environ.get("HELM_SESSION_ID", "gemini-antigravity"),
        "key_custody_inventory": {},
        "impersonation_vulnerabilities": [],
        "mitigation_status": {}
    }

    # 1. SSH key inventory (presence & permissions)
    ssh_dir = Path.home() / ".ssh"
    ssh_keys = []
    if ssh_dir.exists():
        for p in ssh_dir.glob("id_*"):
            if not p.name.endswith(".pub"):
                try:
                    stat = p.stat()
                    perms = oct(stat.st_mode & 0o777)
                    ssh_keys.append({
                        "name": p.name,
                        "permissions": perms,
                        "secure_permissions": perms in ("0o600", "0o400"),
                    })
                except Exception:
                    pass
    
    # Check ssh-agent status
    agent_code, agent_out, _ = _run("ssh-add", "-l")
    agent_keys_present = False
    if agent_code == 0:
        agent_keys_present = True
        agent_status = f"ACTIVE ({len(agent_out.splitlines())} keys loaded)"
    elif agent_code == 1:
        agent_status = "ACTIVE (no keys loaded)"
    else:
        agent_status = "INACTIVE / UNREACHABLE"

    report["key_custody_inventory"]["ssh"] = {
        "dot_ssh_exists": ssh_dir.exists(),
        "private_keys_found": ssh_keys,
        "ssh_agent_status": agent_status,
    }

    # 2. GPG / PGP key inventory
    gpg_code, gpg_out, _ = _run("gpg", "--list-secret-keys", "--keyid-format", "LONG")
    gpg_keys = []
    if gpg_code == 0:
        for line in gpg_out.splitlines():
            if line.startswith("sec") or line.startswith("ssb"):
                gpg_keys.append(line)
    
    report["key_custody_inventory"]["gpg"] = {
        "gpg_available": gpg_code == 0,
        "secret_keys_found": len(gpg_keys) > 0,
        "keys": gpg_keys
    }

    # 3. macOS Keychain accessibility (since we are on Darwin)
    is_mac = sys.platform == "darwin"
    keychain_info = "NOT_DARWIN"
    if is_mac:
        kc_code, kc_out, _ = _run("security", "default-keychain")
        if kc_code == 0:
            keychain_info = f"RESOLVED: {kc_out}"
        else:
            keychain_info = "UNREACHABLE / LOCKED"
            
    report["key_custody_inventory"]["macos_keychain"] = {
        "is_macos": is_mac,
        "status": keychain_info
    }

    # 4. Git Credential Helper config
    helper_code, helper_out, _ = _run("git", "config", "credential.helper")
    report["key_custody_inventory"]["git_credential_helper"] = {
        "configured": helper_code == 0,
        "helper": helper_out if helper_code == 0 else "UNSET"
    }

    # 5. Git signing config
    sign_key_code, sign_key_out, _ = _run("git", "config", "user.signingkey")
    gpg_sign_code, gpg_sign_out, _ = _run("git", "config", "commit.gpgsign")
    report["key_custody_inventory"]["git_signing_config"] = {
        "user_signingkey": sign_key_out if sign_key_code == 0 else "UNSET",
        "commit_gpgsign": gpg_sign_out if gpg_sign_code == 0 else "UNSET",
    }

    # 6. Analyze Impersonation Vulnerability
    vulns = []
    if sign_key_code != 0 or sign_key_out == "":
        vulns.append("COMMITS_UNSIGNED: No commit signing configured. Any agent/process in the shared account can commit as 'Michael Hoch'.")
    
    if len(ssh_keys) > 0:
        insecure_ssh = [k["name"] for k in ssh_keys if not k["secure_permissions"]]
        if insecure_ssh:
            vulns.append(f"INSECURE_SSH_PERMISSIONS: Private keys have overly broad permissions: {insecure_ssh}")
            
    if agent_keys_present:
        vulns.append("SSH_AGENT_SOCKET_EXPOSED: Active keys are held in ssh-agent. Any process with access to SSH_AUTH_SOCK environment variable can sign git/network operations using the human's identity.")

    env_keys = []
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, _ = line.split("=", 1)
                if any(x in k for x in ["KEY", "SECRET", "PASSWORD", "TOKEN"]):
                    env_keys.append(k)
    
    if env_keys:
        vulns.append(f"PLAINTEXT_KEYS_IN_ENV: Plaintext secrets stored in .env: {env_keys}. Any process in the shared account can read these.")

    report["impersonation_vulnerabilities"] = vulns

    # 7. Write the custody report
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"ACTOR-F3 custody report written to {OUT.relative_to(ROOT)}")
    for v in vulns:
        print(f"  ⚠ IMPERSONATION RISK: {v}")

if __name__ == "__main__":
    main()
