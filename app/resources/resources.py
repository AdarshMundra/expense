from __future__ import annotations

import datetime
import json
import logging

from app.database.session import get_session
from app.services.category_service import category_service
from app.services.budget_service import budget_service
from app.services.analytics_service import analytics_service
from app.repositories.transaction_repository import transaction_repository

logger = logging.getLogger(__name__)


def register_resources(mcp) -> None:
    """Register MCP resources."""

    @mcp.resource("expense://categories")
    async def get_categories() -> str:
        """
        List all expense categories with subcategories.
        Returns a JSON string of all categories.
        """
        async with get_session() as session:
            categories = await category_service.list_categories(session)
        return json.dumps(categories, indent=2, default=str)

    @mcp.resource("expense://budgets")
    async def get_budgets() -> str:
        """
        List all budgets with category names and allocated amounts.
        Returns a JSON string of all budgets.
        """
        async with get_session() as session:
            budgets = await budget_service.list_budgets(session)
        return json.dumps(budgets, indent=2, default=str)

    @mcp.resource("expense://monthly-summary")
    async def get_monthly_summary() -> str:
        """
        Get the financial summary for the current month.
        Returns a JSON string with income, expenses, savings, and transaction count.
        """
        now = datetime.datetime.utcnow()
        async with get_session() as session:
            summary = await analytics_service.monthly_summary(session, now.month, now.year)
        return json.dumps(summary, indent=2, default=str)

    @mcp.resource("expense://recent-transactions")
    async def get_recent_transactions() -> str:
        """
        Get the 20 most recent transactions.
        Returns a JSON string of recent transactions with full details.
        """
        async with get_session() as session:
            transactions = await transaction_repository.get_recent(session, limit=20)
            result = [t.to_dict() for t in transactions]
        return json.dumps(result, indent=2, default=str)
