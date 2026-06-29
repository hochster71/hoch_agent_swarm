class GoogleAdapter:
    def __init__(self):
        pass
        
    def get_status(self) -> dict:
        return {"connected": True, "scope": "read_only"}
