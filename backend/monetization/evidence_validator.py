import os

class EvidenceValidator:
    def __init__(self, root_dir=None):
        from backend.runtime_paths import project_root
        if root_dir is None:
            root_dir = str(project_root())
        self.root_dir = root_dir

    def validate_project_evidence(self, project_id: str, name: str, evidence_paths: list) -> dict:
        if not evidence_paths:
            return {
                "valid": False,
                "project_id": project_id,
                "name": name,
                "error": "No evidence paths specified for this project."
            }

        valid_paths = []
        invalid_paths = []
        
        for path in evidence_paths:
            # Map path relative to root if it is not absolute
            full_path = path if os.path.isabs(path) else os.path.join(self.root_dir, path)
            
            if not os.path.exists(full_path):
                invalid_paths.append(f"Path does not exist: {path}")
                continue
                
            if os.path.getsize(full_path) == 0:
                invalid_paths.append(f"Evidence file is empty (0 bytes): {path}")
                continue
                
            valid_paths.append(path)

        if len(valid_paths) == 0:
            return {
                "valid": False,
                "project_id": project_id,
                "name": name,
                "error": f"No valid non-empty evidence files found. Errors: {'; '.join(invalid_paths)}"
            }

        return {
            "valid": True,
            "project_id": project_id,
            "name": name,
            "valid_paths": valid_paths,
            "invalid_paths": invalid_paths
        }
