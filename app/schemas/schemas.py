from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class TransactionCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Transaction amount, must be positive")
    transaction_type: str = Field(default="expense", description="Type: expense or income")
    category: Optional[str] = Field(default=None, description="Category name")
    subcategory: Optional[str] = Field(default=None, description="Subcategory name")
    description: Optional[str] = Field(default=None, description="Transaction description")
    merchant: Optional[str] = Field(default=None, description="Merchant name")
    timestamp: Optional[str] = Field(default=None, description="ISO format datetime string")
    currency: str = Field(default="INR", description="Currency code")
    payment_method: Optional[str] = Field(default=None, description="Payment method used")
    location: Optional[str] = Field(default=None, description="Transaction location")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    tags: Optional[List[str]] = Field(default=None, description="List of tags")

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, v: str) -> str:
        allowed = {"expense", "income", "transfer"}
        if v.lower() not in allowed:
            raise ValueError(f"transaction_type must be one of {allowed}")
        return v.lower()


class TransactionUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0)
    transaction_type: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)
    subcategory: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    merchant: Optional[str] = Field(default=None)
    timestamp: Optional[str] = Field(default=None)
    currency: Optional[str] = Field(default=None)
    payment_method: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"expense", "income", "transfer"}
        if v.lower() not in allowed:
            raise ValueError(f"transaction_type must be one of {allowed}")
        return v.lower()


class TransactionResponse(BaseModel):
    id: str
    timestamp: Optional[str]
    transaction_type: str
    amount: float
    currency: str
    description: Optional[str]
    merchant: Optional[str]
    category_id: Optional[str]
    category: Optional[str]
    subcategory_id: Optional[str]
    subcategory: Optional[str]
    payment_method: Optional[str]
    location: Optional[str]
    notes: Optional[str]
    tags: Optional[List[str]]
    created_at: Optional[str]
    updated_at: Optional[str]


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: Optional[str] = Field(default=None, max_length=50)
    color: Optional[str] = Field(default=None, max_length=50)
    budget_limit: Optional[float] = Field(default=None, gt=0)


class SubcategoryResponse(BaseModel):
    id: str
    category_id: str
    name: str
    created_at: Optional[str]


class CategoryResponse(BaseModel):
    id: str
    name: str
    icon: Optional[str]
    color: Optional[str]
    budget_limit: Optional[float]
    created_at: Optional[str]
    updated_at: Optional[str]
    subcategories: List[SubcategoryResponse] = Field(default_factory=list)


class SubcategoryCreate(BaseModel):
    category_id: str = Field(..., description="ID of the parent category")
    name: str = Field(..., min_length=1, max_length=100)


class BudgetCreate(BaseModel):
    category_id: str = Field(..., description="ID of the category")
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    year: int = Field(..., ge=2000, description="Year")
    allocated_amount: float = Field(..., gt=0, description="Budget amount")


class BudgetResponse(BaseModel):
    id: str
    category_id: str
    category_name: Optional[str]
    month: int
    year: int
    allocated_amount: float
    created_at: Optional[str]
    updated_at: Optional[str]


class SearchFilters(BaseModel):
    start_date: Optional[str] = Field(default=None, description="Start date ISO format")
    end_date: Optional[str] = Field(default=None, description="End date ISO format")
    category: Optional[str] = Field(default=None, description="Category name filter")
    subcategory: Optional[str] = Field(default=None, description="Subcategory name filter")
    merchant: Optional[str] = Field(default=None, description="Merchant name filter")
    min_amount: Optional[float] = Field(default=None, gt=0)
    max_amount: Optional[float] = Field(default=None, gt=0)
    transaction_type: Optional[str] = Field(default=None)
