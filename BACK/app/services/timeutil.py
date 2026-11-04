# BACK/app/services/timeutil.py
import re
from datetime import UTC, datetime, timedelta

from fastapi import Query

from app.errors import AppError

_RELATIVE = re.compile(r"^now(?:-(\d+)([smhd]))?$")
_UNITS = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}

RANGES: dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}


def utcnow() -> datetime:
    return datetime.now(UTC)


def parse_time(value: str | None, field: str = "from") -> datetime | None:
    """Acepta ISO-8601 (sin zona → UTC) o expresiones relativas: `now`, `now-15m`, `now-6h`."""
    if value is None or value == "":
        return None
    value = value.strip()
    match = _RELATIVE.match(value)
    if match:
        amount, unit = match.groups()
        delta = timedelta(**{_UNITS[unit]: int(amount)}) if amount else timedelta()
        return utcnow() - delta
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AppError(
            422, f"Fecha inválida en '{field}': usa ISO-8601 o now-15m", "INVALID_DATE"
        ) from exc
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


class TimeRange:
    """Dependencia para los parámetros `from` / `to`."""

    def __init__(
        self,
        from_: str | None = Query(None, alias="from", description="ISO-8601 o now-15m"),
        to: str | None = Query(None, description="ISO-8601 o now"),
    ) -> None:
        self.start = parse_time(from_, "from")
        self.end = parse_time(to, "to")
        if self.start and self.end and self.start > self.end:
            raise AppError(400, "'from' debe ser anterior a 'to'", "INVALID_RANGE")

    def with_defaults(self, default_span: timedelta) -> tuple[datetime, datetime]:
        end = self.end or utcnow()
        return self.start or end - default_span, end
