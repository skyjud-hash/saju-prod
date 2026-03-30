"""Test configuration — patch DB to use in-memory SQLite."""

import os
os.environ["DATABASE_URL"] = "sqlite:///./test_saju.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.core.database as db_mod
from app.core.database import Base, get_db

# Replace the production engine with a test engine
test_engine = create_engine(
    "sqlite:///./test_saju.db",
    connect_args={"check_same_thread": False},
)
db_mod.engine = test_engine
TestSession = sessionmaker(bind=test_engine)

# Import app AFTER patching the engine
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client(setup_db):
    session = TestSession()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    session.close()
    app.dependency_overrides.clear()
