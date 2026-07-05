# Debt Planner Specification

The debt planner analyzes household liabilities and creates priority payoff strategies for:
1. **Avalanche**: Sorting by highest Interest Rate (APR) descending.
2. **Snowball**: Sorting by lowest current Balance ascending.
3. **Hybrid**: Balancing small wins (debts under $1,000 paid immediately) and APR priority.

## Output Structure
Each strategy outputs:
- **Payoff Order**: Sorter list of debt targets.
- **Estimated Months to Pay Off**: Simulates extra payments applying monthly surplus.
- **Total Interest Paid**: Calculated based on simulated interest compounding.
- **Assumptions**: Base assumptions like fixed surplus and minimum payments.
