import os
import yaml

class BrandRenderer:
    def __init__(self, root_dir=None):
        from backend.runtime_paths import project_root
        if root_dir is None:
            root_dir = str(project_root())
        self.root_dir = root_dir
        self.brand_path = os.path.join(root_dir, "config/brand/hoch_agent_swarm_brand.yaml")

    def get_theme_colors(self) -> dict:
        if not os.path.exists(self.brand_path):
            return {
                "background": "#0a0a0c",
                "surface": "#121216",
                "accent_teal": "#10b981",
                "text_primary": "#f3f4f6"
            }
        with open(self.brand_path, "r") as f:
            data = yaml.safe_load(f) or {}
        return data.get("brand_design_system", {}).get("colors", {})
        
    def get_font_rules(self) -> dict:
        if not os.path.exists(self.brand_path):
            return {"primary": "Outfit", "secondary": "Inter"}
        with open(self.brand_path, "r") as f:
            data = yaml.safe_load(f) or {}
        return data.get("brand_design_system", {}).get("fonts", {})
