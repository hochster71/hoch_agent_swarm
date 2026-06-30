import os
from pathlib import Path

def project_root() -> Path:
    """
    Returns the project root path. Honors HAS_PROJECT_ROOT, defaulting to /app if it exists,
    otherwise falling back to resolving the repository root dynamically.
    """
    if "HAS_PROJECT_ROOT" in os.environ:
        return Path(os.environ["HAS_PROJECT_ROOT"]).resolve()
    if os.path.exists("/app"):
        return Path("/app")
    # Dynamically locate repository root from current file path
    current_file = Path(__file__).resolve()
    return current_file.parent.parent

def data_root() -> Path:
    """
    Returns the data root path. Honors HAS_DATA_ROOT, defaulting to project_root() / "data".
    """
    if "HAS_DATA_ROOT" in os.environ:
        return Path(os.environ["HAS_DATA_ROOT"]).resolve()
    return project_root() / "data"

def evidence_root() -> Path:
    """
    Returns the evidence root path. Honors HAS_EVIDENCE_ROOT, defaulting to project_root() / "docs/evidence".
    """
    if "HAS_EVIDENCE_ROOT" in os.environ:
        return Path(os.environ["HAS_EVIDENCE_ROOT"]).resolve()
    return project_root() / "docs" / "evidence"

def resolve_under_project(*parts) -> Path:
    """
    Resolve path components under the project root, preventing path traversal.
    """
    root = project_root()
    resolved = Path(root, *parts).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError(f"Path traversal detected: {resolved} is not under {root}")
    return resolved

def optional_ag_scratch_root() -> Path:
    """
    Returns the AG scratch root. Defaulting to a container-safe location.
    """
    if "HAS_AG_SCRATCH_ROOT" in os.environ:
        return Path(os.environ["HAS_AG_SCRATCH_ROOT"]).resolve()
    return data_root() / "ag_scratch"

def optional_ag_brain_root() -> Path:
    """
    Returns the AG brain root. Defaulting to a container-safe location.
    """
    if "HAS_AG_BRAIN_ROOT" in os.environ:
        return Path(os.environ["HAS_AG_BRAIN_ROOT"]).resolve()
    return data_root() / "ag_brain"
