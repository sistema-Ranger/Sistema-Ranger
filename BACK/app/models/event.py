# BACK/app/models/event.py
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EventLevel, pg_enum
from app.models.host import Host


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    host_id: Mapped[int] = mapped_column(ForeignKey("hosts.id", ondelete="CASCADE"))
    ts: Mapped[datetime]
    level: Mapped[EventLevel] = mapped_column(pg_enum(EventLevel, "event_level"))
    source: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str | None] = mapped_column(String(64))
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    host: Mapped[Host] = relationship()

    @property
    def hostname(self) -> str:
        return self.host.hostname


Index("ix_events_host_ts", Event.host_id, Event.ts.desc())
Index("ix_events_level_ts", Event.level, Event.ts.desc())
Index(
    "ix_events_msg_trgm",
    Event.message,
    postgresql_using="gin",
    postgresql_ops={"message": "gin_trgm_ops"},
)
