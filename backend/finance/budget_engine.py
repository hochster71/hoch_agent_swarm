import json
from pathlib import Path
from typing import Dict, Any, List

class BudgetEngine:
    def __init__(self, config_path: Path = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "finance" / "budget_categories.json"
        self.config_path = config_path
        self.categories_rules = []
        self.load_categories()

    def load_categories(self):
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                self.categories_rules = data.get("categories", [])
            except Exception as e:
                print(f"[BudgetEngine] Error loading categories config: {e}")

    def categorize_transaction(self, tx_name: str, merchant_name: str = "") -> Dict[str, Any]:
        combined = f"{tx_name} {merchant_name or ''}".lower()
        
        for rule in self.categories_rules:
            cat = rule.get("household_category")
            keywords = rule.get("keywords", [])
            for kw in keywords:
                if kw in combined:
                    return {
                        "household_category": cat,
                        "confidence": 1.0,
                        "needs_review": False,
                        "reason": f"Matched keyword '{kw}'"
                    }
        
        return {
            "household_category": "One-Off / Review",
            "confidence": 0.5,
            "needs_review": True,
            "reason": "No keyword matches found. Defaulting to Review."
        }

    def calculate_monthly_budget(self, transactions: List[Dict[str, Any]], balances: List[Dict[str, Any]], liabilities: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        category_totals = {}
        review_items = []
        
        net_income = 0.0
        fixed_obligations = 0.0
        variable_spending = 0.0
        debt_minimums = 0.0
        savings_investing = 0.0

        targets = {
            "Mortgage / Rent": 2000.0,
            "Utilities": 400.0,
            "Groceries": 500.0,
            "Dining": 300.0,
            "Fuel / Transportation": 200.0,
            "Insurance": 250.0,
            "Subscriptions": 80.0,
            "Debt Payments": 500.0,
            "Kids / School": 400.0,
            "Medical": 150.0,
            "Home Maintenance": 200.0,
            "Pets": 100.0,
            "Savings / Investing": 1000.0
        }

        for tx in transactions:
            amount = tx.get("amount", 0.0)
            cat = tx.get("household_category")
            
            if tx.get("needs_review") or cat == "One-Off / Review":
                review_items.append(tx)

            category_totals[cat] = category_totals.get(cat, 0.0) + amount

        for cat, total in category_totals.items():
            if cat == "Income":
                if total < 0:
                    net_income += abs(total)
                else:
                    net_income += total
            elif cat in ["Mortgage / Rent", "Utilities", "Insurance", "Debt Payments"]:
                fixed_obligations += total
                if cat == "Debt Payments":
                    debt_minimums += total
            elif cat in ["Groceries", "Dining", "Fuel / Transportation", "Kids / School", "Medical", "Home Maintenance", "Pets", "One-Off / Review", "Subscriptions"]:
                variable_spending += total
            elif cat == "Savings / Investing":
                savings_investing += total

        if liabilities:
            for l in liabilities:
                min_pay = l.get("minimum_payment", 0.0)
                debt_minimums += min_pay
                fixed_obligations += min_pay

        free_cash_flow = net_income - fixed_obligations - variable_spending - savings_investing

        budget_variance = {}
        for cat, target in targets.items():
            actual = category_totals.get(cat, 0.0)
            budget_variance[cat] = {
                "target": target,
                "actual": actual,
                "variance": actual - target
            }

        return {
            "net_income": round(net_income, 2),
            "fixed_obligations": round(fixed_obligations, 2),
            "variable_spending": round(variable_spending, 2),
            "debt_minimums": round(debt_minimums, 2),
            "savings_investing": round(savings_investing, 2),
            "free_cash_flow": round(free_cash_flow, 2),
            "category_totals": {k: round(v, 2) for k, v in category_totals.items()},
            "budget_variance": budget_variance,
            "review_items": review_items
        }
