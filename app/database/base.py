from __future__ import annotations

import uuid
import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass
