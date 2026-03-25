from sqlalchemy import BigInteger, Boolean, Column, DateTime, String, Text, func
from app.core.database import Base


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    version_code = Column(String(50), unique=True, nullable=False)
    category = Column(String(50), nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_prompt = Column(Text, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
