import os
import hashlib

class PODVault:
    def __init__(self):
        # Retrieve system/master keys securely from the environment
        self._master_secret = os.getenv("TRACKER_PASSWORD", "default-system-secret")
        self._vault_store = {}

    def store_secret(self, key: str, value: str):
        # Simulate local encryption using SHA256 hashed keys
        hashed_key = hashlib.sha256((key + self._master_secret).encode()).hexdigest()
        self._vault_store[hashed_key] = value

    def retrieve_secret(self, key: str) -> str:
        hashed_key = hashlib.sha256((key + self._master_secret).encode()).hexdigest()
        return self._vault_store.get(hashed_key, "")

    def contains_secret(self, key: str) -> bool:
        hashed_key = hashlib.sha256((key + self._master_secret).encode()).hexdigest()
        return hashed_key in self._vault_store

# Shared instance
vault = PODVault()
