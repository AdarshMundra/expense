from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.schemas import CategoryCreate, SubcategoryCreate
from app.services.category_service import category_service


class TestCreateCategory:
    async def test_create_basic_category(self, async_session: AsyncSession):
        """Test creating a new category."""
        data = CategoryCreate(name="TestCategory", icon="🧪", color="#123456")
        result = await category_service.create_category(async_session, data)
        await async_session.commit()

        assert result["status"] == "success"
        assert result["category"]["name"] == "TestCategory"
        assert result["category"]["icon"] == "🧪"
        assert result["category"]["color"] == "#123456"
        assert "id" in result["category"]

    async def test_create_category_with_budget_limit(self, async_session: AsyncSession):
        """Test creating a category with a budget limit."""
        data = CategoryCreate(name="BudgetCat", budget_limit=5000.0)
        result = await category_service.create_category(async_session, data)
        await async_session.commit()

        assert result["status"] == "success"
        assert result["category"]["budget_limit"] == 5000.0

    async def test_create_duplicate_category_fails(self, async_session: AsyncSession):
        """Test that creating a duplicate category name returns an error."""
        data = CategoryCreate(name="UniqueCategory")
        first = await category_service.create_category(async_session, data)
        await async_session.commit()
        assert first["status"] == "success"

        duplicate = await category_service.create_category(async_session, data)
        assert duplicate["status"] == "error"
        assert "already exists" in duplicate["message"].lower()

    async def test_create_category_minimal(self, async_session: AsyncSession):
        """Test creating a category with only a name."""
        data = CategoryCreate(name="MinimalCat")
        result = await category_service.create_category(async_session, data)
        await async_session.commit()

        assert result["status"] == "success"
        assert result["category"]["name"] == "MinimalCat"
        assert result["category"]["icon"] is None
        assert result["category"]["color"] is None


class TestListCategories:
    async def test_list_categories_includes_seeded_defaults(self, async_session: AsyncSession):
        """Test that seeded default categories are present."""
        categories = await category_service.list_categories(async_session)

        assert isinstance(categories, list)
        assert len(categories) > 0

        names = [c["name"] for c in categories]
        assert "Food" in names
        assert "Transport" in names
        assert "Shopping" in names

    async def test_list_categories_includes_subcategories(self, async_session: AsyncSession):
        """Test that categories include their subcategories."""
        categories = await category_service.list_categories(async_session)

        food_cat = next((c for c in categories if c["name"] == "Food"), None)
        assert food_cat is not None
        assert "subcategories" in food_cat
        assert isinstance(food_cat["subcategories"], list)

        sub_names = [s["name"] for s in food_cat["subcategories"]]
        assert "Restaurant" in sub_names
        assert "Groceries" in sub_names
        assert "Delivery" in sub_names

    async def test_list_categories_returns_new_category(self, async_session: AsyncSession):
        """Test that a newly created category appears in list."""
        data = CategoryCreate(name="NewListedCat")
        await category_service.create_category(async_session, data)
        await async_session.commit()

        categories = await category_service.list_categories(async_session)
        names = [c["name"] for c in categories]
        assert "NewListedCat" in names


class TestCreateSubcategory:
    async def test_create_subcategory_under_existing_category(self, async_session: AsyncSession):
        """Test creating a subcategory under an existing category."""
        categories = await category_service.list_categories(async_session)
        transport_cat = next((c for c in categories if c["name"] == "Transport"), None)
        assert transport_cat is not None

        data = SubcategoryCreate(category_id=transport_cat["id"], name="Metro")
        result = await category_service.create_subcategory(async_session, data)
        await async_session.commit()

        assert result["status"] == "success"
        assert result["subcategory"]["name"] == "Metro"
        assert result["subcategory"]["category_id"] == transport_cat["id"]

    async def test_create_duplicate_subcategory_fails(self, async_session: AsyncSession):
        """Test that duplicate subcategory name within same category fails."""
        categories = await category_service.list_categories(async_session)
        food_cat = next((c for c in categories if c["name"] == "Food"), None)
        assert food_cat is not None

        data = SubcategoryCreate(category_id=food_cat["id"], name="FastFood")
        first = await category_service.create_subcategory(async_session, data)
        await async_session.commit()
        assert first["status"] == "success"

        duplicate = await category_service.create_subcategory(async_session, data)
        assert duplicate["status"] == "error"

    async def test_create_subcategory_invalid_category(self, async_session: AsyncSession):
        """Test creating a subcategory with a non-existent parent category fails."""
        data = SubcategoryCreate(category_id="nonexistent-category-id", name="TestSub")
        result = await category_service.create_subcategory(async_session, data)
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    async def test_list_subcategories(self, async_session: AsyncSession):
        """Test listing subcategories for a category."""
        categories = await category_service.list_categories(async_session)
        food_cat = next((c for c in categories if c["name"] == "Food"), None)
        assert food_cat is not None

        subcategories = await category_service.list_subcategories(
            async_session, food_cat["id"]
        )
        assert isinstance(subcategories, list)
        assert len(subcategories) >= 3  # Restaurant, Groceries, Delivery


class TestUpdateCategory:
    async def test_update_category_name(self, async_session: AsyncSession):
        """Test updating a category's name."""
        data = CategoryCreate(name="OldName")
        create_result = await category_service.create_category(async_session, data)
        await async_session.commit()
        cat_id = create_result["category"]["id"]

        update_result = await category_service.update_category(
            async_session, cat_id, {"name": "NewName"}
        )
        await async_session.commit()

        assert update_result["status"] == "success"
        assert update_result["category"]["name"] == "NewName"

    async def test_delete_category(self, async_session: AsyncSession):
        """Test deleting a category."""
        data = CategoryCreate(name="ToDelete")
        create_result = await category_service.create_category(async_session, data)
        await async_session.commit()
        cat_id = create_result["category"]["id"]

        delete_result = await category_service.delete_category(async_session, cat_id)
        await async_session.commit()

        assert delete_result["status"] == "success"

        # Verify it's removed
        categories = await category_service.list_categories(async_session)
        names = [c["name"] for c in categories]
        assert "ToDelete" not in names
