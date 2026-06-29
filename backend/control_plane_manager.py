import os
import json
import logging
import subprocess

logger = logging.getLogger("ControlPlaneManager")
CONFIG_PATH = "data/control_plane_config.json"

DEFAULT_CONFIG = {
    "selected_autonomy_level": "L1",  # L0, L1, L2, L3, L4, L5
    "active_profile": "home",          # home, work, cyber, tv
    "safety_status": "running",       # running, paused
}

class ControlPlaneManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self) -> dict:
        os.makedirs("data", exist_ok=True)
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    return {**DEFAULT_CONFIG, **json.load(f)}
            except Exception as e:
                logger.error(f"Failed to read control plane config: {e}")
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write control plane config: {e}")

    def get_policy(self) -> dict:
        return self.config

    def update_policy(self, autonomy_level: str = None, profile: str = None, safety_status: str = None) -> dict:
        if autonomy_level in ["L0", "L1", "L2", "L3", "L4", "L5"]:
            self.config["selected_autonomy_level"] = autonomy_level
        if profile in ["home", "work", "cyber", "tv"]:
            self.config["active_profile"] = profile
        if safety_status in ["running", "paused"]:
            self.config["safety_status"] = safety_status
        self.save_config()
        return self.config

    def is_action_allowed(self, action_type: str, severity: str = "medium", cost: float = 0.0) -> tuple[bool, str]:
        """
        Policy Engine Gate: Evaluates if an action is allowed based on Autonomy Level and Profile.
        """
        # Safety Pause override
        if self.config.get("safety_status") == "paused":
            return False, "SAFETY_PAUSED: Swarm is paused. No autonomous actions allowed."

        autonomy = self.config.get("selected_autonomy_level", "L1")
        profile = self.config.get("active_profile", "home")

        # 1. Profile Separation Gates
        if profile == "home":
            # IPTV / TV is allowed, coding / cyber tools require confirmation
            if "tv" in action_type:
                pass
            elif "cyber" in action_type or "code" in action_type:
                if autonomy in ["L0", "L1", "L2", "L3"]:
                    return False, f"PROFILE_GATE: '{action_type}' blocked on 'home' profile. Requires high autonomy (L4/L5) or operator override."
        elif profile == "work":
            # Swarm / code reviews allowed, TV blocked
            if "tv" in action_type:
                return False, f"PROFILE_GATE: TV streaming / diagnostic blocked on 'work' profile."
        elif profile == "cyber":
            # Only security scans and validations are fully automated
            if "trivy" in action_type or "semgrep" in action_type:
                pass
            else:
                if autonomy not in ["L4", "L5"]:
                    return False, f"PROFILE_GATE: Non-security action '{action_type}' requires L4/L5 autonomy on 'cyber' profile."
        elif profile == "tv":
            # Only IPTV proxy/cache is allowed
            if "tv" not in action_type:
                return False, f"PROFILE_GATE: Only TV activities are allowed on 'tv' profile."

        # 2. Autonomy Level Gates
        if autonomy == "L0":
            return False, "AUTONOMY_L0: All actions require manual approval."
        elif autonomy == "L1":
            return False, "AUTONOMY_L1: Human-in-the-Loop. Execution requires operator approval."
        elif autonomy == "L2":
            if action_type in ["read", "get", "query"]:
                return True, "AUTONOMY_L2: Reads allowed."
            return False, "AUTONOMY_L2: Assisted. Write / mutating actions require operator approval."
        elif autonomy == "L3":
            if cost <= 5.0:
                return True, "AUTONOMY_L3: Conditional. Safe budget actions automated."
            return False, f"AUTONOMY_L3: Blocked action costing ${cost:.2f} (> $5.00 limit)."
        elif autonomy == "L4":
            if action_type == "deploy" and severity == "critical":
                return False, "AUTONOMY_L4: Critical production deployment requires operator approval."
            return True, "AUTONOMY_L4: High autonomy allowed."
        elif autonomy == "L5":
            return True, "AUTONOMY_L5: Full autonomy enabled. No safety gates active."

        return True, "Allowed."

    def execute_rollback(self, target_tag: str) -> dict:
        """
        Orchestrates immediate rollback to a target tag using the rc22_rollback utility.
        """
        try:
            cmd = ["bash", "scripts/security/rc22_rollback.sh", target_tag]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {"status": "SUCCESS", "message": f"Rollback succeeded.", "output": res.stdout}
        except Exception as e:
            return {"status": "FAIL", "error": str(e)}

    def export_evidence_pack(self) -> bytes:
        """
        Zips and exports the active release candidate evidence bundle.
        """
        import io
        import zipfile
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            # Add release folder
            release_dir = "dist/releases/"
            if os.path.exists(release_dir):
                for root, _, files in os.walk(release_dir):
                    for file in files:
                        fp = os.path.join(root, file)
                        zip_file.write(fp, os.path.relpath(fp, release_dir))
        return zip_buffer.getvalue()

CONTROL_PLANE = ControlPlaneManager()
