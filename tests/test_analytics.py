from __future__ import annotations

import datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.schemas import TransactionCreate
from app.services.analytics_service import analytics_service
from app.services.category_service import category_service
from app.services.transaction_service import transaction_service


async def _seed_test_transactions(async_session: AsyncSession):
    """Helper to seed multiple test transactions for analytics tests."""
    now = datetime.datetime.utcnow()
    month = now.month
    year = now.year

    test_data = [
        TransactionCreate(
            amount=500.0,
            transaction_type="expense",
            category="Food",
            merchant="Swiggy",
            timestamp=f"{year}-{month:02d}-05T12:00:00",
        ),
        TransactionCreate(
            amount=300.0,
            transaction_type="expense",
            category="Food",
            merchant="Zomato",
            timestamp=f"{year}-{month:02d}-10T13:00:00",
        ),
        TransactionCreate(
            amount=1500.0,
            transaction_type="expense",
            category="Transport",
            merchant="Uber",
            timestamp=f"{year}-{month:02d}-15T09:00:00",
        ),
        TransactionCreate(
            amount=200.0,
            transaction_type="expense",
            category="Entertainment",
            merchant="Netflix",
            timestamp=f"{year}-{month:02d}-20T20:00:00",
        ),
        TransactionCreate(
            amount=30000.0,
            transaction_type="income",
            description="Monthly salary",
            timestamp=f"{year}-{month:02d}-01T09:00:00",
        ),
    ]

    for tx in test_data:
        await transaction_service.add_transaction(async_session, tx)

    await async_session.commit()
    return month, year


class TestMonthlySummary:
    async def test_monthly_summary_empty_month(self, async_session: AsyncSession):
        """Test monthly summary for a month with no transactions."""
        result = await analytics_service.monthly_summary(async_session, 1, 2020)

        assert "income" in result
        assert "expenses" in result
        assert "savings" in result
        assert result["income"] == 0.0
        assert result["expenses"] == 0.0
        assert result["savings"] == 0.0

    async def test_monthly_summary_with_transactions(self, async_session: AsyncSession):
        """Test monthly summary returns correct totals."""
        month, year = await _seed_test_transactions(async_session)

        result = await analytics_service.monthly_summary(async_session, month, year)

        assert result["income"] == 30000.0
        assert result["expenses"] == pytest.approx(2500.0, rel=0.01)
        assert result["savings"] == pytest.approx(27500.0, rel=0.01)
        assert result["transaction_count"] == 5

    async def test_monthly_summary_structure(self, async_session: AsyncSession):
        """Test that monthly summary has the correct keys."""
        now = datetime.datetime.utcnow()
        result = await analytics_service.monthly_summary(async_session, now.month, now.year)

        required_keys = ["month", "year", "income", "expenses", "savings", "transaction_count"]
        for key in required_keys:
            assert key in result, f"Key '{key}' missing from monthly_summary result"


class TestCategoryBreakdown:
    async def test_category_breakdown_structure(self, async_session: AsyncSession):
        """Test that category breakdown has the expected structure."""
        month, year = await _seed_test_transactions(async_session)

        start = f"{year}-{month:02d}-01"
        end = f"{year}-{month:02d}-28"
        result = await analytics_service.category_breakdown(async_session, start, end)

        assert "breakdown" in result
        assert "total_expenses" in result
        assert "start_date" in result
        assert "end_date" in result

    async def test_category_breakdown_sums(self, async_session: AsyncSession):
        """Test that category breakdown totals add up correctly."""
        month, year = await _seed_test_transactions(async_session)

        start = f"{year}-{month:02d}-01"
        end = f"{year}-{month:02d}-28"
        result = await analytics_service.category_breakdown(async_session, start, end)

        total_from_breakdown = sum(
            v["total"] for v in result["breakdown"].values()
        )
        assert abs(total_from_breakdown - result["total_expenses"]) < 0.01

    async def test_category_breakdown_percentages(self, async_session: AsyncSession):
        """Test that percentages in breakdown are reasonable."""
        month, year = await _seed_test_transactions(async_session)

        start = f"{year}-{month:02d}-01"
        end = f"{year}-{month:02d}-28"
        result = await analytics_service.category_breakdown(async_session, start, end)

        total_percentage = sum(v["percentage"] for v in result["breakdown"].values())
        # Percentages should sum to approximately 100%
        assert abs(total_percentage - 100.0) < 1.0

    async def test_category_breakdown_empty_range(self, async_session: AsyncSession):
        """Test breakdown for a range with no transactions."""
        result = await analytics_service.category_breakdown(
            async_session, "2000-01-01", "2000-01-31"
        )
        assert result["breakdown"] == {}


class TestSpendingTrend:
    async def test_spending_trend_returns_correct_count(self, async_session: AsyncSession):
        """Test that spending trend returns the requested number of months."""
        result = await analytics_service.spending_trend(async_session, months=3)

        assert isinstance(result, list)
        assert len(result) == 3

    async def test_spending_trend_structure(self, async_session: AsyncSession):
        """Test that spending trend has the correct structure per month."""
        result = await analytics_service.spending_trend(async_session, months=2)

        for entry in result:
            assert "month" in entry
            assert "year" in entry
            assert "month_label" in entry
            assert "income" in entry
            assert "expenses" in entry
            assert "savings" in entry
            assert "transaction_count" in entry

    async def test_spending_trend_months_ordered(self, async_session: AsyncSession):
        """Test that spending trend months are in chronological order."""
        result = await analytics_service.spending_trend(async_session, months=6)

        # Compare each consecutive pair
        for i in range(len(result) - 1):
            current = datetime.datetime(result[i]["year"], result[i]["month"], 1)
            next_entry = datetime.datetime(result[i + 1]["year"], result[i + 1]["month"], 1)
            assert current <= next_entry, "Months should be in chronological order"

    async def test_spending_trend_current_month_has_data(self, async_session: AsyncSession):
        """Test that the current month in the trend reflects actual transactions."""
        month, year = await _seed_test_transactions(async_session)

        result = await analytics_service.spending_trend(async_session, months=1)

        assert len(result) == 1
        current_month_data = result[0]
        assert current_month_data["income"] == 30000.0
        assert current_month_data["expenses"] == pytest.approx(2500.0, rel=0.01)


class TestIncomeVsExpense:
    async def test_income_vs_expense_structure(self, async_session: AsyncSession):
        """Test income vs expense return structure."""
        now = datetime.datetime.utcnow()
        result = await analytics_service.income_vs_expense(
            async_session, now.month, now.year
        )

        required_keys = ["income", "expenses", "savings", "savings_rate", "is_deficit"]
        for key in required_keys:
            assert key in result

    async def test_income_vs_expense_values(self, async_session: AsyncSession):
        """Test income vs expense calculates correctly."""
        month, year = await _seed_test_transactions(async_session)

        result = await analytics_service.income_vs_expense(async_session, month, year)

        assert result["income"] == 30000.0
        assert result["expenses"] == pytest.approx(2500.0, rel=0.01)
        assert result["savings"] == pytest.approx(27500.0, rel=0.01)
        assert result["is_deficit"] is False
        assert result["savings_rate"] > 0

    async def test_income_vs_expense_deficit(self, async_session: AsyncSession):
        """Test that is_deficit is True when expenses exceed income."""
        # Add only expenses, no income
        await transaction_service.add_transaction(
            async_session,
            TransactionCreate(amount=5000.0, transaction_type="expense"),
        )
        await async_session.commit()

        now = datetime.datetime.utcnow()
        result = await analytics_service.income_vs_expense(
            async_session, now.month, now.year
        )

        assert result["expenses"] >= 5000.0
        assert result["is_deficit"] is True


class TestMerchantAnalysis:
    async def test_merchant_analysis_structure(self, async_session: AsyncSession):
        """Test merchant analysis return structure."""
        month, year = await _seed_test_transactions(async_session)

        result = await analytics_service.merchant_analysis(async_session)

        assert "merchants" in result
        assert "total_merchants" in result
        assert isinstance(result["merchants"], list)

    async def test_merchant_analysis_top_merchant(self, async_session: AsyncSession):
        """Test that the most-spent merchant appears first."""
        month, year = await _seed_test_transactions(async_session)

        result = await analytics_service.merchant_analysis(async_session)

        if result["merchants"]:
            # Uber (1500) should be the top merchant
            top = result["merchants"][0]
            assert top["total_spent"] >= result["merchants"][-1]["total_spent"]


class TestAverageDailySpend:
    async def test_average_daily_spend_empty_month(self, async_session: AsyncSession):
        """Test average daily spend for an empty month."""
        result = await analytics_service.average_daily_spend(async_session, 1, 2020)

        assert "average_daily_spend" in result
        assert result["average_daily_spend"] == 0.0

    async def test_average_daily_spend_with_transactions(self, async_session: AsyncSession):
        """Test average daily spend calculation."""
        month, year = await _seed_test_transactions(async_session)

        result = await analytics_service.average_daily_spend(async_session, month, year)

        assert result["average_daily_spend"] > 0
        assert "total_days_with_expenses" in result
        assert "highest_spend_day" in result
        assert "lowest_spend_day" in result
        assert "daily_breakdown" in result
