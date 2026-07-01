class ModelRouterPolicy:
    def __init__(self):
        pass
        
    def select_best_model(self, task: str) -> str:
        # Route by measured performance
        if "repair" in task.lower() or "code" in task.lower():
            return "anthropic/claude-3-5-sonnet"
        return "openai/gpt-4o"
