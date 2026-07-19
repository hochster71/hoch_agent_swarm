from __future__ import annotations
import os
from typing import Dict, List, Optional, Set
import yaml

class ProfileLoader:
    def __init__(self, profiles_dir: str = None):
        self.profiles_dir = profiles_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../coordination/audit_factory/profiles")
        )
        self.profiles: Dict[str, dict] = {}
        self.load_all_profiles()

    def load_all_profiles(self):
        if not os.path.exists(self.profiles_dir):
            raise FileNotFoundError(f"Profiles directory not found at {self.profiles_dir}")
        
        for fname in os.listdir(self.profiles_dir):
            if fname.endswith(".yaml") or fname.endswith(".yml"):
                p_path = os.path.join(self.profiles_dir, fname)
                with open(p_path, "r") as f:
                    p_data = yaml.safe_load(f)
                
                profile_name = os.path.splitext(fname)[0]
                self.profiles[profile_name] = p_data.get("profile", {})

    def resolve_profile(self, name: str) -> Set[str]:
        profile = self.profiles.get(name)
        if not profile:
            raise ValueError(f"Profile '{name}' not found.")

        active_controls = set(profile.get("active_control_ids", []))
        parent_name = profile.get("inherits")
        
        if parent_name:
            # Recursively resolve parent controls
            parent_controls = self.resolve_profile(parent_name)
            active_controls.update(parent_controls)

        return active_controls
