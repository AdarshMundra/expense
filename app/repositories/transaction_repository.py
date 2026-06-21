from __future__ import annotations

import json
import datetime
import uuid
from typing import Optional, List

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Transaction, Category, Subcategory


class TransactionRepository:
    """Repository for Transaction database operations."""

    async def create(self, session: AsyncSession, data: dict) -> Transaction:
        """Create a new transaction."""
        # Serialize tags if present
        if "tags" in data and isinstance(data["tags"], list):
            data["tags"] = json.dumps(data["tags"])

        transaction = Transaction(**data)
        if not transaction.id:
            transaction.id = str(uuid.uuid4())
        session.add(transaction)
        await session.flush()
        await session.refresh(transaction, attribute_names=["category_rel", "subcategory_rel"])
        return transaction

    async def get_by_id(self, session: AsyncSession, id: str) -> Optional[Transaction]:
        """Get a transaction by ID."""
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.category_rel),
                selectinload(Transaction.subcategory_rel),
            )
            .where(Transaction.id == id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, session: AsyncSession, id: str, data: dict) -> Optional[Transaction]:
        """Update a transaction by ID."""
        transaction = await self.get_by_id(session, id)
        if not transaction:
            return None

        if "tags" in data and isinstance(data["tags"], list):
            data["tags"] = json.dumps(data["tags"])

        for key, value in data.items():
            if hasattr(transaction, key) and value is not None:
                setattr(transaction, key, value)

        transaction.updated_at = datetime.datetime.utcnow()
        session.add(transaction)
        await session.flush()
        await session.refresh(transaction, attribute_names=["category_rel", "subcategory_rel"])
        return transaction

    async def delete(self, session: AsyncSession, id: str) -> bool:
        """Delete a transaction by ID."""
        transaction = await self.get_by_id(session, id)
        if not transaction:
            return False
        await session.delete(transaction)
        await session.flush()
        return True

    async def search(self, session: AsyncSession, filters: dict) -> List[Transaction]:
        """Search transactions with dynamic filters."""
        stmt = select(Transaction).options(
            selectinload(Transaction.category_rel),
            selectinload(Transaction.subcategory_rel),
        )

        conditions = []

        if filters.get("start_date"):
            try:
                start_dt = datetime.datetime.fromisoformat(filters["start_date"])
                conditions.append(Transaction.timestamp >= start_dt)
            except ValueError:
                pass

        if filters.get("end_date"):
            try:
                end_dt = datetime.datetime.fromisoformat(filters["end_date"])
                conditions.append(Transaction.timestamp <= end_dt)
            except ValueError:
                pass

        if filters.get("category_id"):
            conditions.append(Transaction.category_id == filters["category_id"])

        if filters.get("subcategory_id"):
            conditions.append(Transaction.subcategory_id == filters["subcategory_id"])

        if filters.get("merchant"):
            conditions.append(
                Transaction.merchant.ilike(f"%{filters['merchant']}%")
            )

        if filters.get("min_amount") is not None:
            conditions.append(Transaction.amount >= filters["min_amount"])

        if filters.get("max_amount") is not None:
            conditions.append(Transaction.amount <= filters["max_amount"])

        if filters.get("transaction_type"):
            conditions.append(Transaction.transaction_type == filters["transaction_type"])

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(Transaction.timestamp.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_month(
        self, session: AsyncSession, month: int, year: int
    ) -> List[Transaction]:
        """Get all transactions for a specific month and year."""
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.category_rel),
                selectinload(Transaction.subcategory_rel),
            )
            .where(
                and_(
                    Transaction.timestamp >= datetime.datetime(year, month, 1),
                    Transaction.timestamp
                    < datetime.datetime(year, month + 1, 1)
                    if month < 12
                    else Transaction.timestamp < datetime.datetime(year + 1, 1, 1),
                )
            )
            .order_by(Transaction.timestamp.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent(
        self, session: AsyncSession, limit: int = 20
    ) -> List[Transaction]:
        """Get the most recent transactions."""
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.category_rel),
                selectinload(Transaction.subcategory_rel),
            )
            .order_by(Transaction.timestamp.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_in_range(
        self,
        session: AsyncSession,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> List[Transaction]:
        """Get all transactions within a date range."""
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.category_rel),
                selectinload(Transaction.subcategory_rel),
            )
            .where(
                and_(
                    Transaction.timestamp >= start_date,
                    Transaction.timestamp <= end_date,
                )
            )
            .order_by(Transaction.timestamp.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


transaction_repository = TransactionRepository()
