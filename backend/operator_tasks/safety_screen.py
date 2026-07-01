import yaml
import os
from pathlib import Path
from typing import Dict, Any, List

class SafetyScreen:
    def __init__(self):
        # Load config if possible, else fall back to defaults
        self.config = {}
        config_path = Path("/app/config/shopping_research_policy.yaml") if os.path.exists("/app") else Path(__file__).resolve().parent.parent.parent / "config" / "shopping_research_policy.yaml"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f)
        except Exception:
            pass
            
        # Defaults
        self.baby_rat_policy = self.config.get("baby_rat_toy_safety", {
            "allowed_materials": ["washable fabric", "fleece", "untreated wood", "cardboard", "paper tissues"],
            "avoid_materials": ["sharp wire", "painted wood", "treated wood", "small plastic pieces", "toxic glue", "toxic foam", "threads", "strings", "cedar", "pine"],
            "minimum_tunnel_diameter_inches": 2.5,
            "supervision_required": True
        })
        self.child_toy_policy = self.config.get("child_toy_safety", {
            "maximum_acceptable_age_rating": 12,
            "choking_hazard_keywords": ["small parts", "choking hazard", "under 3 years"],
            "trusted_sellers": ["Amazon.com", "Official LEGO Store", "Target"],
            "required_condition": "new/sealed"
        })

    def screen_baby_rat_toy(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate if a baby rat toy/enrichment item is safe.
        """
        violations = []
        warnings = []
        
        # Check material
        material = product.get("material", "").lower()
        title = product.get("title", "").lower()
        description = product.get("description", "").lower()
        
        # Avoidlist check
        for avoid in self.baby_rat_policy["avoid_materials"]:
            if avoid in material or avoid in title or avoid in description:
                violations.append(f"Avoid list material matched: '{avoid}'")
                
        # Allowed check
        has_allowed = False
        for allowed in self.baby_rat_policy["allowed_materials"]:
            if allowed in material or allowed in title or allowed in description:
                has_allowed = True
                break
        if not has_allowed and material:
            warnings.append(f"Material '{material}' not explicitly in allowed safety list.")
            
        # Check tunnel diameter if it is a tunnel/tube/system
        if "tunnel" in title or "tube" in title or "system" in title or "bridge" in title:
            diameter = product.get("diameter_inches", 0.0)
            if diameter > 0.0 and diameter < self.baby_rat_policy["minimum_tunnel_diameter_inches"]:
                violations.append(f"Tunnel diameter {diameter} inches is below safe minimum of {self.baby_rat_policy['minimum_tunnel_diameter_inches']} inches.")
            elif diameter == 0.0:
                warnings.append("Diameter unspecified for tunnel-style product.")
                
        # Supervision notice
        supervision = self.baby_rat_policy["supervision_required"]
        
        passed = len(violations) == 0
        return {
            "passed": passed,
            "violations": violations,
            "warnings": warnings,
            "supervision_required": supervision,
            "domain": "PET_TOYS"
        }

    def screen_child_toy(self, product: Dict[str, Any], child_age: int = 5) -> Dict[str, Any]:
        """
        Evaluate if a child toy is safe for the specified age.
        """
        violations = []
        warnings = []
        
        # Check age rating
        age_rating = product.get("age_rating", 0)
        max_rating = self.child_toy_policy["maximum_acceptable_age_rating"]
        if age_rating > child_age:
            violations.append(f"Product age rating ({age_rating}) exceeds child age ({child_age}).")
            
        # Check choking hazard keywords for kids under 3
        description = product.get("description", "").lower()
        title = product.get("title", "").lower()
        if child_age < 3:
            for keyword in self.child_toy_policy["choking_hazard_keywords"]:
                if keyword in description or keyword in title:
                    violations.append(f"Choking hazard detected for child under 3: '{keyword}'")
                    
        # Check seller trust
        seller = product.get("seller", "")
        if seller and seller not in self.child_toy_policy["trusted_sellers"]:
            warnings.append(f"Seller '{seller}' is not in the trusted allowlist.")
            
        # Check condition
        condition = product.get("condition", "").lower()
        if condition and condition != self.child_toy_policy["required_condition"].lower():
            violations.append(f"Product condition is '{condition}', required is '{self.child_toy_policy['required_condition']}'.")
            
        passed = len(violations) == 0
        return {
            "passed": passed,
            "violations": violations,
            "warnings": warnings,
            "domain": "CHILD_TOYS"
        }
