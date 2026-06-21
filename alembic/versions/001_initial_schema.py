"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-21

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # categories
    op.create_table(
        "categories",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("color", sa.String(50), nullable=True),
        sa.Column("budget_limit", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )

    # subcategories
    op.create_table(
        "subcategories",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "category_id",
            sa.String(36),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_subcategories_category_id", "subcategories", ["category_id"])

    # transactions
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False, server_default="expense"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="INR"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("merchant", sa.String(255), nullable=True),
        sa.Column(
            "category_id",
            sa.String(36),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "subcategory_id",
            sa.String(36),
            sa.ForeignKey("subcategories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("payment_method", sa.String(50), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_transactions_timestamp", "transactions", ["timestamp"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_index("ix_transactions_transaction_type", "transactions", ["transaction_type"])

    # budgets
    op.create_table(
        "budgets",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "category_id",
            sa.String(36),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_budgets_category_id", "budgets", ["category_id"])
    op.create_index("ix_budgets_year_month", "budgets", ["year", "month"])


def downgrade() -> None:
    op.drop_table("budgets")
    op.drop_table("transactions")
    op.drop_table("subcategories")
    op.drop_table("categories")
