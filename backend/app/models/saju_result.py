from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, String, Text, func
from app.core.database import Base


class SajuResult(Base):
    __tablename__ = "saju_results"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    request_id = Column(BigInteger, ForeignKey("saju_requests.id", ondelete="CASCADE"), nullable=False)
    prompt_version_id = Column(BigInteger, nullable=True)
    raw_calculation_json = Column(JSON, nullable=False)
    interpretation_json = Column(JSON, nullable=True)
    final_text = Column(Text, nullable=True)
    result_status = Column(String(20), nullable=False, default="calculated")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
