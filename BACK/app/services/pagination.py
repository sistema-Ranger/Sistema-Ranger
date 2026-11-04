# BACK/app/services/pagination.py
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def paginate(db: Session, stmt: Select, page: int, size: int) -> dict[str, Any]:
    """Ejecuta `stmt` paginado → {items, total, page, size} (convención de 05)."""
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = db.scalars(stmt.limit(size).offset((page - 1) * size)).unique().all()
    return {"items": list(items), "total": total, "page": page, "size": size}
