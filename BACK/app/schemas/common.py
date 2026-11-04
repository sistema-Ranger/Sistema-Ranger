# BACK/app/schemas/common.py
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, StringConstraints

T = TypeVar("T")

Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_lower=True, max_length=160, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    ),
]


class Page(BaseModel, Generic[T]):  # noqa: UP046  (Python 3.11: sin sintaxis PEP 695)
    items: list[T]
    total: int
    page: int
    size: int
