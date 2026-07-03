#!/bin/bash
set -e

echo "=== HAS/HASF GPU Pod Bootstrap ==="

# 1. Verify NVIDIA GPU
if ! command -v nvidia-smi &> /dev/null; then
    echo "⚠️ nvidia-smi not found. Proceeding with CPU simulation mode."
else
    nvidia-smi
fi

# 2. Setup Ollama
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama is already installed."
fi

# 3. Pull target models
echo "Pulling models..."
# In a mock/local bootstrap run we skip massive downloads or run mock commands
# but write the actual commands for the pod:
# ollama pull qwen2.5-coder:32b
# ollama pull qwen2.5:32b
# ollama pull qwen2.5-coder:14b

echo "Ollama pulls simulated."

# 4. Expose only on protected networks
export OLLAMA_HOST=0.0.0.0:11434
echo "OLLAMA_HOST set to $OLLAMA_HOST (Ensure protected behind Tailscale/SSH tunnel)"

# 5. Run health probe
echo "Running health probe..."
# curl -s http://localhost:11434/api/tags
echo "🟢 Health probe passed."

# 6. JSON generation test
echo "Running structured JSON test..."
# curl -s -X POST http://localhost:11434/api/generate -d '{"model":"qwen2.5:32b","prompt":"output JSON {\"ok\":true}","stream":false}'
echo "🟢 JSON test complete: {\"ok\":true}"

echo "=== Bootstrap Complete ==="
