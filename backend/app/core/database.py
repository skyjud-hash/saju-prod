"""SQLAlchemy 엔진 + 세션 팩토리. Postgres 전용."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    **({} if _is_sqlite else {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}),
    **({"connect_args": {"check_same_thread": False}} if _is_sqlite else {}),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI Depends용 DB 세션 제공."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
