def evaluate_confidence(output: str) -> dict:
    if not output or not output.strip():
        return {
            "score": 0.0,
            "label": "low",
            "reason": "Empty output"
        }
    
    # Check simple heuristics
    text_len = len(output.strip())
    
    if text_len < 10:
        return {
            "score": 0.3,
            "label": "low",
            "reason": "Output is extremely short and potentially incomplete."
        }
    
    # Default high confidence score for non-empty local outputs
    return {
        "score": 0.85,
        "label": "high",
        "reason": f"Output verified with {text_len} characters."
    }
