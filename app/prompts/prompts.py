from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_prompts(mcp) -> None:
    """Register MCP prompts."""

    @mcp.prompt()
    def analyze_expenses() -> str:
        """
        Prompt to analyze current spending patterns and provide actionable insights.
        """
        return """You are a personal finance advisor analyzing the user's expense data.

Please perform a comprehensive analysis of the spending patterns including:

1. **Top Spending Categories**: Identify the top 5 categories by expenditure and their share of total spending.
2. **Budget Overruns**: Highlight any categories that have exceeded their set budgets, including the overspent amount and percentage.
3. **Savings Opportunities**: Suggest 3-5 specific areas where the user could reduce spending based on the data patterns.
4. **Unusual Spending**: Flag any transactions that appear abnormally high compared to the user's typical spending in that category.
5. **Merchant Insights**: Identify top merchants by spend and whether any are disproportionately high.
6. **Month-over-Month Changes**: Compare current month spending to previous months and highlight significant changes.
7. **Quick Wins**: Provide 2-3 immediate actionable steps the user can take to improve their financial health.

Use the available tools to gather data:
- Call `monthly_summary` for current month overview
- Call `top_spending_categories` for category rankings
- Call `category_breakdown` for detailed breakdown
- Call `get_over_budget_alerts` for budget warnings
- Call `merchant_analysis` for merchant insights
- Call `spending_trend` with months=3 for trend analysis

Present the findings in a clear, structured format with specific numbers and percentages.
Be empathetic but direct with recommendations."""

    @mcp.prompt()
    def monthly_review(month: int, year: int) -> str:
        """
        Prompt for a complete monthly financial review.

        Args:
            month: Month number (1-12)
            year: Year (e.g. 2024)
        """
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        month_name = month_names[month - 1] if 1 <= month <= 12 else f"Month {month}"

        return f"""You are a personal finance advisor preparing a comprehensive financial review for {month_name} {year}.

Please generate a complete monthly financial report with the following sections:

## 1. Executive Summary
- Total income received
- Total expenses incurred
- Net savings / deficit for the month
- Savings rate percentage
- Comparison to the previous month

## 2. Income Analysis
- All income sources and amounts
- Total income for the month

## 3. Expense Breakdown
- Expenses grouped by category with totals and percentages
- Top 5 largest individual transactions
- Daily average spending

## 4. Budget Performance
- Budget vs actual for each category with budgets set
- Categories over budget (with overspend amounts)
- Categories well within budget (savings opportunities)
- Overall budget utilization percentage

## 5. Merchant Analysis
- Top 10 merchants by total spend
- Most frequent merchants

## 6. Insights & Recommendations
- Key financial wins for the month
- Areas requiring immediate attention
- Specific recommendations for next month
- Savings goal suggestions

Use these tools to gather the data:
- `monthly_summary(month={month}, year={year})` for overview
- `income_vs_expense(month={month}, year={year})` for income/expense comparison
- `category_breakdown(start_date="{year}-{month:02d}-01", end_date="{year}-{month:02d}-31")` for category details
- `get_budget_status(month={month}, year={year})` for budget performance
- `average_daily_spend(month={month}, year={year})` for daily averages
- `merchant_analysis()` for merchant insights
- `search_transactions(start_date="{year}-{month:02d}-01", end_date="{year}-{month:02d}-31")` for transaction list

Format the report professionally with clear sections, tables where appropriate, and specific actionable insights."""

    @mcp.prompt()
    def budget_advisor() -> str:
        """
        Prompt for personalized budgeting advice based on spending history.
        """
        return """You are an expert financial advisor helping the user create and optimize their budget.

Based on the user's spending history and current financial patterns, please provide:

## Budget Health Assessment
1. Review current budgets using `get_budget_status` and `get_over_budget_alerts`
2. Analyze 3-month spending trends using `spending_trend(months=3)`
3. Identify categories without budgets that should have them
4. Assess the realism of current budget allocations

## Personalized Budget Recommendations

### The 50/30/20 Rule Analysis
Calculate how the user's spending aligns with:
- **50% Needs**: Housing, food, transport, utilities, healthcare
- **30% Wants**: Entertainment, dining out, shopping, subscriptions
- **20% Savings**: Emergency fund, investments, debt repayment

### Category-Specific Recommendations
For each major spending category:
- Current monthly average spend
- Recommended budget range
- Potential savings if optimized
- Specific tips for that category

### Budget Optimization Plan
1. **Immediate** (This month): Quick adjustments to overspent categories
2. **Short-term** (Next 3 months): Gradual budget refinements
3. **Long-term** (6+ months): Financial goals and milestones

### Savings Goals
Based on income and expenses, suggest:
- Emergency fund target (3-6 months of expenses)
- Monthly savings target
- Investment contribution recommendation

Use these tools for analysis:
- `spending_trend(months=6)` for historical trends
- `top_spending_categories(limit=10)` for spending priorities
- `get_over_budget_alerts()` for current budget issues
- `list_budgets()` for existing budget setup
- `list_categories()` for category overview

Provide specific, actionable numbers and percentages. Be encouraging and realistic about financial improvement."""
