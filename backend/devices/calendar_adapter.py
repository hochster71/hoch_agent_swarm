class CalendarAdapter:
    def __init__(self):
        pass
        
    def get_events(self) -> list:
        return [
            {"id": "evt-1", "title": "Family Dinner", "start": "2026-06-30T18:00:00"}
        ]
        
    def delete_event(self, event_id: str) -> dict:
        # Block deletions without manual override
        return {
            "status": "BLOCKED",
            "message": "Direct calendar deletion blocked by policy-as-code."
        }
