"""사주 분석 API — 계산 엔진 + Claude 해석 엔진 분리.

핵심 원칙:
- 계산은 내부 엔진(saju_engine)이 수행
- Claude는 자연어 해석만 수행
- raw_calculation_json / interpretation_json / final_text 분리 저장
"""

import logging
from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.saju_request import SajuRequest
from app.models.saju_result import SajuResult
from app.models.llm_log import LlmLog
from app.models.shared_result import SharedResult
from app.schemas.saju import AiInterpretRequest, SajuAnalyzeRequest, SajuAnalyzeResponse, InputSummary
from app.services.saju_engine.orchestrator import calculate_saju
from app.services.llm.claude_client import check_claude_available, interpret_saju_full, interpret_saju_stream

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/calculate")
def calculate_preview(payload: dict):
    """사주 라이브 프리뷰 — DB 저장 없이 순수 계산만 수행."""
    try:
        raw_calc = calculate_saju(
            birth_year=payload.get("birth_year"),
            birth_month=payload.get("birth_month"),
            birth_day=payload.get("birth_day"),
            birth_hour=payload.get("birth_hour"),
            birth_minute=payload.get("birth_minute"),
            gender=payload.get("gender_for_daewoon", "male"),
            calendar_type=payload.get("calendar_type", "solar"),
        )
        return raw_calc
    except Exception as e:
        logger.error("계산 오류: %s", e)
        raise HTTPException(status_code=500, detail=f"사주 계산 오류: {e}") from e


@router.post("/analyze", response_model=SajuAnalyzeResponse)
def analyze_saju(
    payload: SajuAnalyzeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """사주 분석 엔드투엔드: 입력 → 계산 → 템플릿 해석 → DB 저장 → 응답."""

    # 1. 입력 파싱
    parts = payload.birth_date.split("-")
    birth_year, birth_month, birth_day = int(parts[0]), int(parts[1]), int(parts[2])
    birth_hour, birth_minute = None, None
    if payload.birth_time:
        tp = payload.birth_time.split(":")
        birth_hour, birth_minute = int(tp[0]), int(tp[1])

    # 2. DB에 요청 저장
    saju_req = SajuRequest(
        input_name=payload.name,
        birth_date=date(birth_year, birth_month, birth_day),
        birth_time=time(birth_hour, birth_minute) if birth_hour is not None else None,
        gender=payload.gender,
        calendar_type=payload.calendar_type,
        is_leap_month=payload.is_leap_month,
        birthplace=payload.birthplace,
        request_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )
    db.add(saju_req)
    db.flush()

    # 3. 계산 엔진 호출 (Claude 아님!)
    try:
        raw_calc = calculate_saju(
            birth_year=birth_year,
            birth_month=birth_month,
            birth_day=birth_day,
            birth_hour=birth_hour,
            birth_minute=birth_minute,
            gender=payload.gender,
            calendar_type=payload.calendar_type,
        )
    except Exception as e:
        logger.error("계산 오류: %s", e)
        raise HTTPException(status_code=500, detail=f"사주 계산 오류: {e}") from e

    # 4. 결과 저장 — raw_calculation_json + interpretation_json 분리
    interpretation = raw_calc.pop("interpretation", [])
    saju_result = SajuResult(
        request_id=saju_req.id,
        raw_calculation_json=raw_calc,
        interpretation_json=interpretation,
        result_status="calculated",
    )
    db.add(saju_result)
    db.commit()
    db.refresh(saju_result)

    # 5. 응답
    return SajuAnalyzeResponse(
        request_id=saju_req.id,
        result_id=saju_result.id,
        input_summary=InputSummary(
            name=payload.name,
            birth_date=payload.birth_date,
            birth_time=payload.birth_time,
            gender=payload.gender,
            calendar_type=payload.calendar_type,
        ),
        raw_calculation=raw_calc,
        interpretation=interpretation,
        result_status="calculated",
    )


@router.get("/ai/status")
async def ai_status():
    """LLM 상태 확인 — Ollama 또는 Claude."""
    from app.core.config import settings
    available = await check_claude_available()
    if settings.ollama_model:
        provider = "ollama" if available else None
        msg = f"Ollama ({settings.ollama_model}) 연결됨" if available else "Ollama 서버에 연결할 수 없습니다."
    else:
        provider = "claude" if available else None
        msg = "Claude API 연결됨" if available else "CLAUDE_API_KEY가 설정되지 않았습니다."
    return {"available": available, "provider": provider, "message": msg}


@router.post("/ai/interpret")
async def ai_interpret(
    request: Request,
    category: str = Query("destiny_manual"),
    title: str = Query(""),
    tag: str = Query(""),
):
    """Claude로 사주 해석 (SSE 스트리밍).

    프론트엔드에서 raw_calculation을 직접 전달받아 Claude에 보냄.
    category는 query parameter로 받음.
    title은 saju_detail 카테고리에서 소제목 텍스트를 전달할 때 사용.
    tag는 saju_detail에서 소제목의 카테고리 태그 (#기질, #커리어 등)를 전달.
    """
    available = await check_claude_available()
    if not available:
        raise HTTPException(status_code=503, detail="CLAUDE_API_KEY가 설정되지 않았습니다.")

    raw_calc = await request.json()

    async def event_stream():
        async for chunk in interpret_saju_stream(raw_calc, category, title=title, tag=tag):
            for line in chunk.split("\n"):
                yield f"data: {line}\n"
            yield "\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/ai/interpret-full")
async def ai_interpret_full(
    payload: AiInterpretRequest,
    db: Session = Depends(get_db),
):
    """Claude로 사주 해석 (비스트리밍) + DB 저장 + LLM 로그.

    결과를 saju_results.final_text에 저장하고 llm_logs에 기록.
    """
    result = db.query(SajuResult).filter(SajuResult.id == payload.result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다.")

    available = await check_claude_available()
    if not available:
        raise HTTPException(status_code=503, detail="CLAUDE_API_KEY가 설정되지 않았습니다.")

    # Claude 호출
    ai_result = await interpret_saju_full(result.raw_calculation_json, payload.category)

    # final_text 저장
    result.final_text = ai_result["text"]
    result.result_status = "interpreted" if ai_result["text"] else "failed"

    # LLM 로그 저장
    log_data = ai_result["log"]
    llm_log = LlmLog(
        result_id=result.id,
        provider=log_data.get("provider", "anthropic"),
        model_name=log_data.get("model_name", ""),
        category=payload.category,
        input_tokens=log_data.get("input_tokens"),
        output_tokens=log_data.get("output_tokens"),
        latency_ms=log_data.get("latency_ms"),
        status_code=log_data.get("status_code"),
        request_payload=log_data.get("request_payload"),
        response_payload=log_data.get("response_payload"),
        error_message=log_data.get("error_message"),
    )
    db.add(llm_log)
    db.commit()

    return {
        "result_id": result.id,
        "category": payload.category,
        "final_text": ai_result["text"],
        "status": result.result_status,
        "tokens": {
            "input": log_data.get("input_tokens"),
            "output": log_data.get("output_tokens"),
        },
    }


# ===== 공유 기능 =====

@router.post("/share")
async def create_share(
    request: Request,
    db: Session = Depends(get_db),
):
    """사주 결과를 공유 링크로 저장."""
    payload = await request.json()

    shared = SharedResult(
        input_name=payload.get("input_name"),
        birth_date=payload.get("birth_date"),
        gender=payload.get("gender"),
        raw_calculation=payload.get("raw_calculation", {}),
        ai_texts=payload.get("ai_texts"),
    )
    db.add(shared)
    db.commit()
    db.refresh(shared)

    return {
        "share_id": shared.share_id,
        "share_url": f"/share/{shared.share_id}",
    }


@router.get("/share/{share_id}")
def get_shared(share_id: str, db: Session = Depends(get_db)):
    """공유된 사주 결과 조회."""
    shared = db.query(SharedResult).filter(SharedResult.share_id == share_id).first()
    if not shared:
        raise HTTPException(status_code=404, detail="공유된 결과를 찾을 수 없습니다.")

    return {
        "share_id": shared.share_id,
        "input_name": shared.input_name,
        "birth_date": shared.birth_date,
        "gender": shared.gender,
        "raw_calculation": shared.raw_calculation,
        "ai_texts": shared.ai_texts,
        "created_at": shared.created_at.isoformat() if shared.created_at else None,
    }
