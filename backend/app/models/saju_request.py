from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, ForeignKey, String, Text, Time, func
from app.core.database import Base


class SajuRequest(Base):
    __tablename__ = "saju_requests"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    input_name = Column(String(100))
    birth_date = Column(Date, nullable=False)
    birth_time = Column(Time, nullable=True)
    gender = Column(String(10), nullable=False)
    calendar_type = Column(String(10), nullable=False, default="solar")
    is_leap_month = Column(Boolean, default=False)
    birthplace = Column(String(255))
    request_ip = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
