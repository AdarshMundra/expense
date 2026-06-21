from __future__ import annotations

import datetime
import logging
from typing import Optional, List

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.transaction_repository import transaction_repository

logger = logging.getLogger(__name__)


def _transactions_to_df(transactions: list) -> pd.DataFrame:
    """Convert a list of Transaction model objects to a pandas DataFrame."""
    if not transactions:
        return pd.DataFrame()

    rows = []
    for t in transactions:
        rows.append({
            "id": t.id,
            "timestamp": t.timestamp,
            "transaction_type": t.transaction_type,
            "amount": float(t.amount) if t.amount is not None else 0.0,
            "currency": t.currency,
            "description": t.description,
            "merchant": t.merchant,
            "category": t.category_rel.name if t.category_rel else "Uncategorized",
            "subcategory": t.subcategory_rel.name if t.subcategory_rel else None,
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


class AnalyticsService:
    """Service for analytics and reporting using pandas."""

    async def monthly_summary(
        self, session: AsyncSession, month: int, year: int
    ) -> dict:
        """Get income, expenses, and savings for a specific month."""
        try:
            transactions = await transaction_repository.get_by_month(session, month, year)
            df = _transactions_to_df(transactions)

            if df.empty:
                return {
                    "month": month,
                    "year": year,
                    "income": 0.0,
                    "expenses": 0.0,
                    "savings": 0.0,
                    "transaction_count": 0,
                    "net_balance": 0.0,
                }

            income = float(df[df["transaction_type"] == "income"]["amount"].sum())
            expenses = float(df[df["transaction_type"] == "expense"]["amount"].sum())
            savings = income - expenses

            return {
                "month": month,
                "year": year,
                "income": round(income, 2),
                "expenses": round(expenses, 2),
                "savings": round(savings, 2),
                "transaction_count": len(df),
                "net_balance": round(savings, 2),
                "avg_daily_expense": round(expenses / max(1, df["timestamp"].dt.day.nunique()), 2),
            }
        except Exception as e:
            logger.error(f"Error in monthly_summary: {e}")
            return {"status": "error", "message": str(e)}

    async def category_breakdown(
        self, session: AsyncSession, start_date: str, end_date: str
    ) -> dict:
        """Get expense breakdown by category for a date range."""
        try:
            start_dt = datetime.datetime.fromisoformat(start_date)
            end_dt = datetime.datetime.fromisoformat(end_date)

            transactions = await transaction_repository.get_all_in_range(
                session, start_dt, end_dt
            )
            df = _transactions_to_df(transactions)

            if df.empty:
                return {"start_date": start_date, "end_date": end_date, "breakdown": {}}

            expenses_df = df[df["transaction_type"] == "expense"]
            if expenses_df.empty:
                return {"start_date": start_date, "end_date": end_date, "breakdown": {}}

            breakdown = (
                expenses_df.groupby("category")["amount"]
                .agg(["sum", "count", "mean"])
                .round(2)
            )
            total = expenses_df["amount"].sum()

            result = {}
            for cat, row in breakdown.iterrows():
                result[cat] = {
                    "total": round(float(row["sum"]), 2),
                    "count": int(row["count"]),
                    "average": round(float(row["mean"]), 2),
                    "percentage": round(float(row["sum"]) / total * 100, 1) if total > 0 else 0.0,
                }

            return {
                "start_date": start_date,
                "end_date": end_date,
                "total_expenses": round(float(total), 2),
                "breakdown": result,
            }
        except Exception as e:
            logger.error(f"Error in category_breakdown: {e}")
            return {"status": "error", "message": str(e)}

    async def top_spending_categories(
        self,
        session: AsyncSession,
        limit: int = 5,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> list:
        """Get top N spending categories."""
        try:
            if start_date and end_date:
                start_dt = datetime.datetime.fromisoformat(start_date)
                end_dt = datetime.datetime.fromisoformat(end_date)
                transactions = await transaction_repository.get_all_in_range(
                    session, start_dt, end_dt
                )
            else:
                # Default to current month if no date range
                now = datetime.datetime.utcnow()
                transactions = await transaction_repository.get_by_month(
                    session, now.month, now.year
                )

            df = _transactions_to_df(transactions)
            if df.empty:
                return []

            expenses_df = df[df["transaction_type"] == "expense"]
            if expenses_df.empty:
                return []

            top = (
                expenses_df.groupby("category")["amount"]
                .sum()
                .sort_values(ascending=False)
                .head(limit)
            )

            total = expenses_df["amount"].sum()
            return [
                {
                    "rank": i + 1,
                    "category": cat,
                    "total": round(float(amount), 2),
                    "percentage": round(float(amount) / total * 100, 1) if total > 0 else 0.0,
                }
                for i, (cat, amount) in enumerate(top.items())
            ]
        except Exception as e:
            logger.error(f"Error in top_spending_categories: {e}")
            return []

    async def spending_trend(self, session: AsyncSession, months: int = 6) -> list[dict]:
        """Get spending trend for the last N months."""
        try:
            now = datetime.datetime.utcnow()
            results = []

            for i in range(months - 1, -1, -1):
                # Calculate the target month
                target_month = now.month - i
                target_year = now.year

                while target_month <= 0:
                    target_month += 12
                    target_year -= 1

                transactions = await transaction_repository.get_by_month(
                    session, target_month, target_year
                )
                df = _transactions_to_df(transactions)

                income = float(df[df["transaction_type"] == "income"]["amount"].sum()) if not df.empty else 0.0
                expenses = float(df[df["transaction_type"] == "expense"]["amount"].sum()) if not df.empty else 0.0

                results.append({
                    "month": target_month,
                    "year": target_year,
                    "month_label": datetime.datetime(target_year, target_month, 1).strftime("%B %Y"),
                    "income": round(income, 2),
                    "expenses": round(expenses, 2),
                    "savings": round(income - expenses, 2),
                    "transaction_count": len(df) if not df.empty else 0,
                })

            return results
        except Exception as e:
            logger.error(f"Error in spending_trend: {e}")
            return []

    async def merchant_analysis(
        self,
        session: AsyncSession,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        """Get spending analysis by merchant."""
        try:
            if start_date and end_date:
                start_dt = datetime.datetime.fromisoformat(start_date)
                end_dt = datetime.datetime.fromisoformat(end_date)
                transactions = await transaction_repository.get_all_in_range(
                    session, start_dt, end_dt
                )
            else:
                now = datetime.datetime.utcnow()
                transactions = await transaction_repository.get_by_month(
                    session, now.month, now.year
                )

            df = _transactions_to_df(transactions)
            if df.empty:
                return {"merchants": [], "total_merchants": 0}

            expenses_df = df[df["transaction_type"] == "expense"].copy()
            expenses_df["merchant"] = expenses_df["merchant"].fillna("Unknown")

            merchant_stats = (
                expenses_df.groupby("merchant")["amount"]
                .agg(["sum", "count", "mean"])
                .sort_values("sum", ascending=False)
                .round(2)
            )

            total = expenses_df["amount"].sum()
            merchants = []
            for merchant, row in merchant_stats.iterrows():
                merchants.append({
                    "merchant": merchant,
                    "total_spent": round(float(row["sum"]), 2),
                    "transaction_count": int(row["count"]),
                    "average_transaction": round(float(row["mean"]), 2),
                    "percentage": round(float(row["sum"]) / total * 100, 1) if total > 0 else 0.0,
                })

            return {
                "merchants": merchants,
                "total_merchants": len(merchants),
                "total_spent": round(float(total), 2),
            }
        except Exception as e:
            logger.error(f"Error in merchant_analysis: {e}")
            return {"status": "error", "message": str(e)}

    async def average_daily_spend(
        self, session: AsyncSession, month: int, year: int
    ) -> dict:
        """Calculate average daily spending for a month."""
        try:
            transactions = await transaction_repository.get_by_month(session, month, year)
            df = _transactions_to_df(transactions)

            if df.empty:
                return {
                    "month": month,
                    "year": year,
                    "average_daily_spend": 0.0,
                    "total_days_with_expenses": 0,
                    "highest_day": None,
                    "lowest_day": None,
                }

            expenses_df = df[df["transaction_type"] == "expense"].copy()
            if expenses_df.empty:
                return {
                    "month": month,
                    "year": year,
                    "average_daily_spend": 0.0,
                    "total_days_with_expenses": 0,
                }

            expenses_df["date"] = expenses_df["timestamp"].dt.date
            daily = expenses_df.groupby("date")["amount"].sum()

            highest_day = daily.idxmax()
            lowest_day = daily.idxmin()

            return {
                "month": month,
                "year": year,
                "average_daily_spend": round(float(daily.mean()), 2),
                "total_days_with_expenses": len(daily),
                "highest_spend_day": {
                    "date": str(highest_day),
                    "amount": round(float(daily[highest_day]), 2),
                },
                "lowest_spend_day": {
                    "date": str(lowest_day),
                    "amount": round(float(daily[lowest_day]), 2),
                },
                "daily_breakdown": {
                    str(date): round(float(amount), 2)
                    for date, amount in daily.items()
                },
            }
        except Exception as e:
            logger.error(f"Error in average_daily_spend: {e}")
            return {"status": "error", "message": str(e)}

    async def income_vs_expense(
        self, session: AsyncSession, month: int, year: int
    ) -> dict:
        """Compare income vs expenses for a month."""
        try:
            transactions = await transaction_repository.get_by_month(session, month, year)
            df = _transactions_to_df(transactions)

            if df.empty:
                return {
                    "month": month,
                    "year": year,
                    "income": 0.0,
                    "expenses": 0.0,
                    "savings": 0.0,
                    "savings_rate": 0.0,
                    "is_deficit": False,
                }

            income = float(df[df["transaction_type"] == "income"]["amount"].sum())
            expenses = float(df[df["transaction_type"] == "expense"]["amount"].sum())
            savings = income - expenses
            savings_rate = (savings / income * 100) if income > 0 else 0.0

            return {
                "month": month,
                "year": year,
                "income": round(income, 2),
                "expenses": round(expenses, 2),
                "savings": round(savings, 2),
                "savings_rate": round(savings_rate, 1),
                "is_deficit": savings < 0,
                "income_transactions": int(len(df[df["transaction_type"] == "income"])),
                "expense_transactions": int(len(df[df["transaction_type"] == "expense"])),
            }
        except Exception as e:
            logger.error(f"Error in income_vs_expense: {e}")
            return {"status": "error", "message": str(e)}


analytics_service = AnalyticsService()
