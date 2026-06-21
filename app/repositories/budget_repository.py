from __future__ import annotations

import uuid
import datetime
from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Budget


class BudgetRepository:
    """Repository for Budget database operations."""

    async def create(self, session: AsyncSession, data: dict) -> Budget:
        """Create a new budget."""
        budget = Budget(**data)
        if not budget.id:
            budget.id = str(uuid.uuid4())
        session.add(budget)
        await session.flush()
        await session.refresh(budget, attribute_names=["category"])
        return budget

    async def get_by_id(self, session: AsyncSession, id: str) -> Optional[Budget]:
        """Get a budget by ID."""
        stmt = (
            select(Budget)
            .options(selectinload(Budget.category))
            .where(Budget.id == id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_category_month(
        self,
        session: AsyncSession,
        category_id: str,
        month: int,
        year: int,
    ) -> Optional[Budget]:
        """Get a budget for a specific category, month, and year."""
        stmt = (
            select(Budget)
            .options(selectinload(Budget.category))
            .where(
                and_(
                    Budget.category_id == category_id,
                    Budget.month == month,
                    Budget.year == year,
                )
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self, session: AsyncSession, id: str, data: dict
    ) -> Optional[Budget]:
        """Update a budget by ID."""
        budget = await self.get_by_id(session, id)
        if not budget:
            return None

        for key, value in data.items():
            if hasattr(budget, key) and value is not None:
                setattr(budget, key, value)

        budget.updated_at = datetime.datetime.utcnow()
        session.add(budget)
        await session.flush()
        await session.refresh(budget, attribute_names=["category"])
        return budget

    async def delete(self, session: AsyncSession, id: str) -> bool:
        """Delete a budget by ID."""
        budget = await self.get_by_id(session, id)
        if not budget:
            return False
        await session.delete(budget)
        await session.flush()
        return True

    async def list_all(self, session: AsyncSession) -> List[Budget]:
        """List all budgets."""
        stmt = select(Budget).options(selectinload(Budget.category))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_current_month_budgets(self, session: AsyncSession) -> List[Budget]:
        """Get budgets for the current month."""
        now = datetime.datetime.utcnow()
        stmt = (
            select(Budget)
            .options(selectinload(Budget.category))
            .where(
                and_(
                    Budget.month == now.month,
                    Budget.year == now.year,
                )
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_month_year(
        self, session: AsyncSession, month: int, year: int
    ) -> List[Budget]:
        """Get all budgets for a specific month and year."""
        stmt = (
            select(Budget)
            .options(selectinload(Budget.category))
            .where(
                and_(
                    Budget.month == month,
                    Budget.year == year,
                )
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


budget_repository = BudgetRepository()
