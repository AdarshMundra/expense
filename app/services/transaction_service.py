from __future__ import annotations

import datetime
import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.transaction_repository import transaction_repository
from app.repositories.category_repository import category_repository
from app.schemas.schemas import TransactionCreate, TransactionUpdate, SearchFilters

logger = logging.getLogger(__name__)

# Auto-categorization rules: keyword -> (category_name, subcategory_name or None)
AUTO_CATEGORIZATION: dict[str, tuple[str, Optional[str]]] = {
    "uber": ("Transport", "Taxi"),
    "ola": ("Transport", "Taxi"),
    "swiggy": ("Food", "Delivery"),
    "zomato": ("Food", "Delivery"),
    "amazon": ("Shopping", None),
    "flipkart": ("Shopping", None),
    "netflix": ("Entertainment", None),
    "spotify": ("Entertainment", None),
    "electricity": ("Bills", None),
    "wifi": ("Bills", None),
    "bigbasket": ("Food", "Groceries"),
    "grofers": ("Food", "Groceries"),
    "blinkit": ("Food", "Groceries"),
    "rapido": ("Transport", "Taxi"),
    "dunzo": ("Food", "Delivery"),
    "gym": ("Healthcare", None),
    "hospital": ("Healthcare", None),
    "pharmacy": ("Healthcare", None),
    "medicine": ("Healthcare", None),
    "fuel": ("Transport", "Fuel"),
    "petrol": ("Transport", "Fuel"),
    "diesel": ("Transport", "Fuel"),
    "irctc": ("Transport", "Train"),
    "train": ("Transport", "Train"),
}


def suggest_category(
    description: Optional[str] = None,
    merchant: Optional[str] = None,
) -> dict:
    """
    Suggest a category and subcategory based on merchant name or description.
    Merchant name is checked first (exact keyword match), then description keywords.
    Returns {category, subcategory, confidence}.
    """
    # Check merchant first
    if merchant:
        merchant_lower = merchant.lower().strip()
        for keyword, (cat, subcat) in AUTO_CATEGORIZATION.items():
            if keyword in merchant_lower:
                return {
                    "category": cat,
                    "subcategory": subcat,
                    "confidence": 0.9,
                    "matched_keyword": keyword,
                    "matched_on": "merchant",
                }

    # Then check description keywords
    if description:
        desc_lower = description.lower().strip()
        for keyword, (cat, subcat) in AUTO_CATEGORIZATION.items():
            if keyword in desc_lower:
                return {
                    "category": cat,
                    "subcategory": subcat,
                    "confidence": 0.7,
                    "matched_keyword": keyword,
                    "matched_on": "description",
                }

    return {
        "category": "Other",
        "subcategory": None,
        "confidence": 0.1,
        "matched_keyword": None,
        "matched_on": None,
    }


async def _resolve_category(
    session: AsyncSession,
    category_name: Optional[str],
    subcategory_name: Optional[str],
    description: Optional[str],
    merchant: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve category and subcategory names to IDs.
    If no category given, attempt auto-categorization.
    Returns (category_id, subcategory_id).
    """
    # If no category provided, attempt auto-categorization
    if not category_name:
        suggestion = suggest_category(description, merchant)
        if suggestion["confidence"] >= 0.5:
            category_name = suggestion["category"]
            subcategory_name = suggestion.get("subcategory")

    if not category_name:
        return None, None

    # Look up category by name
    category = await category_repository.get_by_name(session, category_name)
    if not category:
        return None, None

    category_id = category.id
    subcategory_id = None

    if subcategory_name:
        subcategory = await category_repository.get_subcategory_by_name(
            session, category_id, subcategory_name
        )
        if subcategory:
            subcategory_id = subcategory.id

    return category_id, subcategory_id


class TransactionService:
    """Business logic service for transactions."""

    async def add_transaction(
        self, session: AsyncSession, data: TransactionCreate
    ) -> dict:
        """
        Add a new transaction. Resolves category/subcategory names to IDs.
        Auto-categorizes if no category provided.
        """
        try:
            category_id, subcategory_id = await _resolve_category(
                session,
                data.category,
                data.subcategory,
                data.description,
                data.merchant,
            )

            # Parse timestamp
            if data.timestamp:
                try:
                    timestamp = datetime.datetime.fromisoformat(data.timestamp)
                except ValueError:
                    timestamp = datetime.datetime.utcnow()
            else:
                timestamp = datetime.datetime.utcnow()

            transaction_data = {
                "amount": data.amount,
                "transaction_type": data.transaction_type,
                "description": data.description,
                "merchant": data.merchant,
                "timestamp": timestamp,
                "currency": data.currency,
                "payment_method": data.payment_method,
                "location": data.location,
                "notes": data.notes,
                "tags": data.tags,
                "category_id": category_id,
                "subcategory_id": subcategory_id,
            }

            transaction = await transaction_repository.create(session, transaction_data)

            return {
                "status": "success",
                "transaction_id": transaction.id,
                "message": f"Transaction of {data.currency} {data.amount} added successfully.",
                "transaction": transaction.to_dict(),
            }
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            return {"status": "error", "message": str(e)}

    async def update_transaction(
        self, session: AsyncSession, id: str, data: TransactionUpdate
    ) -> dict:
        """Update an existing transaction."""
        try:
            existing = await transaction_repository.get_by_id(session, id)
            if not existing:
                return {"status": "error", "message": f"Transaction {id} not found."}

            update_data: dict = {}

            if data.amount is not None:
                update_data["amount"] = data.amount
            if data.transaction_type is not None:
                update_data["transaction_type"] = data.transaction_type
            if data.description is not None:
                update_data["description"] = data.description
            if data.merchant is not None:
                update_data["merchant"] = data.merchant
            if data.currency is not None:
                update_data["currency"] = data.currency
            if data.payment_method is not None:
                update_data["payment_method"] = data.payment_method
            if data.location is not None:
                update_data["location"] = data.location
            if data.notes is not None:
                update_data["notes"] = data.notes
            if data.tags is not None:
                update_data["tags"] = data.tags
            if data.timestamp is not None:
                try:
                    update_data["timestamp"] = datetime.datetime.fromisoformat(data.timestamp)
                except ValueError:
                    pass

            # Resolve new category if provided
            if data.category is not None or data.subcategory is not None:
                category_id, subcategory_id = await _resolve_category(
                    session,
                    data.category,
                    data.subcategory,
                    data.description,
                    data.merchant,
                )
                update_data["category_id"] = category_id
                update_data["subcategory_id"] = subcategory_id

            updated = await transaction_repository.update(session, id, update_data)
            if not updated:
                return {"status": "error", "message": f"Transaction {id} not found."}

            return {
                "status": "success",
                "message": "Transaction updated successfully.",
                "transaction": updated.to_dict(),
            }
        except Exception as e:
            logger.error(f"Error updating transaction: {e}")
            return {"status": "error", "message": str(e)}

    async def delete_transaction(self, session: AsyncSession, id: str) -> dict:
        """Delete a transaction by ID."""
        try:
            deleted = await transaction_repository.delete(session, id)
            if not deleted:
                return {"status": "error", "message": f"Transaction {id} not found."}
            return {
                "status": "success",
                "message": f"Transaction {id} deleted successfully.",
            }
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            return {"status": "error", "message": str(e)}

    async def get_transaction(self, session: AsyncSession, id: str) -> dict:
        """Get a transaction by ID."""
        try:
            transaction = await transaction_repository.get_by_id(session, id)
            if not transaction:
                return {"status": "error", "message": f"Transaction {id} not found."}
            return {
                "status": "success",
                "transaction": transaction.to_dict(),
            }
        except Exception as e:
            logger.error(f"Error getting transaction: {e}")
            return {"status": "error", "message": str(e)}

    async def search_transactions(
        self, session: AsyncSession, filters: SearchFilters
    ) -> list[dict]:
        """Search transactions with filters."""
        try:
            filter_dict: dict = {}

            if filters.start_date:
                filter_dict["start_date"] = filters.start_date
            if filters.end_date:
                filter_dict["end_date"] = filters.end_date
            if filters.merchant:
                filter_dict["merchant"] = filters.merchant
            if filters.min_amount is not None:
                filter_dict["min_amount"] = filters.min_amount
            if filters.max_amount is not None:
                filter_dict["max_amount"] = filters.max_amount
            if filters.transaction_type:
                filter_dict["transaction_type"] = filters.transaction_type

            # Resolve category name to ID
            if filters.category:
                category = await category_repository.get_by_name(session, filters.category)
                if category:
                    filter_dict["category_id"] = category.id
                    # Resolve subcategory if provided
                    if filters.subcategory:
                        subcategory = await category_repository.get_subcategory_by_name(
                            session, category.id, filters.subcategory
                        )
                        if subcategory:
                            filter_dict["subcategory_id"] = subcategory.id

            transactions = await transaction_repository.search(session, filter_dict)
            return [t.to_dict() for t in transactions]
        except Exception as e:
            logger.error(f"Error searching transactions: {e}")
            return []

    async def bulk_import(
        self, session: AsyncSession, transactions: List[TransactionCreate]
    ) -> dict:
        """Bulk import multiple transactions."""
        success_count = 0
        error_count = 0
        errors = []
        imported_ids = []

        for i, tx_data in enumerate(transactions):
            result = await self.add_transaction(session, tx_data)
            if result.get("status") == "success":
                success_count += 1
                imported_ids.append(result.get("transaction_id"))
            else:
                error_count += 1
                errors.append({"index": i, "error": result.get("message", "Unknown error")})

        return {
            "status": "success" if error_count == 0 else "partial",
            "total": len(transactions),
            "imported": success_count,
            "failed": error_count,
            "imported_ids": imported_ids,
            "errors": errors,
        }


transaction_service = TransactionService()
