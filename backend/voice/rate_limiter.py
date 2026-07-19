from __future__ import annotations

import time
import threading
from typing import Dict, List

class VoiceRateLimiter:
    _lock = threading.Lock()
    _history: Dict[str, List[float]] = {}
    _max_per_hour = 30

    @classmethod
    def check_rate_limit(cls, identifier: str, limit: int = None) -> bool:
        """Returns True if the request is within rate limits, False if throttled."""
        limit = limit or cls._max_per_hour
        now = time.time()
        
        with cls._lock:
            # Get request timestamps for this identifier (e.g. device_id or actor_id)
            history = cls._history.get(identifier, [])
            
            # Filter to only keep requests within the last hour (3600 seconds)
            history = [t for t in history if now - t < 3600]
            
            if len(history) >= limit:
                return False
                
            history.append(now)
            cls._history[identifier] = history
            return True
