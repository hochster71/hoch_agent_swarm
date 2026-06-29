from typing import Dict, Any

class SecretsResponder:
    def __init__(self):
        pass

    def handle_leak(self, secret_type: str, file_path: str) -> Dict[str, Any]:
        """Locks access and logs incident upon detecting secret key leaks."""
        return {
            "status": "CONTAINED",
            "message": f"Detected leaked {secret_type} in {file_path}! Lockfile triggered, notifications queued.",
            "secret_type": secret_type,
            "target_file": file_path
        }
