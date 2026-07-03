#!/bin/bash
# =============================================================================
# setup_agent_user.sh — create a non-login macOS role account for swarm agents
#
# SECURITY RATIONALE
# The founder key (~/.has_founder/) lives in michaelhoch's home directory.
# If the swarm backend runs as the same user (michaelhoch), a compromised
# agent can read the key at rest and forge approvals, collapsing all of C2.
# Running agents as a separate standard role account removes that path.
#
# macOS calls this a "role account" — a service account that cannot log in
# interactively. sysadminctl -roleAccount is Apple's recommended CLI tool for
# user account management since macOS 10.13 High Sierra [SS64/Apple DevForums].
# The Alcoholless project (NTT Labs, 2025) independently validated this exact
# pattern for sandboxing AI agents on macOS.
#
# Threat model closed by this change:
#   Compromised agent process (running as hoch_agent) CAN:
#     - read/write ~/hoch_agent_swarm (shared via ACL — see below)
#     - connect to localhost:8000
#     - call APIs gated by the founder key
#   Compromised agent process CANNOT:
#     - read /Users/michaelhoch (home is chmod 700)
#     - read ~/.has_founder/founder_signing_key (not accessible to hoch_agent)
#     - forge approvals (signing requires the passphrase + key file)
#     - read other secrets in michaelhoch's home
#
# USAGE
#   sudo bash scripts/setup_agent_user.sh
#
# REQUIREMENTS: must be run as admin (or sudo). macOS 13+.
# =============================================================================
set -euo pipefail

AGENT_USER="hoch_agent"
AGENT_HOME="/var/hoch_agent"
REPO="$HOME/hoch_agent_swarm"  # michaelhoch's repo clone
FOUNDER_HOME="$HOME/.has_founder"

[[ "$(id -u)" -eq 0 ]] || { echo "Run with sudo."; exit 1; }
ADMIN_USER="${SUDO_USER:-michaelhoch}"

echo "=== 1. Create role account: $AGENT_USER ==="
# -roleAccount: non-interactive, no GUI login, no home dir in /Users
# This is the Apple-recommended pattern for service accounts [Apple Developer Forums]
if id "$AGENT_USER" &>/dev/null; then
    echo "  User $AGENT_USER already exists — skipping creation."
else
    sysadminctl -addUser "$AGENT_USER" \
                -fullName "HAS Agent Runtime" \
                -UID 501 \
                -roleAccount \
                -password "$(openssl rand -hex 32)"   # long random; no interactive login
    echo "  Created $AGENT_USER."
fi

echo "=== 2. Home directory (outside agent's reach by default) ==="
mkdir -p "$AGENT_HOME"
chown "$AGENT_USER":staff "$AGENT_HOME"
chmod 750 "$AGENT_HOME"
# Set the home in Directory Services so launchd knows where to put env
dscl . -change "/Users/$AGENT_USER" NFSHomeDirectory \
        "/var/empty" "$AGENT_HOME" 2>/dev/null || true

echo "=== 3. Harden michaelhoch home against the agent user ==="
chmod 700 "/Users/$ADMIN_USER"
chmod 700 "$FOUNDER_HOME" 2>/dev/null || true
chmod 600 "$FOUNDER_HOME/founder_signing_key" 2>/dev/null || true
echo "  /Users/$ADMIN_USER and ~/.has_founder hardened to 700/600."

echo "=== 4. Grant agent read/write access to the repo only ==="
# ACL entry: hoch_agent can read/write the repo but not traverse to its parent
chmod +a "$AGENT_USER allow read,write,execute,delete,append,file_inherit,directory_inherit" \
    "$REPO"
echo "  ACL set: $AGENT_USER rw on $REPO only."

echo "=== 5. Verify isolation ==="
echo "  Checking agent cannot stat founder key..."
if sudo -u "$AGENT_USER" test -r "$FOUNDER_HOME/founder_signing_key" 2>/dev/null; then
    echo "  WARNING: agent can still read founder key — check permissions."
else
    echo "  OK: agent cannot read founder key."
fi

echo ""
echo "=== Next: update launchd plists to run as $AGENT_USER ==="
echo "  In com.hoch.agent.swarm.runtime.plist and any other plists,"
echo "  add: <key>UserName</key><string>$AGENT_USER</string>"
echo "  Then: sudo launchctl bootout system/ <plist> && sudo launchctl bootstrap system/ <plist>"
echo ""
echo "  For manual runs during dev: sudo -u $AGENT_USER bash scripts/has_goal_runner_daemon.sh"
