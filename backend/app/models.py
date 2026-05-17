from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TorrentRecord(Base):
    """Persistent record of torrents we've added.

    Resume data is stored as a separate file under settings.resume_dir,
    keyed by infohash, because it can be large and binary.
    """

    __tablename__ = "torrents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    infohash: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    magnet: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
