from __future__ import annotations

import logging

from app.database.session import get_session
from app.schemas.schemas import BudgetCreate
from app.services.budget_service import budget_service

logger = logging.getLogger(__name__)


def register_tools(mcp) -> None:
    """Register budget-related MCP tools."""

    @mcp.tool()
    async def set_budget(
        category_id: str,
        month: int,
        year: int,
        allocated_amount: float,
    ) -> dict:
        """
        Set or update a budget for a category in a specific month/year.
        If a budget already exists for the category/month/year, it will be updated.

        Args:
            category_id: UUID of the category
            month: Month number (1-12)
            year: Year (e.g. 2024)
            allocated_amount: Budget amount to allocate
        """
        data = BudgetCreate(
            category_id=category_id,
            month=month,
            year=year,
            allocated_amount=allocated_amount,
        )
        async with get_session() as session:
            return await budget_service.set_budget(session, data)

    @mcp.tool()
    async def get_budget_status(month: int, year: int) -> dict:
        """
        Get budget status for all categories in a given month.
        Shows allocated vs spent amounts and identifies over-budget categories.

        Args:
            month: Month number (1-12)
            year: Year (e.g. 2024)
        """
        async with get_session() as session:
            return await budget_service.get_budget_status(session, month, year)

    @mcp.tool()
    async def update_budget(budget_id: str, allocated_amount: float) -> dict:
        """
        Update the allocated amount for an existing budget.

        Args:
            budget_id: UUID of the budget to update
            allocated_amount: New allocated amount
        """
        async with get_session() as session:
            return await budget_service.update_budget(
                session, budget_id, {"allocated_amount": allocated_amount}
            )

    @mcp.tool()
    async def delete_budget(budget_id: str) -> dict:
        """
        Delete a budget by ID.

        Args:
            budget_id: UUID of the budget to delete
        """
        async with get_session() as session:
            return await budget_service.delete_budget(session, budget_id)

    @mcp.tool()
    async def list_budgets() -> list[dict]:
        """
        List all budgets with category names, allocated amounts, and periods.
        """
        async with get_session() as session:
            return await budget_service.list_budgets(session)

    @mcp.tool()
    async def get_over_budget_alerts() -> list[dict]:
        """
        Get alerts for categories that are over budget or approaching limits (≥80%)
        for the current month. Includes overspend amounts and alert severity.
        """
        async with get_session() as session:
            return await budget_service.get_over_budget_alerts(session)
