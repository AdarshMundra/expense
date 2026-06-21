from __future__ import annotations

import uuid
import datetime
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Category, Subcategory


class CategoryRepository:
    """Repository for Category and Subcategory database operations."""

    async def create(self, session: AsyncSession, data: dict) -> Category:
        """Create a new category."""
        category = Category(**data)
        if not category.id:
            category.id = str(uuid.uuid4())
        session.add(category)
        await session.flush()
        await session.refresh(category, attribute_names=["subcategories"])
        return category

    async def get_by_id(self, session: AsyncSession, id: str) -> Optional[Category]:
        """Get a category by ID."""
        stmt = (
            select(Category)
            .options(selectinload(Category.subcategories))
            .where(Category.id == id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, session: AsyncSession, name: str) -> Optional[Category]:
        """Get a category by name (case-insensitive)."""
        stmt = (
            select(Category)
            .options(selectinload(Category.subcategories))
            .where(Category.name.ilike(name))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self, session: AsyncSession, id: str, data: dict
    ) -> Optional[Category]:
        """Update a category by ID."""
        category = await self.get_by_id(session, id)
        if not category:
            return None

        for key, value in data.items():
            if hasattr(category, key) and value is not None:
                setattr(category, key, value)

        category.updated_at = datetime.datetime.utcnow()
        session.add(category)
        await session.flush()
        await session.refresh(category, attribute_names=["subcategories"])
        return category

    async def delete(self, session: AsyncSession, id: str) -> bool:
        """Delete a category by ID."""
        category = await self.get_by_id(session, id)
        if not category:
            return False
        await session.delete(category)
        await session.flush()
        return True

    async def list_all(self, session: AsyncSession) -> List[Category]:
        """List all categories with their subcategories."""
        stmt = select(Category).options(selectinload(Category.subcategories))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_subcategory(
        self, session: AsyncSession, data: dict
    ) -> Subcategory:
        """Create a new subcategory."""
        subcategory = Subcategory(**data)
        if not subcategory.id:
            subcategory.id = str(uuid.uuid4())
        session.add(subcategory)
        await session.flush()
        return subcategory

    async def get_subcategory_by_name(
        self, session: AsyncSession, category_id: str, name: str
    ) -> Optional[Subcategory]:
        """Get a subcategory by category_id and name (case-insensitive)."""
        stmt = select(Subcategory).where(
            Subcategory.category_id == category_id,
            Subcategory.name.ilike(name),
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_subcategory_by_id(
        self, session: AsyncSession, id: str
    ) -> Optional[Subcategory]:
        """Get a subcategory by ID."""
        stmt = select(Subcategory).where(Subcategory.id == id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_subcategories(
        self, session: AsyncSession, category_id: str
    ) -> List[Subcategory]:
        """List all subcategories for a given category."""
        stmt = select(Subcategory).where(Subcategory.category_id == category_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())


category_repository = CategoryRepository()
