# BACK/app/services/events.py
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Event, EventLevel
from app.services.pagination import paginate


@dataclass
class EventFilters:
    q: str | None = None
    host_id: int | None = None
    levels: list[EventLevel] | None = None
    source: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    def apply(self, stmt: Select, include_level: bool = True) -> Select:
        if self.q:
            # ILIKE usa el índice trigram ix_events_msg_trgm
            escaped = self.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(Event.message.ilike(f"%{escaped}%", escape="\\"))
        if self.host_id is not None:
            stmt = stmt.where(Event.host_id == self.host_id)
        if include_level and self.levels:
            stmt = stmt.where(Event.level.in_(self.levels))
        if self.source:
            stmt = stmt.where(Event.source == self.source)
        if self.start:
            stmt = stmt.where(Event.ts >= self.start)
        if self.end:
            stmt = stmt.where(Event.ts <= self.end)
        return stmt


def list_events(db: Session, filters: EventFilters, page: int, size: int) -> dict[str, Any]:
    stmt = filters.apply(
        select(Event).options(joinedload(Event.host)).order_by(Event.ts.desc(), Event.id.desc())
    )
    return paginate(db, stmt, page, size)


def summary(db: Session, filters: EventFilters) -> dict[str, int]:
    """Conteo por nivel; ignora el filtro de nivel para que los 4 contadores tengan sentido."""
    stmt = filters.apply(
        select(Event.level, func.count()).group_by(Event.level), include_level=False
    )
    counts = {level.value: 0 for level in EventLevel}
    for level, count in db.execute(stmt):
        counts[level.value] = count
    return counts
