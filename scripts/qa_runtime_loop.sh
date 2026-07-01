#!/bin/bash
# Forcibly lock repository root
cd /Users/michaelhoch/hoch_agent_swarm

LOG_FILE="/Users/michaelhoch/hoch_agent_swarm/data/qa_loop.log"
mkdir -p "$(dirname "$LOG_FILE")"

# Execute python script and pipe all outputs
uv run python scripts/qa_runtime_loop.py > "$LOG_FILE" 2>&1
exit_code=$?

echo "QA Runtime Loop finished with code $exit_code" >> "$LOG_FILE"
exit $exit_code
