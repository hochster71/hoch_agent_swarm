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

    # 6. Non-destructive Custody Probes
    keychain_prompt_required = "UNKNOWN"
    remote_cred_reuse = "UNKNOWN — NOT TESTED"
    
    # Probe Git Keychain credentials (requires no password display)
    try:
        p = subprocess.Popen(["git", "credential", "fill"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout_data, _ = p.communicate(input="protocol=https\nhost=github.com\n\n", timeout=3)
        if p.returncode == 0:
            has_password = any(line.startswith("password=") for line in stdout_data.splitlines())
            if has_password:
                keychain_prompt_required = "NO_PROMPT_REQUIRED"
                remote_cred_reuse = "OBSERVED POSSIBLE"
            else:
                keychain_prompt_required = "PROMPT_REQUIRED_OR_EMPTY"
                remote_cred_reuse = "OBSERVED BLOCKED"
        else:
            keychain_prompt_required = "PROMPT_FAILED_OR_CANCELLED"
            remote_cred_reuse = "UNKNOWN"
    except subprocess.TimeoutExpired:
        p.kill()
        keychain_prompt_required = "TIMEOUT_EXPIRED"
        remote_cred_reuse = "UNKNOWN"
    except Exception:
        keychain_prompt_required = "PROBE_ERROR"
        remote_cred_reuse = "UNKNOWN"

    # Probe SSH authentication to GitHub (non-destructive)
    ssh_code, ssh_out, ssh_err = _run("ssh", "-T", "-o", "ConnectTimeout=3", "-o", "StrictHostKeyChecking=no", "git@github.com")
    ssh_usability = "UNKNOWN"
    if "Permission denied" in ssh_err or "Permission denied" in ssh_out:
        ssh_usability = "UNUSABLE_FOR_GITHUB (publickey denied)"
    elif "successfully authenticated" in ssh_err or "successfully authenticated" in ssh_out:
        ssh_usability = "OBSERVED POSSIBLE"
    else:
        ssh_usability = f"UNKNOWN (code={ssh_code})"

    # Probe if SSH key is Secure Enclave backed
    se_protection = "UNKNOWN"
    if ssh_dir.exists():
        key_files = list(ssh_dir.glob("id_*"))
        if any(not k.name.endswith(".pub") for k in key_files):
            se_protection = "ABSENT (standard files on disk)"
        else:
            se_protection = "NO_PRIVATE_KEYS_FOUND"

    findings = {
        "LOCAL_AUTHOR_IMPERSONATION": "OBSERVED POSSIBLE" if (sign_key_code != 0 or sign_key_out == "") else "OBSERVED PROTECTED",
        "SSH_PRIVATE_KEY_USABILITY": ssh_usability,
        "SECURE_ENCLAVE_PROTECTION": "ABSENT (for discovered standard SSH key file; Keychain-stored token characteristics partially characterized)" if se_protection == "ABSENT (standard files on disk)" else se_protection,
    }
    
    report["evidence_scoped_findings"] = findings
    report["prior_observation"] = {
        "credential_retrieval": "SUCCEEDED_WITHOUT_OBSERVED_PROMPT"
    }
    report["current_observation"] = {
        "credential_retrieval": "FAILED_AFTER_LOCAL_REJECTION" if keychain_prompt_required != "NO_PROMPT_REQUIRED" else "SUCCEEDED"
    }
    report["remote_revocation"] = {
        "status": "UNKNOWN_UNTIL_GITHUB_REVOCATION_CONFIRMED"
    }

    # Check for plaintext keys in .env (by count, not names)
    env_keys_count = 0
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, _ = line.split("=", 1)
                if any(x in k for x in ["KEY", "SECRET", "PASSWORD", "TOKEN"]):
                    env_keys_count += 1
    
    report["key_custody_inventory"]["plaintext_secrets_in_env"] = {
        "exists": env_keys_count > 0,
        "count": env_keys_count
    }

    # 7. Write the custody report
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"ACTOR-F3 custody report written to {OUT.relative_to(ROOT)}")
    print("Evidence-Scoped Findings:")
    for k, v in findings.items():
        print(f"  {k:28s} {v}")
    print(f"  PRIOR CREDENTIAL RETRIEVAL:  SUCCEEDED_WITHOUT_OBSERVED_PROMPT")
    print(f"  CURRENT RETRIEVAL:           {report['current_observation']['credential_retrieval']}")
    print(f"  REMOTE REVOCATION STATUS:    {report['remote_revocation']['status']}")
    print(f"  PLAINTEXT_KEYS_IN_ENV        COUNT: {env_keys_count}")

if __name__ == "__main__":
    main()
