from __future__ import annotations

import uuid
import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Numeric, ForeignKey, Integer, Text, func, JSON
)
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.database.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    budget_limit: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        nullable=True, onupdate=func.now()
    )

    # Relationships
    subcategories: Mapped[List["Subcategory"]] = relationship(
        "Subcategory", back_populates="category", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="category_rel", foreign_keys="Transaction.category_id"
    )
    budgets: Mapped[List["Budget"]] = relationship(
        "Budget", back_populates="category", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "color": self.color,
            "budget_limit": float(self.budget_limit) if self.budget_limit is not None else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Subcategory(Base):
    __tablename__ = "subcategories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="subcategories")
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="subcategory_rel", foreign_keys="Transaction.subcategory_id"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category_id": self.category_id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    timestamp: Mapped[datetime.datetime] = mapped_column(nullable=False)
    transaction_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="expense"
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    merchant: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    subcategory_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("subcategories.id", ondelete="SET NULL"), nullable=True
    )
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON stored as text
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        nullable=True, onupdate=func.now()
    )

    # Relationships
    category_rel: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="transactions", foreign_keys=[category_id]
    )
    subcategory_rel: Mapped[Optional["Subcategory"]] = relationship(
        "Subcategory", back_populates="transactions", foreign_keys=[subcategory_id]
    )

    def to_dict(self) -> dict:
        import json
        tags = None
        if self.tags:
            try:
                tags = json.loads(self.tags)
            except (json.JSONDecodeError, TypeError):
                tags = []
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "transaction_type": self.transaction_type,
            "amount": float(self.amount) if self.amount is not None else None,
            "currency": self.currency,
            "description": self.description,
            "merchant": self.merchant,
            "category_id": self.category_id,
            "category": self.category_rel.name if self.category_rel else None,
            "subcategory_id": self.subcategory_id,
            "subcategory": self.subcategory_rel.name if self.subcategory_rel else None,
            "payment_method": self.payment_method,
            "location": self.location,
            "notes": self.notes,
            "tags": tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        nullable=True, onupdate=func.now()
    )

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="budgets")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "month": self.month,
            "year": self.year,
            "allocated_amount": float(self.allocated_amount) if self.allocated_amount is not None else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
