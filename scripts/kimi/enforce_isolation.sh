#!/bin/zsh
set -euo pipefail
WS="${HOME}/Documents/kimi/workspace"
REG="${HOME}/Library/Application Support/kimi-desktop/kimi-agent/created-workspaces.json"
mkdir -p "$WS"
python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
path = Path.home() / "Library/Application Support/kimi-desktop/kimi-agent/created-workspaces.json"
ws = str(Path.home() / "Documents/kimi/workspace")
path.parent.mkdir(parents=True, exist_ok=True)
payload = {
    ws: {
        "label": "kimi-workspace-ONLY",
        "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "note": "HELM isolation: Kimi Desktop workspace is Documents/kimi/workspace only",
    }
}
# If existing already correct, keep createdAt
if path.exists():
    try:
        old = json.loads(path.read_text())
        if list(old.keys()) == [ws]:
            payload = old
    except Exception:
        pass
path.write_text(json.dumps(payload, indent=2) + "\n")
print("enforced workspace registry ->", ws)
PY
# claw display name
python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / "Library/Application Support/kimi-desktop/bridge-store/desktop-claw-prefs.json"
d = {}
if p.exists():
    try:
        d = json.loads(p.read_text() or "{}")
    except Exception:
        d = {}
d["customName"] = "kimi-workspace-ONLY"
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(d, indent=2) + "\n")
print("enforced claw name")
PY
# verify
exec "${HOME}/Documents/kimi/policy/verify_isolation.sh"
