from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class LlmLog(Base):
    __tablename__ = "llm_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    result_id = Column(BigInteger, nullable=True)
    provider = Column(String(30), nullable=False, default="anthropic")
    model_name = Column(String(100), nullable=False)
    category = Column(String(50))
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    request_payload = Column(JSONB)
    response_payload = Column(JSONB)
    latency_ms = Column(Integer)
    status_code = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
