"""사주 앱 FastAPI 메인 — 실서비스 구조."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.saju import router as saju_router
from app.core.config import settings
from app.core.database import Base, engine

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# 앱 생성
app = FastAPI(
    title="사주와 입시 API",
    description="사주명리학 기반 진로진학 상담 시스템",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(health_router)
app.include_router(saju_router, prefix="/api/saju", tags=["saju"])


@app.on_event("startup")
def on_startup():
    """서버 시작 시 테이블 자동 생성."""
    Base.metadata.create_all(bind=engine)
    logger.info("DB tables ensured. APP_ENV=%s", settings.app_env)


@app.get("/")
def root():
    return {
        "service": "사주와 입시 API",
        "version": "1.0.0",
        "env": settings.app_env,
        "docs": "/docs" if not settings.is_production else "disabled",
    }
