from typing import Dict, Any, List

class DebtPlanner:
    def plan(self, liabilities: List[Dict[str, Any]], monthly_surplus: float = 500.0) -> List[Dict[str, Any]]:
        # Map fields in case of legacy Plaid input formats
        mapped_liabilities = []
        for d in liabilities:
            mapped_liabilities.append({
                "account_id": d.get("account_id"),
                "balance": d.get("balance", d.get("current_balance", 0.0)),
                "apr": d.get("apr", d.get("apr_percentage", 0.0)),
                "minimum_payment": d.get("minimum_payment", d.get("minimum_payment_amount", 0.0)),
                "liability_type": d.get("liability_type", "credit")
            })

        # Avalanche (APR descending)
        avalanche_debts = sorted(mapped_liabilities, key=lambda x: x.get("apr", 0.0), reverse=True)
        avalanche_order = [{"account_id": d["account_id"], "liability_type": d["liability_type"]} for d in avalanche_debts]
        
        # Snowball (balance ascending)
        snowball_debts = sorted(mapped_liabilities, key=lambda x: x.get("balance", 0.0))
        snowball_order = [{"account_id": d["account_id"], "liability_type": d["liability_type"]} for d in snowball_debts]
        
        # Hybrid (balance <= $1000 first, then APR descending)
        small_wins = [d for d in mapped_liabilities if d.get("balance", 0.0) <= 1000.0]
        remaining = [d for d in mapped_liabilities if d.get("balance", 0.0) > 1000.0]
        
        hybrid_debts = sorted(small_wins, key=lambda x: x.get("balance", 0.0)) + sorted(remaining, key=lambda x: x.get("apr", 0.0), reverse=True)
        hybrid_order = [{"account_id": d["account_id"], "liability_type": d["liability_type"]} for d in hybrid_debts]
        
        min_total = sum(d.get("minimum_payment", 0.0) for d in mapped_liabilities)
        
        av_months, av_interest = self._simulate_payoff(avalanche_debts, min_total + monthly_surplus)
        sb_months, sb_interest = self._simulate_payoff(snowball_debts, min_total + monthly_surplus)
        hb_months, hb_interest = self._simulate_payoff(hybrid_debts, min_total + monthly_surplus)

        return [
            {
                "strategy": "Avalanche",
                "monthly_surplus_applied": monthly_surplus,
                "estimated_payoff_order": avalanche_order,
                "interest_priority": "High",
                "small_balance_priority": "Low",
                "minimum_payment_total": min_total,
                "months_to_payoff": av_months,
                "total_interest_paid": round(av_interest, 2),
                "risk_notes": "Optimized for minimal interest cost.",
                "assumptions": "Extra surplus applied strictly to highest APR first."
            },
            {
                "strategy": "Snowball",
                "monthly_surplus_applied": monthly_surplus,
                "estimated_payoff_order": snowball_order,
                "interest_priority": "Low",
                "small_balance_priority": "High",
                "minimum_payment_total": min_total,
                "months_to_payoff": sb_months,
                "total_interest_paid": round(sb_interest, 2),
                "risk_notes": "Psychologically rewarding but pays more interest.",
                "assumptions": "Extra surplus applied strictly to lowest balance first."
            },
            {
                "strategy": "Hybrid",
                "monthly_surplus_applied": monthly_surplus,
                "estimated_payoff_order": hybrid_order,
                "interest_priority": "Medium",
                "small_balance_priority": "Medium",
                "minimum_payment_total": min_total,
                "months_to_payoff": hb_months,
                "total_interest_paid": round(hb_interest, 2),
                "risk_notes": "Balanced approach for both speed and interest savings.",
                "assumptions": "Balances <= $1000 cleared first, then APR prioritized."
            }
        ]
        
    def _simulate_payoff(self, sorted_debts: List[Dict[str, Any]], total_monthly_budget: float) -> tuple[int, float]:
        debts = [dict(d) for d in sorted_debts]
        months = 0
        total_interest = 0.0
        
        while any(d["balance"] > 0 for d in debts) and months < 360:
            months += 1
            available_surplus = total_monthly_budget
            
            # Apply interest
            for d in debts:
                if d["balance"] > 0:
                    monthly_rate = (d.get("apr", 0.0) / 100.0) / 12.0
                    interest_charge = d["balance"] * monthly_rate
                    total_interest += interest_charge
                    d["balance"] += interest_charge
            
            # Pay minimums
            for d in debts:
                if d["balance"] > 0:
                    min_pay = min(d.get("minimum_payment", 0.0), d["balance"])
                    d["balance"] -= min_pay
                    available_surplus -= min_pay
            
            # Apply surplus
            if available_surplus > 0:
                for d in debts:
                    if d["balance"] > 0:
                        extra_pay = min(available_surplus, d["balance"])
                        d["balance"] -= extra_pay
                        available_surplus -= extra_pay
                        if available_surplus <= 0:
                            break
                            
        return months, total_interest
