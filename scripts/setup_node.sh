#!/bin/bash
# ==============================================================================
# Hoch Agent Swarm - Node Setup Script
# Configures a worker node (macOS / Linux) to join the local cluster.
# ==============================================================================

set -euo pipefail

# Configurations
CONTROL_PLANE_IP="10.0.0.6"
DEFAULT_OLLAMA_PORT=11434

echo "=================================================="
echo "Initializing Hoch Swarm Node Setup..."
echo "=================================================="

# 1. Detect OS
OS_TYPE=$(uname)
echo "Detected OS: $OS_TYPE"

# 2. Check and Setup SSH Authorization
echo "--> Configuring SSH authorization..."
SSH_DIR="$HOME/.ssh"
AUTHORIZED_KEYS="$SSH_DIR/authorized_keys"

if [ ! -d "$SSH_DIR" ]; then
    echo "Creating SSH directory..."
    mkdir -p "$SSH_DIR"
    chmod 700 "$SSH_DIR"
fi

if [ ! -f "$AUTHORIZED_KEYS" ]; then
    touch "$AUTHORIZED_KEYS"
    chmod 600 "$AUTHORIZED_KEYS"
fi

echo "Ensure the Control Plane public key (from MBP $CONTROL_PLANE_IP) is appended to: $AUTHORIZED_KEYS"

# 3. Check Python 3
echo "--> Checking Python 3..."
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "Found Python: $PYTHON_VERSION"
else
    echo "WARNING: Python 3 is not installed. Python 3.9+ is required for native runners."
fi

# 4. Check Docker
echo "--> Checking Docker..."
if command -v docker &>/dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "Found Docker: $DOCKER_VERSION"
else
    echo "INFO: Docker is not installed. If this is Mac Neo (L3) or Dell 9440 (W1), install Docker Desktop to run containerized agents."
fi

# 5. Check Ollama
echo "--> Checking local Ollama endpoint..."
if command -v ollama &>/dev/null; then
    echo "Found local Ollama CLI."
    # Check if Ollama is running
    if curl -s "http://localhost:${DEFAULT_OLLAMA_PORT}/api/tags" &>/dev/null; then
        echo "Ollama is running on port ${DEFAULT_OLLAMA_PORT}."
    else
        echo "WARNING: Ollama is installed but not running. Start it using: ollama serve"
    fi
else
    echo "INFO: Ollama is not installed locally. Node will query remote Ollama on the control plane or designated models."
fi

# 6. Create Agent Working Directory
SWARM_WORK_DIR="$HOME/hoch_swarm_node"
echo "--> Creating Swarm Node directory at $SWARM_WORK_DIR..."
mkdir -p "$SWARM_WORK_DIR/logs"
mkdir -p "$SWARM_WORK_DIR/workspace"

echo "=================================================="
echo "Setup Complete!"
echo "Please run: 'cat ~/.ssh/authorized_keys' to verify SSH configuration."
echo "=================================================="
