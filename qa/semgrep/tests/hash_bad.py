import hashlib

def calculate_checksum(data):
    # Matches weak hash pattern md5 and sha1
    h_md5 = hashlib.md5(data.encode()).hexdigest()
    h_sha1 = hashlib.sha1(data.encode()).hexdigest()
    return h_md5, h_sha1
