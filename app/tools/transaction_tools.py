from __future__ import annotations

import json
import logging
from typing import Optional

from app.database.session import get_session
from app.schemas.schemas import TransactionCreate, TransactionUpdate, SearchFilters
from app.services.transaction_service import transaction_service, suggest_category as _suggest_category

logger = logging.getLogger(__name__)


def register_tools(mcp) -> None:
    """Register transaction-related MCP tools."""

    @mcp.tool()
    async def add_transaction(
        amount: float,
        transaction_type: str = "expense",
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        description: Optional[str] = None,
        merchant: Optional[str] = None,
        timestamp: Optional[str] = None,
        currency: str = "INR",
        payment_method: Optional[str] = None,
        location: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> dict:
        """
        Add a new expense or income transaction.

        Args:
            amount: Transaction amount (must be positive)
            transaction_type: 'expense', 'income', or 'transfer'
            category: Category name (auto-detected if not provided)
            subcategory: Subcategory name
            description: Transaction description
            merchant: Merchant/vendor name
            timestamp: ISO format datetime (defaults to now)
            currency: Currency code (default: INR)
            payment_method: Payment method (cash, card, upi, etc.)
            location: Transaction location
            notes: Additional notes
            tags: JSON string of tag list, e.g. '["food", "lunch"]'
        """
        tags_list: Optional[list] = None
        if tags:
            try:
                tags_list = json.loads(tags)
            except json.JSONDecodeError:
                tags_list = [tags]

        data = TransactionCreate(
            amount=amount,
            transaction_type=transaction_type,
            category=category,
            subcategory=subcategory,
            description=description,
            merchant=merchant,
            timestamp=timestamp,
            currency=currency,
            payment_method=payment_method,
            location=location,
            notes=notes,
            tags=tags_list,
        )

        async with get_session() as session:
            return await transaction_service.add_transaction(session, data)

    @mcp.tool()
    async def update_transaction(
        transaction_id: str,
        amount: Optional[float] = None,
        transaction_type: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        description: Optional[str] = None,
        merchant: Optional[str] = None,
        timestamp: Optional[str] = None,
        currency: Optional[str] = None,
        payment_method: Optional[str] = None,
        location: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> dict:
        """
        Update an existing transaction.

        Args:
            transaction_id: The UUID of the transaction to update
            amount: New amount
            transaction_type: New type
            category: New category name
            subcategory: New subcategory name
            description: New description
            merchant: New merchant name
            timestamp: New timestamp (ISO format)
            currency: New currency code
            payment_method: New payment method
            location: New location
            notes: New notes
            tags: JSON string of tags
        """
        tags_list: Optional[list] = None
        if tags:
            try:
                tags_list = json.loads(tags)
            except json.JSONDecodeError:
                tags_list = [tags]

        data = TransactionUpdate(
            amount=amount,
            transaction_type=transaction_type,
            category=category,
            subcategory=subcategory,
            description=description,
            merchant=merchant,
            timestamp=timestamp,
            currency=currency,
            payment_method=payment_method,
            location=location,
            notes=notes,
            tags=tags_list,
        )

        async with get_session() as session:
            return await transaction_service.update_transaction(session, transaction_id, data)

    @mcp.tool()
    async def delete_transaction(transaction_id: str) -> dict:
        """
        Delete a transaction by ID.

        Args:
            transaction_id: The UUID of the transaction to delete
        """
        async with get_session() as session:
            return await transaction_service.delete_transaction(session, transaction_id)

    @mcp.tool()
    async def get_transaction(transaction_id: str) -> dict:
        """
        Get details of a specific transaction.

        Args:
            transaction_id: The UUID of the transaction
        """
        async with get_session() as session:
            return await transaction_service.get_transaction(session, transaction_id)

    @mcp.tool()
    async def search_transactions(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        merchant: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        transaction_type: Optional[str] = None,
    ) -> list[dict]:
        """
        Search transactions with optional filters.

        Args:
            start_date: Start date in ISO format (e.g. '2024-01-01')
            end_date: End date in ISO format (e.g. '2024-01-31')
            category: Filter by category name
            subcategory: Filter by subcategory name
            merchant: Filter by merchant name (partial match)
            min_amount: Minimum amount filter
            max_amount: Maximum amount filter
            transaction_type: Filter by type ('expense', 'income', 'transfer')
        """
        filters = SearchFilters(
            start_date=start_date,
            end_date=end_date,
            category=category,
            subcategory=subcategory,
            merchant=merchant,
            min_amount=min_amount,
            max_amount=max_amount,
            transaction_type=transaction_type,
        )

        async with get_session() as session:
            return await transaction_service.search_transactions(session, filters)

    @mcp.tool()
    async def bulk_import_transactions(transactions_json: str) -> dict:
        """
        Bulk import multiple transactions from a JSON string.

        Args:
            transactions_json: JSON string representing a list of transactions.
                Each item should match TransactionCreate schema.
                Example: '[{"amount": 100, "merchant": "Swiggy", "transaction_type": "expense"}]'
        """
        try:
            raw_list = json.loads(transactions_json)
            if not isinstance(raw_list, list):
                return {"status": "error", "message": "Expected a JSON array of transactions."}

            transactions = [TransactionCreate(**item) for item in raw_list]

            async with get_session() as session:
                return await transaction_service.bulk_import(session, transactions)
        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"Invalid JSON: {e}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @mcp.tool()
    async def suggest_category(
        description: Optional[str] = None,
        merchant: Optional[str] = None,
    ) -> dict:
        """
        Suggest a category and subcategory based on merchant or description.
        Merchant name is checked first, then description keywords.

        Args:
            description: Transaction description text
            merchant: Merchant name
        """
        return _suggest_category(description=description, merchant=merchant)
