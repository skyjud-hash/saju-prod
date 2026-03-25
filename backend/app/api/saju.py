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
from app.schemas.saju import AiInterpretRequest, SajuAnalyzeRequest, SajuAnalyzeResponse, InputSummary
from app.services.saju_engine.orchestrator import calculate_saju
from app.services.llm.claude_client import check_claude_available, interpret_saju_full, interpret_saju_stream

logger = logging.getLogger(__name__)
router = APIRouter()


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
    """Claude API 상태 확인."""
    available = await check_claude_available()
    return {
        "available": available,
        "provider": "claude" if available else None,
        "message": "Claude API 연결됨" if available else "CLAUDE_API_KEY가 설정되지 않았습니다.",
    }


@router.post("/ai-interpret")
async def ai_interpret(
    payload: AiInterpretRequest,
    db: Session = Depends(get_db),
):
    """Claude로 사주 해석 (SSE 스트리밍).

    1. DB에서 raw_calculation_json 조회
    2. Claude API에 전달 (계산 재수행 금지)
    3. 스트리밍 응답
    """
    # DB에서 결과 조회
    result = db.query(SajuResult).filter(SajuResult.id == payload.result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다.")

    available = await check_claude_available()
    if not available:
        raise HTTPException(status_code=503, detail="CLAUDE_API_KEY가 설정되지 않았습니다.")

    raw_calc = result.raw_calculation_json

    async def event_stream():
        async for chunk in interpret_saju_stream(raw_calc, payload.category):
            for line in chunk.split("\n"):
                yield f"data: {line}\n"
            yield "\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/ai-interpret-full")
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
