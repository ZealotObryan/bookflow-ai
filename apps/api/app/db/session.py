from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_settings().database_url,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def set_tenant_context(db: Session, business_id) -> None:
    """Set PostgreSQL RLS context for the current transaction only."""
    if db.get_bind().dialect.name != "postgresql":
        return
    from sqlalchemy import text

    db.execute(
        text("SELECT set_config('app.current_business_id', :business_id, true)"),
        {"business_id": str(business_id)},
    )
