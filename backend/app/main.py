"""사주 앱 FastAPI 메인 — 실서비스 구조."""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

# 프론트엔드 경로 (backend/ 기준으로 ../frontend/)
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

# 앱 생성
app = FastAPI(
    title="사주 분석 API",
    description="사주명리학 기반 사주팔자 분석 시스템",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    logger.info("Frontend dir: %s (exists=%s)", FRONTEND_DIR, FRONTEND_DIR.exists())


@app.get("/")
def serve_index():
    """프론트엔드 index.html 제공."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file, media_type="text/html")
    return {
        "service": "사주 분석 API",
        "version": "1.0.0",
        "docs": "/docs",
        "note": "프론트엔드 파일을 찾을 수 없습니다.",
    }


# 프론트엔드 정적 파일 (public/ 디렉토리 — CSS, JS, 이미지 등)
if (FRONTEND_DIR / "public").exists():
    app.mount("/public", StaticFiles(directory=str(FRONTEND_DIR / "public")), name="public")

# 프론트엔드 이미지 파일
if (FRONTEND_DIR / "images").exists():
    app.mount("/images", StaticFiles(directory=str(FRONTEND_DIR / "images")), name="images")
