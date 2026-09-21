import uuid
from datetime import datetime
from typing import Any, Self

from sqlalchemy import DateTime, delete, func, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.session import SessionLocal


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    """Async counterpart of driver-performance's DPSModel."""

    __abstract__ = True
    __session__ = SessionLocal

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    async def create(self) -> Self:
        """Persist this model instance atomically, including generated-field refresh."""
        async with self.__session__() as session, session.begin():
            session.add(self)
            await session.flush()
            await session.refresh(self)
        return self

    @classmethod
    async def select(cls, query: Any, *, first: bool = False) -> Any:
        """Execute a scalar select query for this model or one of its columns."""
        if first:
            query = query.limit(1)
        async with cls.__session__() as session:
            result = await session.scalars(query)
            data = list(result)
        return data[0] if first and data else (None if first else data)

    @classmethod
    async def get(cls, record_id: uuid.UUID) -> Self | None:
        return await cls.select(select(cls).where(cls.id == record_id), first=True)

    @classmethod
    async def delete(cls, where: Any) -> None:
        async with cls.__session__() as session:
            await session.execute(delete(cls).where(where))
            await session.commit()
