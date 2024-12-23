from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass


class Base(AsyncAttrs, DeclarativeBase, MappedAsDataclass):
    """Base class for all SQLAlchemy models."""

    pass
