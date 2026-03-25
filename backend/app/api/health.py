"""헬스체크 엔드포인트 — Render 배포 필수."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz():
    return {"ok": True}
