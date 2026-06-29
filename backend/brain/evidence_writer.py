import os
import logging
from datetime import datetime

logger = logging.getLogger("EvidenceWriter")

class EvidenceWriter:
    def __init__(self, root_dir="/Users/michaelhoch/hoch_agent_swarm"):
        self.evidence_dir = os.path.join(root_dir, "docs/evidence/brain")
        os.makedirs(self.evidence_dir, exist_ok=True)

    def write_session_evidence(self, session_id: str, action: str, status: str, details: str):
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}-brain-{session_id}.md"
        filepath = os.path.join(self.evidence_dir, filename)
        
        content = f"""# Brain Autonomy Evidence Log
Session: {session_id}
Timestamp: {datetime.utcnow().isoformat()}Z
Action: {action}
Status: {status}

## Verification Details
{details}

---
Verified by Hoch Swarm Autonomy Control Plane
"""
        try:
            with open(filepath, "w") as f:
                f.write(content)
            logger.info(f"Evidence file saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to write evidence log: {e}")
            return None
            
    def get_evidence_files(self) -> list:
        if not os.path.exists(self.evidence_dir):
            return []
        try:
            files = []
            for name in os.listdir(self.evidence_dir):
                if name.endswith(".md"):
                    path = os.path.join(self.evidence_dir, name)
                    stat = os.stat(path)
                    files.append({
                        "name": name,
                        "path": f"file://{path}",
                        "timestamp": datetime.utcfromtimestamp(stat.st_mtime).isoformat() + "Z"
                    })
            return sorted(files, key=lambda x: x["timestamp"], reverse=True)
        except Exception as e:
            logger.error(f"Error listing evidence files: {e}")
            return []
