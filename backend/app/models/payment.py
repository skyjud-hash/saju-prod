from sqlalchemy import BigInteger, Column, DateTime, Integer, String, func
from app.core.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=True)
    amount = Column(Integer, nullable=False)
    currency = Column(String(10), default="KRW")
    payment_method = Column(String(50))
    payment_key = Column(String(255))
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
