from __future__ import annotations

import logging
from typing import Optional

from app.database.session import get_session
from app.services.analytics_service import analytics_service

logger = logging.getLogger(__name__)


def register_tools(mcp) -> None:
    """Register analytics-related MCP tools."""

    @mcp.tool()
    async def monthly_summary(month: int, year: int) -> dict:
        """
        Get a financial summary for a specific month.

        Args:
            month: Month number (1-12)
            year: Year (e.g. 2024)

        Returns total income, expenses, savings, and transaction count.
        """
        async with get_session() as session:
            return await analytics_service.monthly_summary(session, month, year)

    @mcp.tool()
    async def category_breakdown(start_date: str, end_date: str) -> dict:
        """
        Get expense breakdown by category for a date range.

        Args:
            start_date: Start date in ISO format (e.g. '2024-01-01')
            end_date: End date in ISO format (e.g. '2024-01-31')

        Returns per-category totals, counts, averages, and percentages.
        """
        async with get_session() as session:
            return await analytics_service.category_breakdown(session, start_date, end_date)

    @mcp.tool()
    async def top_spending_categories(
        limit: int = 5,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        """
        Get the top N spending categories.

        Args:
            limit: Number of top categories to return (default: 5)
            start_date: Start date in ISO format (optional, defaults to current month)
            end_date: End date in ISO format (optional, defaults to current month)

        Returns ranked list of categories by total spend.
        """
        async with get_session() as session:
            return await analytics_service.top_spending_categories(
                session, limit, start_date, end_date
            )

    @mcp.tool()
    async def spending_trend(months: int = 6) -> list[dict]:
        """
        Get spending trend data for the last N months.

        Args:
            months: Number of past months to include (default: 6)

        Returns monthly income, expenses, and savings for each period.
        """
        async with get_session() as session:
            return await analytics_service.spending_trend(session, months)

    @mcp.tool()
    async def merchant_analysis(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        """
        Analyze spending by merchant.

        Args:
            start_date: Start date in ISO format (optional, defaults to current month)
            end_date: End date in ISO format (optional, defaults to current month)

        Returns merchants ranked by total spend with transaction counts and averages.
        """
        async with get_session() as session:
            return await analytics_service.merchant_analysis(session, start_date, end_date)

    @mcp.tool()
    async def average_daily_spend(month: int, year: int) -> dict:
        """
        Calculate average daily spending for a given month.

        Args:
            month: Month number (1-12)
            year: Year (e.g. 2024)

        Returns average daily spend, highest/lowest spend days, and daily breakdown.
        """
        async with get_session() as session:
            return await analytics_service.average_daily_spend(session, month, year)

    @mcp.tool()
    async def income_vs_expense(month: int, year: int) -> dict:
        """
        Compare income vs expenses for a given month.

        Args:
            month: Month number (1-12)
            year: Year (e.g. 2024)

        Returns income, expenses, savings, savings rate, and deficit flag.
        """
        async with get_session() as session:
            return await analytics_service.income_vs_expense(session, month, year)
