import yaml
import os
from pathlib import Path
from typing import Dict, Any

class LocalPrintAdapter:
    def __init__(self):
        self.config = {}
        config_path = Path("/app/config/local_print_policy.yaml") if os.path.exists("/app") else Path(__file__).resolve().parent.parent.parent / "config" / "local_print_policy.yaml"
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = yaml.safe_load(f)
        except Exception:
            pass
            
        self.print_policy = self.config.get("local_print", {
            "allowlist_printers": ["HP-OfficeJet-Pro-WiFi", "HP-LaserJet-WiFi", "Local-Virtual-PDF-Printer"],
            "require_preview": True,
            "require_operator_approval": True
        })

    def print_brief(self, brief_content: str, printer_name: str, operator_approved: bool) -> Dict[str, Any]:
        """
        Simulate Wi-Fi handshake and print execution for the brief.
        """
        if printer_name not in self.print_policy["allowlist_printers"]:
            return {
                "success": False,
                "error": f"Printer '{printer_name}' is not in the allowlist of approved printers.",
                "handshake": "FAILED"
            }
            
        if self.print_policy["require_operator_approval"] and not operator_approved:
            return {
                "success": False,
                "error": "Print job aborted: Operator approval required but not granted.",
                "handshake": "PENDING_APPROVAL"
            }
            
        # Simulate Wi-Fi handshake and transmission
        return {
            "success": True,
            "printer": printer_name,
            "handshake": "SUCCESS",
            "bytes_sent": len(brief_content.encode("utf-8")),
            "job_status": "COMPLETED",
            "message": f"Successfully printed operator brief to {printer_name} via Wi-Fi."
        }
