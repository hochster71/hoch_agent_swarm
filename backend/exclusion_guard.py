import os
import json
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from backend.runtime_truth.state_store import resolve_root_dir
ROOT = Path(resolve_root_dir())
ROUTING_PATH = ROOT / "src/hoch_agent_swarm/config/model_routing.yaml"
EXCLUDE_FILE_PATH = ROOT / "src/hoch_agent_swarm/config/rclone-exclude.txt"

class ExclusionGuard:
    def __init__(self):
        self.manifests_root = Path.home() / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library"
        self.blobs_root = Path.home() / ".ollama" / "models" / "blobs"

    def get_active_models(self) -> List[str]:
        models = set()
        # 1. Read from routing config
        if ROUTING_PATH.exists():
            try:
                with open(ROUTING_PATH, "r") as f:
                    config = yaml.safe_load(f) or {}
                routing = config.get("routing", {})
                for rule in routing.values():
                    if rule.get("primary"):
                        models.add(rule.get("primary"))
                    if rule.get("fallback"):
                        models.add(rule.get("fallback"))
            except Exception as e:
                print(f"Error reading routing config in ExclusionGuard: {e}")
        
        # 2. Add env default model
        env_default = os.getenv("MODEL", "ollama/llama3.1:8b")
        models.add(env_default)
        return sorted(list(models))

    def resolve_protected_assets(self) -> Dict[str, Any]:
        active_models = self.get_active_models()
        protected_manifests: List[str] = []
        protected_blobs: List[Dict[str, Any]] = []
        blob_digests: Set[str] = set()
        total_bytes = 0

        for raw_model in active_models:
            name = raw_model
            if name.startswith("ollama/"):
                name = name[len("ollama/"):]
            
            if ":" in name:
                family, tag = name.split(":", 1)
            else:
                family, tag = name, "latest"

            manifest_file = self.manifests_root / family / tag
            if manifest_file.exists():
                rel_manifest = f"manifests/registry.ollama.ai/library/{family}/{tag}"
                protected_manifests.append(rel_manifest)
                
                try:
                    with open(manifest_file, "r") as f:
                        data = json.load(f)
                    
                    # Gather configuration digest
                    cfg = data.get("config", {})
                    if cfg.get("digest"):
                        blob_digests.add(cfg["digest"])
                    
                    # Gather layers digests
                    for layer in data.get("layers", []):
                        if layer.get("digest"):
                            blob_digests.add(layer["digest"])
                except Exception as e:
                    print(f"Error reading manifest {manifest_file}: {e}")

        # Resolve blob filenames and sizes
        for digest in sorted(list(blob_digests)):
            # Digest is in form: sha256:<hash>
            if digest.startswith("sha256:"):
                hash_val = digest[len("sha256:"):]
                blob_name = f"sha256-{hash_val}"
                blob_path = self.blobs_root / blob_name
                
                size = -1
                exists = False
                if blob_path.exists():
                    size = blob_path.stat().st_size
                    total_bytes += size
                    exists = True

                protected_blobs.append({
                    "digest": digest,
                    "filename": blob_name,
                    "rel_path": f"blobs/{blob_name}",
                    "size_bytes": size,
                    "exists": exists
                })

        return {
            "active_models": active_models,
            "protected_manifests": sorted(protected_manifests),
            "protected_blobs": protected_blobs,
            "total_protected_bytes": total_bytes,
            "exclude_file_path": str(EXCLUDE_FILE_PATH),
            "exclude_file_exists": EXCLUDE_FILE_PATH.exists()
        }

    def generate_exclude_file(self) -> Dict[str, Any]:
        assets = self.resolve_protected_assets()
        
        lines = [
            "# Safe Model Storage Exclude List",
            f"# Generated: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
            f"# Active Routing Models: {', '.join(assets['active_models'])}",
            "#",
            "# Usage with rclone:",
            "#   rclone sync ~/.ollama/models/ remote:backup/models/ --exclude-from rclone-exclude.txt",
            "#",
            "",
            "# Protect manifest directories and active tags",
        ]

        for manifest in assets["protected_manifests"]:
            lines.append(f"/{manifest}")
        
        lines.append("")
        lines.append("# Protect underlying model weights and config blobs")
        
        for blob in assets["protected_blobs"]:
            lines.append(f"/{blob['rel_path']}")

        lines.append("")

        try:
            EXCLUDE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            EXCLUDE_FILE_PATH.write_text("\n".join(lines), encoding="utf-8")
            assets["exclude_file_exists"] = True
            assets["status"] = "SUCCESS"
            assets["message"] = f"Exclude filter file successfully generated at {EXCLUDE_FILE_PATH}"
        except Exception as e:
            assets["status"] = "ERROR"
            assets["message"] = f"Failed to write exclude filter file: {e}"

        return assets

# Global exclusion guard instance
GUARD = ExclusionGuard()
