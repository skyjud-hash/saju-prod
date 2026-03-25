from sqlalchemy import BigInteger, Boolean, Column, DateTime, String, func
from app.core.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    plan_code = Column(String(50), nullable=False)
    starts_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
