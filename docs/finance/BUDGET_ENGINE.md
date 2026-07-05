# Budget Engine Specification

The budget engine takes in transaction databases, balance states, liabilities records, and returns deterministic budgeting and category variance calculations.

## Budget Category Assignment
Transactions are mapped based on `config/finance/budget_categories.json` rules:
- **Income**
- **Mortgage / Rent**
- **Utilities**
- **Groceries**
- **Dining**
- **Fuel / Transportation**
- **Insurance**
- **Subscriptions**
- **Debt Payments**
- **Kids / School**
- **Medical**
- **Home Maintenance**
- **Pets**
- **Savings / Investing**
- **One-Off / Review**

## Monthly Budget Output Matrix
1. **Net Income**: Total credit deposits matching Income category.
2. **Fixed Obligations**: Recurring or contract expenses (Rent, Utilities, Insurance, Debt Minimums).
3. **Variable Spending**: Non-fixed category expenses (Groceries, Dining, Fuel).
4. **Debt Minimums**: Total interest & base obligations.
5. **Savings / Investing**: Allocations to investments/savings accounts.
6. **Free Cash Flow**: `Net Income - Fixed Obligations - Variable Spending - Savings`.
7. **Variance**: Actual vs target budget comparison per category.
