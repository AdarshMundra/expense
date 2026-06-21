from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.schemas import TransactionCreate, TransactionUpdate, SearchFilters
from app.services.transaction_service import transaction_service, suggest_category


class TestAddTransaction:
    async def test_add_basic_expense(self, async_session: AsyncSession):
        """Test adding a basic expense transaction."""
        data = TransactionCreate(
            amount=150.0,
            transaction_type="expense",
            merchant="Swiggy",
            description="Dinner order",
        )
        result = await transaction_service.add_transaction(async_session, data)
        await async_session.commit()

        assert result["status"] == "success"
        assert "transaction_id" in result
        assert result["transaction"]["amount"] == 150.0
        assert result["transaction"]["merchant"] == "Swiggy"

    async def test_add_income_transaction(self, async_session: AsyncSession):
        """Test adding an income transaction."""
        data = TransactionCreate(
            amount=50000.0,
            transaction_type="income",
            description="Monthly salary",
            merchant="Employer Corp",
        )
        result = await transaction_service.add_transaction(async_session, data)
        await async_session.commit()

        assert result["status"] == "success"
        assert result["transaction"]["transaction_type"] == "income"
        assert result["transaction"]["amount"] == 50000.0

    async def test_add_transaction_with_explicit_category(self, async_session: AsyncSession):
        """Test adding a transaction with an explicit category."""
        data = TransactionCreate(
            amount=200.0,
            transaction_type="expense",
            category="Food",
            subcategory="Restaurant",
            description="Lunch",
        )
        result = await transaction_service.add_transaction(async_session, data)
        await async_session.commit()

        assert result["status"] == "success"
        assert result["transaction"]["category"] == "Food"
        assert result["transaction"]["subcategory"] == "Restaurant"

    async def test_add_transaction_auto_categorizes_swiggy(self, async_session: AsyncSession):
        """Test that Swiggy merchant is auto-categorized to Food/Delivery."""
        data = TransactionCreate(
            amount=120.0,
            merchant="Swiggy",
        )
        result = await transaction_service.add_transaction(async_session, data)
        await async_session.commit()

        assert result["status"] == "success"
        assert result["transaction"]["category"] == "Food"
        assert result["transaction"]["subcategory"] == "Delivery"

    async def test_add_transaction_auto_categorizes_uber(self, async_session: AsyncSession):
        """Test that Uber merchant is auto-categorized to Transport/Taxi."""
        data = TransactionCreate(
            amount=85.0,
            merchant="Uber",
        )
        result = await transaction_service.add_transaction(async_session, data)
        await async_session.commit()

        assert result["status"] == "success"
        assert result["transaction"]["category"] == "Transport"
        assert result["transaction"]["subcategory"] == "Taxi"

    async def test_add_transaction_with_tags(self, async_session: AsyncSession):
        """Test adding a transaction with tags."""
        data = TransactionCreate(
            amount=300.0,
            merchant="Amazon",
            tags=["online", "shopping", "household"],
        )
        result = await transaction_service.add_transaction(async_session, data)
        await async_session.commit()

        assert result["status"] == "success"
        assert isinstance(result["transaction"]["tags"], list)
        assert "online" in result["transaction"]["tags"]

    async def test_add_transaction_with_timestamp(self, async_session: AsyncSession):
        """Test adding a transaction with a specific timestamp."""
        data = TransactionCreate(
            amount=500.0,
            timestamp="2024-03-15T10:30:00",
        )
        result = await transaction_service.add_transaction(async_session, data)
        await async_session.commit()

        assert result["status"] == "success"
        assert "2024-03-15" in result["transaction"]["timestamp"]

    async def test_add_transaction_invalid_type(self, async_session: AsyncSession):
        """Test that invalid transaction_type raises a validation error."""
        with pytest.raises(Exception):
            TransactionCreate(amount=100.0, transaction_type="invalid_type")


class TestGetTransaction:
    async def test_get_existing_transaction(self, async_session: AsyncSession):
        """Test retrieving an existing transaction by ID."""
        data = TransactionCreate(amount=250.0, merchant="Netflix")
        create_result = await transaction_service.add_transaction(async_session, data)
        await async_session.commit()

        tx_id = create_result["transaction_id"]
        get_result = await transaction_service.get_transaction(async_session, tx_id)

        assert get_result["status"] == "success"
        assert get_result["transaction"]["id"] == tx_id
        assert get_result["transaction"]["amount"] == 250.0

    async def test_get_nonexistent_transaction(self, async_session: AsyncSession):
        """Test getting a transaction that doesn't exist returns error."""
        result = await transaction_service.get_transaction(
            async_session, "nonexistent-uuid-1234"
        )
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()


class TestUpdateTransaction:
    async def test_update_amount(self, async_session: AsyncSession):
        """Test updating a transaction's amount."""
        data = TransactionCreate(amount=100.0, merchant="Zomato")
        create_result = await transaction_service.add_transaction(async_session, data)
        await async_session.commit()

        tx_id = create_result["transaction_id"]
        update_data = TransactionUpdate(amount=200.0)
        update_result = await transaction_service.update_transaction(
            async_session, tx_id, update_data
        )
        await async_session.commit()

        assert update_result["status"] == "success"
        assert update_result["transaction"]["amount"] == 200.0

    async def test_update_description_and_notes(self, async_session: AsyncSession):
        """Test updating description and notes of a transaction."""
        data = TransactionCreate(amount=100.0)
        create_result = await transaction_service.add_transaction(async_session, data)
        await async_session.commit()

        tx_id = create_result["transaction_id"]
        update_data = TransactionUpdate(
            description="Updated description",
            notes="Updated notes",
        )
        update_result = await transaction_service.update_transaction(
            async_session, tx_id, update_data
        )
        await async_session.commit()

        assert update_result["status"] == "success"
        assert update_result["transaction"]["description"] == "Updated description"
        assert update_result["transaction"]["notes"] == "Updated notes"

    async def test_update_nonexistent_transaction(self, async_session: AsyncSession):
        """Test updating a non-existent transaction returns error."""
        update_data = TransactionUpdate(amount=500.0)
        result = await transaction_service.update_transaction(
            async_session, "fake-id-xyz", update_data
        )
        assert result["status"] == "error"


class TestDeleteTransaction:
    async def test_delete_existing_transaction(self, async_session: AsyncSession):
        """Test deleting an existing transaction."""
        data = TransactionCreate(amount=75.0, merchant="Spotify")
        create_result = await transaction_service.add_transaction(async_session, data)
        await async_session.commit()

        tx_id = create_result["transaction_id"]
        delete_result = await transaction_service.delete_transaction(async_session, tx_id)
        await async_session.commit()

        assert delete_result["status"] == "success"

        # Verify it's gone
        get_result = await transaction_service.get_transaction(async_session, tx_id)
        assert get_result["status"] == "error"

    async def test_delete_nonexistent_transaction(self, async_session: AsyncSession):
        """Test deleting a non-existent transaction returns error."""
        result = await transaction_service.delete_transaction(
            async_session, "nonexistent-id-9999"
        )
        assert result["status"] == "error"


class TestSearchTransactions:
    async def test_search_by_transaction_type(self, async_session: AsyncSession):
        """Test searching transactions by type."""
        # Add expense
        await transaction_service.add_transaction(
            async_session, TransactionCreate(amount=100.0, transaction_type="expense")
        )
        # Add income
        await transaction_service.add_transaction(
            async_session, TransactionCreate(amount=5000.0, transaction_type="income")
        )
        await async_session.commit()

        filters = SearchFilters(transaction_type="expense")
        results = await transaction_service.search_transactions(async_session, filters)

        assert len(results) >= 1
        assert all(r["transaction_type"] == "expense" for r in results)

    async def test_search_by_merchant(self, async_session: AsyncSession):
        """Test searching transactions by merchant name."""
        await transaction_service.add_transaction(
            async_session,
            TransactionCreate(amount=200.0, merchant="BigBasket"),
        )
        await async_session.commit()

        filters = SearchFilters(merchant="BigBasket")
        results = await transaction_service.search_transactions(async_session, filters)

        assert len(results) >= 1
        assert all("bigbasket" in r["merchant"].lower() for r in results)

    async def test_search_by_amount_range(self, async_session: AsyncSession):
        """Test searching transactions by amount range."""
        await transaction_service.add_transaction(
            async_session, TransactionCreate(amount=50.0)
        )
        await transaction_service.add_transaction(
            async_session, TransactionCreate(amount=500.0)
        )
        await transaction_service.add_transaction(
            async_session, TransactionCreate(amount=5000.0)
        )
        await async_session.commit()

        filters = SearchFilters(min_amount=100.0, max_amount=1000.0)
        results = await transaction_service.search_transactions(async_session, filters)

        assert len(results) >= 1
        for r in results:
            assert 100.0 <= r["amount"] <= 1000.0

    async def test_search_by_date_range(self, async_session: AsyncSession):
        """Test searching transactions within a date range."""
        await transaction_service.add_transaction(
            async_session,
            TransactionCreate(amount=300.0, timestamp="2024-06-15T12:00:00"),
        )
        await async_session.commit()

        filters = SearchFilters(
            start_date="2024-06-01T00:00:00",
            end_date="2024-06-30T23:59:59",
        )
        results = await transaction_service.search_transactions(async_session, filters)

        assert len(results) >= 1


class TestSuggestCategory:
    def test_suggest_swiggy_merchant(self):
        result = suggest_category(merchant="Swiggy")
        assert result["category"] == "Food"
        assert result["subcategory"] == "Delivery"
        assert result["confidence"] >= 0.8

    def test_suggest_uber_merchant(self):
        result = suggest_category(merchant="Uber India")
        assert result["category"] == "Transport"
        assert result["subcategory"] == "Taxi"

    def test_suggest_from_description(self):
        result = suggest_category(description="Monthly wifi bill payment")
        assert result["category"] == "Bills"
        assert result["matched_on"] == "description"

    def test_suggest_merchant_priority_over_description(self):
        """Merchant match should take priority over description match."""
        result = suggest_category(
            description="zomato",
            merchant="Uber"
        )
        assert result["category"] == "Transport"
        assert result["matched_on"] == "merchant"

    def test_suggest_no_match_returns_other(self):
        result = suggest_category(
            description="Random unknown transaction",
            merchant="Unknown Shop"
        )
        assert result["category"] == "Other"
        assert result["confidence"] < 0.5
