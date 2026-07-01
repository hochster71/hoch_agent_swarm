class ImprovementBacklog:
    def __init__(self):
        self.backlog = []
        
    def add_item(self, title: str, description: str):
        self.backlog.append({
            "title": title,
            "description": description,
            "status": "backlog"
        })
        
    def get_items(self) -> list:
        return self.backlog
