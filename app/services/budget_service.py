from __future__ import annotations

import datetime
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.budget_repository import budget_repository
from app.repositories.transaction_repository import transaction_repository
from app.schemas.schemas import BudgetCreate

logger = logging.getLogger(__name__)


class BudgetService:
    """Business logic service for budgets."""

    async def set_budget(self, session: AsyncSession, data: BudgetCreate) -> dict:
        """Create or update a budget for a category/month/year."""
        try:
            # Check if budget already exists for this category/month/year
            existing = await budget_repository.get_by_category_month(
                session, data.category_id, data.month, data.year
            )

            if existing:
                # Update existing budget
                updated = await budget_repository.update(
                    session,
                    existing.id,
                    {"allocated_amount": data.allocated_amount},
                )
                return {
                    "status": "success",
                    "action": "updated",
                    "message": "Budget updated successfully.",
                    "budget": updated.to_dict() if updated else None,
                }

            budget = await budget_repository.create(
                session,
                {
                    "category_id": data.category_id,
                    "month": data.month,
                    "year": data.year,
                    "allocated_amount": data.allocated_amount,
                },
            )

            return {
                "status": "success",
                "action": "created",
                "message": "Budget created successfully.",
                "budget": budget.to_dict(),
            }
        except Exception as e:
            logger.error(f"Error setting budget: {e}")
            return {"status": "error", "message": str(e)}

    async def get_budget_status(
        self, session: AsyncSession, month: int, year: int
    ) -> dict:
        """
        Get budget status for all budgets in a given month/year.
        Calculates spent amount from transactions.
        """
        try:
            budgets = await budget_repository.get_by_month_year(session, month, year)
            if not budgets:
                return {
                    "month": month,
                    "year": year,
                    "budgets": {},
                    "message": "No budgets set for this period.",
                }

            transactions = await transaction_repository.get_by_month(session, month, year)

            # Build category -> spent map
            category_spent: dict[str, float] = {}
            for t in transactions:
                if t.transaction_type == "expense" and t.category_id:
                    cat_id = t.category_id
                    category_spent[cat_id] = category_spent.get(cat_id, 0.0) + float(t.amount)

            result: dict[str, dict] = {}
            for budget in budgets:
                category_name = budget.category.name if budget.category else budget.category_id
                allocated = float(budget.allocated_amount)
                spent = round(category_spent.get(budget.category_id, 0.0), 2)
                remaining = round(allocated - spent, 2)
                percentage = round((spent / allocated * 100) if allocated > 0 else 0.0, 1)

                result[category_name] = {
                    "budget_id": budget.id,
                    "category_id": budget.category_id,
                    "allocated": round(allocated, 2),
                    "spent": spent,
                    "remaining": remaining,
                    "percentage_used": percentage,
                    "is_over_budget": spent > allocated,
                    "status": "over_budget" if spent > allocated else (
                        "warning" if percentage >= 80 else "on_track"
                    ),
                }

            return {
                "month": month,
                "year": year,
                "budgets": result,
                "summary": {
                    "total_allocated": round(sum(b["allocated"] for b in result.values()), 2),
                    "total_spent": round(sum(b["spent"] for b in result.values()), 2),
                    "over_budget_categories": [
                        cat for cat, data in result.items() if data["is_over_budget"]
                    ],
                },
            }
        except Exception as e:
            logger.error(f"Error getting budget status: {e}")
            return {"status": "error", "message": str(e)}

    async def update_budget(
        self, session: AsyncSession, id: str, data: dict
    ) -> dict:
        """Update a budget by ID."""
        try:
            budget = await budget_repository.update(session, id, data)
            if not budget:
                return {"status": "error", "message": f"Budget {id} not found."}
            return {
                "status": "success",
                "message": "Budget updated.",
                "budget": budget.to_dict(),
            }
        except Exception as e:
            logger.error(f"Error updating budget: {e}")
            return {"status": "error", "message": str(e)}

    async def delete_budget(self, session: AsyncSession, id: str) -> dict:
        """Delete a budget by ID."""
        try:
            deleted = await budget_repository.delete(session, id)
            if not deleted:
                return {"status": "error", "message": f"Budget {id} not found."}
            return {
                "status": "success",
                "message": f"Budget {id} deleted successfully.",
            }
        except Exception as e:
            logger.error(f"Error deleting budget: {e}")
            return {"status": "error", "message": str(e)}

    async def list_budgets(self, session: AsyncSession) -> list[dict]:
        """List all budgets."""
        try:
            budgets = await budget_repository.list_all(session)
            return [b.to_dict() for b in budgets]
        except Exception as e:
            logger.error(f"Error listing budgets: {e}")
            return []

    async def get_over_budget_alerts(self, session: AsyncSession) -> list[dict]:
        """
        Get alerts for categories that are over budget for the current month.
        """
        try:
            now = datetime.datetime.utcnow()
            status = await self.get_budget_status(session, now.month, now.year)

            if status.get("status") == "error":
                return []

            budgets_data = status.get("budgets", {})
            alerts = []

            for category_name, data in budgets_data.items():
                if data["is_over_budget"] or data["percentage_used"] >= 80:
                    alerts.append({
                        "category": category_name,
                        "category_id": data["category_id"],
                        "budget_id": data["budget_id"],
                        "allocated": data["allocated"],
                        "spent": data["spent"],
                        "overspend": round(data["spent"] - data["allocated"], 2),
                        "percentage_used": data["percentage_used"],
                        "status": data["status"],
                        "alert_type": "over_budget" if data["is_over_budget"] else "approaching_limit",
                        "message": (
                            f"⚠️ {category_name} is OVER budget by "
                            f"₹{round(data['spent'] - data['allocated'], 2)}"
                            if data["is_over_budget"]
                            else f"⚡ {category_name} has used {data['percentage_used']}% of budget"
                        ),
                    })

            alerts.sort(key=lambda x: x["percentage_used"], reverse=True)
            return alerts
        except Exception as e:
            logger.error(f"Error getting over budget alerts: {e}")
            return []


budget_service = BudgetService()
