"""사주 API 입출력 스키마."""

from typing import Any

from pydantic import BaseModel, Field


class SajuAnalyzeRequest(BaseModel):
    """POST /api/saju/analyze 입력."""
    name: str | None = Field(None, max_length=100, examples=["홍길동"])
    birth_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", examples=["1981-09-11"])
    birth_time: str | None = Field(None, pattern=r"^\d{2}:\d{2}$", examples=["07:00"])
    gender: str = Field(..., examples=["male", "female"])
    calendar_type: str = Field("solar", examples=["solar", "lunar"])
    is_leap_month: bool = False
    birthplace: str | None = Field(None, examples=["Seoul"])


class InputSummary(BaseModel):
    name: str | None
    birth_date: str
    birth_time: str | None
    gender: str
    calendar_type: str


class SajuAnalyzeResponse(BaseModel):
    """POST /api/saju/analyze 응답."""
    request_id: int
    result_id: int
    input_summary: InputSummary
    raw_calculation: dict[str, Any]
    interpretation: list[dict[str, Any]]
    result_status: str


class AiInterpretRequest(BaseModel):
    """POST /api/saju/ai-interpret 입력."""
    result_id: int
    category: str = Field("comprehensive", examples=["comprehensive", "personality", "career", "study"])
