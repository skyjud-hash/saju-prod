"""공유 결과 모델 — UUID 기반 공유 링크."""

import uuid

from sqlalchemy import Column, DateTime, Integer, JSON, String, func
from app.core.database import Base


class SharedResult(Base):
    __tablename__ = "shared_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    share_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    input_name = Column(String(100), nullable=True)
    birth_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    gender = Column(String(10), nullable=True)
    raw_calculation = Column(JSON, nullable=False)
    ai_texts = Column(JSON, nullable=True)  # {"personality": "...", "comprehensive": "..."}
    created_at = Column(DateTime, nullable=False, server_default=func.now())
