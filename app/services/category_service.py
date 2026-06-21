from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.category_repository import category_repository
from app.schemas.schemas import CategoryCreate, SubcategoryCreate

logger = logging.getLogger(__name__)

# Default categories to seed
DEFAULT_CATEGORIES = [
    {
        "name": "Food",
        "icon": "🍽️",
        "color": "#FF6B6B",
        "subcategories": ["Restaurant", "Groceries", "Delivery"],
    },
    {
        "name": "Transport",
        "icon": "🚗",
        "color": "#4ECDC4",
        "subcategories": ["Taxi", "Fuel", "Train"],
    },
    {
        "name": "Shopping",
        "icon": "🛒",
        "color": "#45B7D1",
        "subcategories": ["Clothing", "Electronics", "Online"],
    },
    {
        "name": "Entertainment",
        "icon": "🎬",
        "color": "#96CEB4",
        "subcategories": ["Movies", "Streaming", "Events"],
    },
    {
        "name": "Bills",
        "icon": "📄",
        "color": "#FFEAA7",
        "subcategories": ["Electricity", "Internet", "Rent"],
    },
    {
        "name": "Healthcare",
        "icon": "🏥",
        "color": "#DDA0DD",
        "subcategories": ["Doctor", "Pharmacy", "Insurance"],
    },
    {
        "name": "Other",
        "icon": "📦",
        "color": "#B0C4DE",
        "subcategories": [],
    },
    {
        "name": "Miscellaneous",
        "icon": "🗂️",
        "color": "#A9A9A9",
        "subcategories": [],
    },
]


class CategoryService:
    """Business logic service for categories and subcategories."""

    async def create_category(
        self, session: AsyncSession, data: CategoryCreate
    ) -> dict:
        """Create a new category."""
        try:
            # Check for duplicate name
            existing = await category_repository.get_by_name(session, data.name)
            if existing:
                return {
                    "status": "error",
                    "message": f"Category '{data.name}' already exists.",
                }

            category = await category_repository.create(
                session,
                {
                    "name": data.name,
                    "icon": data.icon,
                    "color": data.color,
                    "budget_limit": data.budget_limit,
                },
            )

            return {
                "status": "success",
                "message": f"Category '{data.name}' created.",
                "category": {
                    **category.to_dict(),
                    "subcategories": [],
                },
            }
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return {"status": "error", "message": str(e)}

    async def update_category(
        self, session: AsyncSession, id: str, data: dict
    ) -> dict:
        """Update a category by ID."""
        try:
            category = await category_repository.update(session, id, data)
            if not category:
                return {"status": "error", "message": f"Category {id} not found."}

            subcategories = [s.to_dict() for s in (category.subcategories or [])]
            return {
                "status": "success",
                "message": "Category updated.",
                "category": {
                    **category.to_dict(),
                    "subcategories": subcategories,
                },
            }
        except Exception as e:
            logger.error(f"Error updating category: {e}")
            return {"status": "error", "message": str(e)}

    async def delete_category(self, session: AsyncSession, id: str) -> dict:
        """Delete a category by ID."""
        try:
            deleted = await category_repository.delete(session, id)
            if not deleted:
                return {"status": "error", "message": f"Category {id} not found."}
            return {
                "status": "success",
                "message": f"Category {id} deleted successfully.",
            }
        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            return {"status": "error", "message": str(e)}

    async def list_categories(self, session: AsyncSession) -> list[dict]:
        """List all categories with subcategories."""
        try:
            categories = await category_repository.list_all(session)
            result = []
            for cat in categories:
                subcategories = [s.to_dict() for s in (cat.subcategories or [])]
                result.append({
                    **cat.to_dict(),
                    "subcategories": subcategories,
                })
            return result
        except Exception as e:
            logger.error(f"Error listing categories: {e}")
            return []

    async def create_subcategory(
        self, session: AsyncSession, data: SubcategoryCreate
    ) -> dict:
        """Create a new subcategory."""
        try:
            # Verify parent category exists
            category = await category_repository.get_by_id(session, data.category_id)
            if not category:
                return {
                    "status": "error",
                    "message": f"Category {data.category_id} not found.",
                }

            # Check for duplicate subcategory name within category
            existing = await category_repository.get_subcategory_by_name(
                session, data.category_id, data.name
            )
            if existing:
                return {
                    "status": "error",
                    "message": f"Subcategory '{data.name}' already exists in category '{category.name}'.",
                }

            subcategory = await category_repository.create_subcategory(
                session,
                {
                    "category_id": data.category_id,
                    "name": data.name,
                },
            )

            return {
                "status": "success",
                "message": f"Subcategory '{data.name}' created under '{category.name}'.",
                "subcategory": subcategory.to_dict(),
            }
        except Exception as e:
            logger.error(f"Error creating subcategory: {e}")
            return {"status": "error", "message": str(e)}

    async def list_subcategories(
        self, session: AsyncSession, category_id: str
    ) -> list[dict]:
        """List subcategories for a given category."""
        try:
            subcategories = await category_repository.list_subcategories(session, category_id)
            return [s.to_dict() for s in subcategories]
        except Exception as e:
            logger.error(f"Error listing subcategories: {e}")
            return []

    async def seed_default_categories(self, session: AsyncSession) -> None:
        """Seed default categories and subcategories if they don't exist."""
        try:
            for cat_data in DEFAULT_CATEGORIES:
                subcategory_names = cat_data.get("subcategories", [])
                existing = await category_repository.get_by_name(session, cat_data["name"])

                if not existing:
                    cat_fields = {k: v for k, v in cat_data.items() if k != "subcategories"}
                    category = await category_repository.create(session, cat_fields)
                    logger.info(f"Seeded category: {category.name}")
                else:
                    category = existing

                for subcat_name in subcategory_names:
                    existing_sub = await category_repository.get_subcategory_by_name(
                        session, category.id, subcat_name
                    )
                    if not existing_sub:
                        await category_repository.create_subcategory(
                            session,
                            {"category_id": category.id, "name": subcat_name},
                        )
                        logger.info(f"Seeded subcategory: {subcat_name} under {category.name}")

        except Exception as e:
            logger.error(f"Error seeding default categories: {e}")
            raise


category_service = CategoryService()
