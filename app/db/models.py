from typing import Any, ClassVar, Self

from sqlalchemy import BigInteger, CheckConstraint, Integer, String, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BaseModel
from app.db.session import SessionLocal
from app.services.palette import palette_rgb_totals


class ColorStatistics(Base):
    """Singleton row containing the aggregate contribution of every image palette."""

    __tablename__ = "color_statistics"
    __table_args__ = (CheckConstraint("id = 1", name="ck_color_statistics_singleton"),)

    SINGLETON_ID: ClassVar[int] = 1
    __session__ = SessionLocal

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=SINGLETON_ID,
        server_default="1",
    )
    total_red: Mapped[int] = mapped_column(BigInteger, server_default="0", nullable=False)
    total_green: Mapped[int] = mapped_column(BigInteger, server_default="0", nullable=False)
    total_blue: Mapped[int] = mapped_column(BigInteger, server_default="0", nullable=False)

    @classmethod
    async def get_global(cls) -> Self | None:
        """Return the one row that holds service-wide colour totals."""
        async with cls.__session__() as session:
            return await session.scalar(select(cls).where(cls.id == cls.SINGLETON_ID))

    @classmethod
    async def apply_delta(
        cls,
        session: AsyncSession,
        *,
        red: int,
        green: int,
        blue: int,
    ) -> None:
        """Atomically add a palette contribution while the caller owns a transaction."""
        result = await session.execute(
            sa_update(cls)
            .where(cls.id == cls.SINGLETON_ID)
            .values(
                total_red=cls.total_red + red,
                total_green=cls.total_green + green,
                total_blue=cls.total_blue + blue,
            )
        )
        if result.rowcount != 1:
            raise RuntimeError("The color statistics row is missing")


class ImageRecord(BaseModel):
    __tablename__ = "images"

    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(50), default="image/jpeg")
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    palette: Mapped[list[str]] = mapped_column(JSONB)

    async def create(self) -> Self:
        """Persist an image and its RGB aggregate in one transaction."""
        red, green, blue = palette_rgb_totals(self.palette)
        async with self.__session__() as session, session.begin():
            session.add(self)
            await session.flush()
            await ColorStatistics.apply_delta(
                session,
                red=red,
                green=green,
                blue=blue,
            )
            await session.refresh(self)
        return self

    @classmethod
    async def delete(cls, where: Any) -> list[Self]:
        """Delete images and subtract their palette totals in one transaction."""
        async with cls.__session__() as session, session.begin():
            images = list(await session.scalars(select(cls).where(where).with_for_update()))
            if not images:
                return []

            totals = [0, 0, 0]
            for image in images:
                red, green, blue = palette_rgb_totals(image.palette)
                totals[0] += red
                totals[1] += green
                totals[2] += blue

            await ColorStatistics.apply_delta(
                session,
                red=-totals[0],
                green=-totals[1],
                blue=-totals[2],
            )
            await session.execute(sa_delete(cls).where(where))
        return images
