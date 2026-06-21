from __future__ import annotations

import datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.schemas import BudgetCreate, TransactionCreate
from app.services.budget_service import budget_service
from app.services.category_service import category_service
from app.services.transaction_service import transaction_service


async def _get_food_category_id(async_session: AsyncSession) -> str:
    """Helper to get the Food category ID."""
    categories = await category_service.list_categories(async_session)
    food_cat = next((c for c in categories if c["name"] == "Food"), None)
    assert food_cat is not None, "Food category should be seeded"
    return food_cat["id"]


async def _get_transport_category_id(async_session: AsyncSession) -> str:
    """Helper to get the Transport category ID."""
    categories = await category_service.list_categories(async_session)
    transport_cat = next((c for c in categories if c["name"] == "Transport"), None)
    assert transport_cat is not None, "Transport category should be seeded"
    return transport_cat["id"]


class TestSetBudget:
    async def test_create_new_budget(self, async_session: AsyncSession):
        """Test creating a new budget."""
        food_id = await _get_food_category_id(async_session)
        now = datetime.datetime.utcnow()

        data = BudgetCreate(
            category_id=food_id,
            month=now.month,
            year=now.year,
            allocated_amount=5000.0,
        )
        result = await budget_service.set_budget(async_session, data)
        await async_session.commit()

        assert result["status"] == "success"
        assert result["action"] == "created"
        assert result["budget"]["allocated_amount"] == 5000.0
        assert result["budget"]["category_id"] == food_id

    async def test_update_existing_budget(self, async_session: AsyncSession):
        """Test that setting a budget for same category/month/year updates it."""
        food_id = await _get_food_category_id(async_session)
        now = datetime.datetime.utcnow()

        data = BudgetCreate(
            category_id=food_id,
            month=now.month,
            year=now.year,
            allocated_amount=3000.0,
        )
        first = await budget_service.set_budget(async_session, data)
        await async_session.commit()
        assert first["action"] == "created"

        data2 = BudgetCreate(
            category_id=food_id,
            month=now.month,
            year=now.year,
            allocated_amount=6000.0,
        )
        second = await budget_service.set_budget(async_session, data2)
        await async_session.commit()

        assert second["status"] == "success"
        assert second["action"] == "updated"
        assert second["budget"]["allocated_amount"] == 6000.0

    async def test_budget_for_different_months(self, async_session: AsyncSession):
        """Test creating budgets for different months."""
        food_id = await _get_food_category_id(async_session)

        result1 = await budget_service.set_budget(
            async_session,
            BudgetCreate(category_id=food_id, month=1, year=2024, allocated_amount=3000.0),
        )
        result2 = await budget_service.set_budget(
            async_session,
            BudgetCreate(category_id=food_id, month=2, year=2024, allocated_amount=4000.0),
        )
        await async_session.commit()

        assert result1["status"] == "success"
        assert result2["status"] == "success"
        assert result1["budget"]["id"] != result2["budget"]["id"]


class TestGetBudgetStatus:
    async def test_budget_status_with_no_spending(self, async_session: AsyncSession):
        """Test budget status when there are no transactions."""
        food_id = await _get_food_category_id(async_session)
        now = datetime.datetime.utcnow()

        await budget_service.set_budget(
            async_session,
            BudgetCreate(
                category_id=food_id,
                month=now.month,
                year=now.year,
                allocated_amount=5000.0,
            ),
        )
        await async_session.commit()

        status = await budget_service.get_budget_status(
            async_session, now.month, now.year
        )

        assert "budgets" in status
        assert "Food" in status["budgets"]
        food_status = status["budgets"]["Food"]
        assert food_status["allocated"] == 5000.0
        assert food_status["spent"] == 0.0
        assert food_status["remaining"] == 5000.0
        assert food_status["percentage_used"] == 0.0
        assert not food_status["is_over_budget"]

    async def test_budget_status_with_spending(self, async_session: AsyncSession):
        """Test budget status reflects actual spending."""
        food_id = await _get_food_category_id(async_session)
        now = datetime.datetime.utcnow()

        await budget_service.set_budget(
            async_session,
            BudgetCreate(
                category_id=food_id,
                month=now.month,
                year=now.year,
                allocated_amount=2000.0,
            ),
        )

        # Add food expense
        await transaction_service.add_transaction(
            async_session,
            TransactionCreate(
                amount=500.0,
                transaction_type="expense",
                category="Food",
            ),
        )
        await async_session.commit()

        status = await budget_service.get_budget_status(
            async_session, now.month, now.year
        )

        assert "Food" in status["budgets"]
        food_status = status["budgets"]["Food"]
        assert food_status["spent"] >= 500.0
        assert food_status["remaining"] <= 1500.0
        assert not food_status["is_over_budget"]

    async def test_budget_status_over_budget(self, async_session: AsyncSession):
        """Test that over-budget status is detected correctly."""
        food_id = await _get_food_category_id(async_session)
        now = datetime.datetime.utcnow()

        await budget_service.set_budget(
            async_session,
            BudgetCreate(
                category_id=food_id,
                month=now.month,
                year=now.year,
                allocated_amount=100.0,  # Set a very low budget
            ),
        )

        # Add expense exceeding the budget
        await transaction_service.add_transaction(
            async_session,
            TransactionCreate(
                amount=500.0,
                transaction_type="expense",
                category="Food",
            ),
        )
        await async_session.commit()

        status = await budget_service.get_budget_status(
            async_session, now.month, now.year
        )

        assert "Food" in status["budgets"]
        food_status = status["budgets"]["Food"]
        assert food_status["is_over_budget"]
        assert food_status["status"] == "over_budget"

    async def test_budget_status_no_budgets(self, async_session: AsyncSession):
        """Test budget status when no budgets are set."""
        status = await budget_service.get_budget_status(async_session, 1, 2020)

        assert "budgets" in status
        assert status["budgets"] == {}


class TestOverBudgetAlerts:
    async def test_no_alerts_when_within_budget(self, async_session: AsyncSession):
        """Test that no alerts are generated when spending is within budget."""
        food_id = await _get_food_category_id(async_session)
        now = datetime.datetime.utcnow()

        await budget_service.set_budget(
            async_session,
            BudgetCreate(
                category_id=food_id,
                month=now.month,
                year=now.year,
                allocated_amount=10000.0,
            ),
        )
        await async_session.commit()

        alerts = await budget_service.get_over_budget_alerts(async_session)
        # Food budget with no spending should not trigger an alert
        food_alerts = [a for a in alerts if a["category"] == "Food"]
        assert len(food_alerts) == 0

    async def test_alerts_when_over_budget(self, async_session: AsyncSession):
        """Test that alerts are triggered when spending exceeds budget."""
        food_id = await _get_food_category_id(async_session)
        now = datetime.datetime.utcnow()

        await budget_service.set_budget(
            async_session,
            BudgetCreate(
                category_id=food_id,
                month=now.month,
                year=now.year,
                allocated_amount=50.0,  # Very low budget
            ),
        )
        await transaction_service.add_transaction(
            async_session,
            TransactionCreate(
                amount=200.0,
                transaction_type="expense",
                category="Food",
            ),
        )
        await async_session.commit()

        alerts = await budget_service.get_over_budget_alerts(async_session)
        food_alerts = [a for a in alerts if a["category"] == "Food"]

        assert len(food_alerts) >= 1
        assert food_alerts[0]["alert_type"] == "over_budget"
        assert food_alerts[0]["overspend"] > 0

    async def test_warning_alert_at_80_percent(self, async_session: AsyncSession):
        """Test that a warning alert is triggered at 80% budget utilization."""
        transport_id = await _get_transport_category_id(async_session)
        now = datetime.datetime.utcnow()

        await budget_service.set_budget(
            async_session,
            BudgetCreate(
                category_id=transport_id,
                month=now.month,
                year=now.year,
                allocated_amount=1000.0,
            ),
        )
        # Spend exactly 85% of budget
        await transaction_service.add_transaction(
            async_session,
            TransactionCreate(
                amount=850.0,
                transaction_type="expense",
                category="Transport",
            ),
        )
        await async_session.commit()

        alerts = await budget_service.get_over_budget_alerts(async_session)
        transport_alerts = [a for a in alerts if a["category"] == "Transport"]

        assert len(transport_alerts) >= 1
        assert transport_alerts[0]["percentage_used"] >= 80


class TestListAndDeleteBudget:
    async def test_list_budgets(self, async_session: AsyncSession):
        """Test listing all budgets."""
        food_id = await _get_food_category_id(async_session)

        await budget_service.set_budget(
            async_session,
            BudgetCreate(category_id=food_id, month=3, year=2024, allocated_amount=4000.0),
        )
        await async_session.commit()

        budgets = await budget_service.list_budgets(async_session)
        assert isinstance(budgets, list)
        assert len(budgets) >= 1

    async def test_delete_budget(self, async_session: AsyncSession):
        """Test deleting a budget."""
        food_id = await _get_food_category_id(async_session)

        create_result = await budget_service.set_budget(
            async_session,
            BudgetCreate(category_id=food_id, month=6, year=2024, allocated_amount=3000.0),
        )
        await async_session.commit()

        budget_id = create_result["budget"]["id"]
        delete_result = await budget_service.delete_budget(async_session, budget_id)
        await async_session.commit()

        assert delete_result["status"] == "success"

    async def test_delete_nonexistent_budget(self, async_session: AsyncSession):
        """Test deleting a non-existent budget returns error."""
        result = await budget_service.delete_budget(async_session, "nonexistent-budget-id")
        assert result["status"] == "error"
