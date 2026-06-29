from typing import Dict, Any, List

class PriceRanker:
    def __init__(self):
        pass

    def rank(self, candidates_with_screen: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort candidate items.
        Primary key: safety pass (True first, False last).
        Secondary key: price (lowest first).
        Tertiary key: number of warnings (lowest first).
        """
        def sorting_key(item_wrap):
            passed = item_wrap["safety_result"]["passed"]
            price = item_wrap["product"]["price"]
            warning_count = len(item_wrap["safety_result"]["warnings"])
            
            # Sort passed (True -> 0, False -> 1)
            passed_val = 0 if passed else 1
            return (passed_val, price, warning_count)

        ranked = sorted(candidates_with_screen, key=sorting_key)
        
        # Assign ranks
        for idx, item in enumerate(ranked):
            item["rank"] = idx + 1
            
        return ranked
