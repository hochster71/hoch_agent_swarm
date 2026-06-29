import hashlib

def calculate_checksum(data):
    # Enforces cryptographically secure SHA-256
    return hashlib.sha256(data.encode()).hexdigest()
