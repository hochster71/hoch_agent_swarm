from typing import Dict, Any, List

class PurchaseLinkPreparer:
    def __init__(self):
        pass

    def prepare_clean_link(self, product_url: str, tag: str = "has-operator-20") -> str:
        """
        Clean up trackers and append the clean associate tag or structure.
        """
        if "?" in product_url:
            base = product_url.split("?")[0]
        else:
            base = product_url
            
        return f"{base}?tag={tag}"

    def prepare_cart_draft(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a deep-link representing a cart draft containing the items.
        """
        item_ids = [item.get("id") for item in items]
        deep_link = f"https://www.amazon.com/gp/aws/cart/add.html?AssociateTag=has-operator-20"
        for idx, item in enumerate(items):
            deep_link += f"&ASIN.{idx+1}={item.get('id')}&Quantity.{idx+1}=1"
            
        return {
            "cart_url": deep_link,
            "items_added": len(items),
            "status": "DRAFT_PREPARED"
        }
