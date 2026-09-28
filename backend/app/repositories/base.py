"""Repository base class.

Repositories own: translating between domain objects and SQLAlchemy rows,
and running queries. They do NOT own: business rules (e.g. which status
transitions are legal — that's `app.services`), request/response shaping
(that's `app.schemas`), or committing/rolling back transactions across
multiple repositories in one request (that's the calling service, which
owns the unit-of-work boundary via the shared `Session`).

Any unexpected SQLAlchemy error must be caught at the service boundary
and re-raised as `app.core.exceptions.PersistenceError` — repositories
themselves are allowed to let `SQLAlchemyError` propagate up to that
boundary.
"""

from typing import Generic, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, instance: ModelT) -> ModelT:
        self.db.add(instance)
        self.db.flush()
        return instance
