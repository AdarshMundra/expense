from __future__ import annotations

import logging
from typing import Optional

from app.database.session import get_session
from app.schemas.schemas import CategoryCreate, SubcategoryCreate
from app.services.category_service import category_service

logger = logging.getLogger(__name__)


def register_tools(mcp) -> None:
    """Register category-related MCP tools."""

    @mcp.tool()
    async def create_category(
        name: str,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        budget_limit: Optional[float] = None,
    ) -> dict:
        """
        Create a new expense category.

        Args:
            name: Category name (must be unique)
            icon: Emoji or icon identifier (e.g. '🍽️')
            color: Hex color code (e.g. '#FF6B6B')
            budget_limit: Optional monthly budget limit for this category
        """
        data = CategoryCreate(name=name, icon=icon, color=color, budget_limit=budget_limit)
        async with get_session() as session:
            return await category_service.create_category(session, data)

    @mcp.tool()
    async def update_category(
        category_id: str,
        name: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        budget_limit: Optional[float] = None,
    ) -> dict:
        """
        Update an existing category.

        Args:
            category_id: UUID of the category to update
            name: New category name
            icon: New icon
            color: New color
            budget_limit: New budget limit
        """
        update_data: dict = {}
        if name is not None:
            update_data["name"] = name
        if icon is not None:
            update_data["icon"] = icon
        if color is not None:
            update_data["color"] = color
        if budget_limit is not None:
            update_data["budget_limit"] = budget_limit

        async with get_session() as session:
            return await category_service.update_category(session, category_id, update_data)

    @mcp.tool()
    async def delete_category(category_id: str) -> dict:
        """
        Delete a category by ID.

        Args:
            category_id: UUID of the category to delete
        """
        async with get_session() as session:
            return await category_service.delete_category(session, category_id)

    @mcp.tool()
    async def list_categories() -> list[dict]:
        """
        List all expense categories with their subcategories.

        Returns a list of categories including id, name, icon, color,
        budget_limit, and associated subcategories.
        """
        async with get_session() as session:
            return await category_service.list_categories(session)

    @mcp.tool()
    async def create_subcategory(category_id: str, name: str) -> dict:
        """
        Create a subcategory under an existing category.

        Args:
            category_id: UUID of the parent category
            name: Subcategory name (must be unique within the category)
        """
        data = SubcategoryCreate(category_id=category_id, name=name)
        async with get_session() as session:
            return await category_service.create_subcategory(session, data)

    @mcp.tool()
    async def list_subcategories(category_id: str) -> list[dict]:
        """
        List all subcategories for a specific category.

        Args:
            category_id: UUID of the parent category
        """
        async with get_session() as session:
            return await category_service.list_subcategories(session, category_id)
