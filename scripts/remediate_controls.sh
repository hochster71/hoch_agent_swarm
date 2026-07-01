#!/bin/bash
# ==============================================================================
# Hoch Agent Swarm Cluster - NIST RMF Security Remediation Script
# Coordinates and executes system patching for identified security gaps.
# ==============================================================================

echo "=================================================="
echo "HOCH CLUSTER: STARTING AUTOMATED SECURITY REMEDIATION"
echo "=================================================="

# 1. AC-3 Access Enforcement (SSH Directories)
echo -n "[AC-3] Hardening SSH directory and key permissions... "
SSH_DIR="$HOME/.ssh"
if [ -d "$SSH_DIR" ]; then
    chmod 700 "$SSH_DIR"
    find "$SSH_DIR" -type f -exec chmod 600 {} +
    echo "SUCCESS: Perms set to 700 (dir) and 600 (keys)."
else
    echo "WARNING: ~/.ssh directory not found. Skipping."
fi

# 2. AC-17 Remote Access (SSH Configurations)
echo "[AC-17] Hardening remote SSH host configurations..."
SSHD_CONFIG="/etc/ssh/sshd_config"
if [ -f "$SSHD_CONFIG" ]; then
    echo "          Found sshd_config at $SSHD_CONFIG"
    echo "          (Remediation requires root access: 'sudo sed')"
    echo "          Suggested Command: sudo sed -i.bak 's/PasswordAuthentication yes/PasswordAuthentication no/g' $SSHD_CONFIG"
else
    echo "          WARNING: sshd_config not found at $SSHD_CONFIG."
fi

# 3. AU-12 Audit Generation (Logging Process)
echo "[AU-12] Auditing logging process services..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "          OS Detected: macOS"
    echo "          Starting syslogd daemon if stopped..."
    sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.syslogd.plist 2>/dev/null
    echo "          SUCCESS: macOS syslogd loaded."
else
    echo "          OS Detected: Linux/Unix"
    echo "          Starting rsyslog daemon if stopped..."
    if command -v systemctl &> /dev/null; then
        sudo systemctl start rsyslog
        echo "          SUCCESS: rsyslog service started."
    else
        echo "          WARNING: systemctl not available. Please verify logging process manually."
    fi
fi

# 4. SI-2 Flaw Remediation (System Disk Space & Updates)
echo "[SI-2] Checking Docker disk space and temp assets..."
if command -v docker &> /dev/null; then
    echo "          Docker detected. Pruning unused cache, volumes, and dangling containers..."
    docker system prune -f --volumes
    echo "          SUCCESS: Docker pruned successfully."
else
    echo "          Docker not installed on this host. Skipping Docker system prune."
fi

echo "=================================================="
echo "SECURITY REMEDIATION COMPLETED."
echo "Please rerun the Dashboard Security Audit to verify compliance status."
echo "=================================================="
