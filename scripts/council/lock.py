import os
import sys
import fcntl
from pathlib import Path

LOCK_PATH = Path(__file__).resolve().parents[3] / "coordination" / "council" / "harness.lock"
_lock_fd = None

def duplicate_processes() -> bool:
    """Check if another harness process holds the lock."""
    if not LOCK_PATH.parent.exists():
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # We got the lock, so there are no duplicate processes.
        # Release it so acquire() can take it properly.
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        return False
    except (BlockingIOError, OSError):
        return True

def acquire():
    """Acquire the harness lock."""
    global _lock_fd
    if not LOCK_PATH.parent.exists():
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    _lock_fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR)
    fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

def release():
    """Release the harness lock."""
    global _lock_fd
    if _lock_fd is not None:
        fcntl.flock(_lock_fd, fcntl.LOCK_UN)
        os.close(_lock_fd)
        _lock_fd = None

def is_clear() -> bool:
    """Check if the lock is currently clear."""
    return not duplicate_processes()
