import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, ARRAY, Text, SmallInteger, Boolean, BigInteger, func
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(10), default="open")
    next_turn: Mapped[str] = mapped_column(String(10), default="self")
    pending_shot: Mapped[str | None] = mapped_column(String(4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    ships: Mapped[list["OwnShip"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    shots: Mapped[list["Shot"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class OwnShip(Base):
    __tablename__ = "own_ships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    length: Mapped[int] = mapped_column(SmallInteger)
    coordinates: Mapped[list[str]] = mapped_column(ARRAY(Text))
    hit_coordinates: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    sunk: Mapped[bool] = mapped_column(Boolean, default=False)

    session: Mapped["Session"] = relationship(back_populates="ships")


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    direction: Mapped[str] = mapped_column(String(10))  # 'own' | 'opponent'
    coordinate: Mapped[str] = mapped_column(String(4))
    result: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="shots")
