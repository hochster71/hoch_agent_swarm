from typing import Dict, Any, List

class ProductSearchRunner:
    def __init__(self):
        # High-fidelity mock products matching domain details
        self.mock_rat_toys = [
            {
                "id": "rat-001",
                "title": "Washable Fleece Tunnel for Small Animals",
                "material": "washable fabric, fleece",
                "diameter_inches": 3.0,
                "price": 15.99,
                "seller": "Amazon.com",
                "condition": "new/sealed",
                "description": "Premium double-layer fleece tunnel. Easy to wash. Fits baby rats and guinea pigs.",
                "url": "https://www.amazon.com/dp/B001PETTUNNEL"
            },
            {
                "id": "rat-002",
                "title": "Untreated Apple Wood Chew Sticks",
                "material": "untreated wood",
                "diameter_inches": 0.0,
                "price": 7.99,
                "seller": "Amazon.com",
                "condition": "new/sealed",
                "description": "100% pesticide-free apple orchard branch sticks. Dental chew safe.",
                "url": "https://www.amazon.com/dp/B002WOODCHEW"
            },
            {
                "id": "rat-003",
                "title": "Giant Cardboard Tunnel Play Tubes",
                "material": "cardboard",
                "diameter_inches": 4.0,
                "price": 9.99,
                "seller": "Amazon.com",
                "condition": "new/sealed",
                "description": "Thick, unbleached brown paper tubes. Completely chew-safe.",
                "url": "https://www.amazon.com/dp/B003CARDBOARD"
            },
            {
                "id": "rat-004",
                "title": "Hanging Fleece Hammock Bed",
                "material": "fleece",
                "diameter_inches": 0.0,
                "price": 12.49,
                "seller": "Amazon.com",
                "condition": "new/sealed",
                "description": "Double-layer hammock with secure metal clips. Nice hanging spot.",
                "url": "https://www.amazon.com/dp/B004HAMMOCK"
            },
            {
                "id": "rat-005",
                "title": "Hamster Plastic Play Tube System (Small)",
                "material": "small plastic pieces",
                "diameter_inches": 1.8,
                "price": 8.99,
                "seller": "PetSmart",
                "condition": "new/sealed",
                "description": "Interconnecting plastic tubes. Suitable for tiny dwarf hamsters.",
                "url": "https://www.amazon.com/dp/B005PLASTICTUBE"
            },
            {
                "id": "rat-006",
                "title": "Pine Wooden Bridge (Treated/Varnished)",
                "material": "painted wood, pine",
                "diameter_inches": 0.0,
                "price": 11.99,
                "seller": "Third Party Seller",
                "condition": "new/sealed",
                "description": "Sturdy pine wood arch bridge painted with high gloss finish.",
                "url": "https://www.amazon.com/dp/B006TREATEDWOOD"
            }
        ]

        self.mock_lego_disney = [
            {
                "id": "lego-001",
                "title": "LEGO Disney Princess Ariel's Celebration Boat",
                "age_rating": 4,
                "price": 29.99,
                "seller": "Amazon.com",
                "condition": "new/sealed",
                "description": "Easy-to-build celebration boat. Warning: Contains small parts.",
                "url": "https://www.amazon.com/dp/B007LEGOARIEL"
            },
            {
                "id": "lego-002",
                "title": "LEGO Disney Mickey and Minnie Creative Box",
                "age_rating": 6,
                "price": 34.99,
                "seller": "Amazon.com",
                "condition": "new/sealed",
                "description": "Creative building bricks set with Mickey and Minnie figures.",
                "url": "https://www.amazon.com/dp/B008LEGOMICKEY"
            },
            {
                "id": "lego-003",
                "title": "LEGO Disney Frozen Elsa's Castle",
                "age_rating": 4,
                "price": 39.99,
                "seller": "Official LEGO Store",
                "condition": "new/sealed",
                "description": "Elsa's magical ice palace castle with slide and minidolls.",
                "url": "https://www.amazon.com/dp/B009LEGOELSA"
            },
            {
                "id": "lego-004",
                "title": "LEGO Disney Castle (Advanced Collector Series)",
                "age_rating": 18,
                "price": 349.99,
                "seller": "eBay Seller",
                "condition": "used",
                "description": "Huge 4000-piece castle building kit. Missing box, built once.",
                "url": "https://www.amazon.com/dp/B010LEGOCASTLE"
            }
        ]

    def search(self, query: str, domain: str) -> List[Dict[str, Any]]:
        if domain == "PET_TOYS":
            return self.mock_rat_toys
        elif domain == "CHILD_TOYS":
            return self.mock_lego_disney
        else:
            # Fallback empty list or generic household mocks
            return [
                {
                    "id": "house-001",
                    "title": "Simple Lavender Bar Soap",
                    "price": 4.99,
                    "seller": "Target",
                    "condition": "new/sealed",
                    "description": "All natural bar soap.",
                    "url": "https://www.amazon.com/dp/B001SOAP"
                }
            ]
