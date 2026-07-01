class PromptSummaryEngine:
    def summarize(self, prompt_text: str) -> str:
        prompt_text = prompt_text.strip()
        lines = [l.strip() for l in prompt_text.split("\n") if l.strip()]
        if not lines:
            return "Empty prompt"
            
        first_line = lines[0]
        if len(first_line) > 80:
            return first_line[:77] + "..."
        return first_line
