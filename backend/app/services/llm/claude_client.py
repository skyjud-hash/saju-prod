"""Claude API 클라이언트 — 해석 전용. 계산은 하지 않음.

사용법:
    result = await interpret_saju(raw_calculation_json, "comprehensive")
"""

import json
import logging
import time
from collections.abc import AsyncGenerator

import httpx

from app.core.config import settings
from app.services.llm.prompts import CATEGORY_PROMPTS, SYSTEM_PROMPT, build_context

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


async def interpret_saju_stream(
    raw_calc: dict,
    category: str = "comprehensive",
) -> AsyncGenerator[str, None]:
    """Claude API로 사주 해석을 스트리밍 생성.

    raw_calc: 내부 엔진의 계산 결과 JSON
    category: comprehensive | personality | career | study
    """
    if not settings.claude_api_key:
        yield "[오류] CLAUDE_API_KEY가 설정되지 않았습니다."
        return

    context = build_context(raw_calc)
    user_prompt = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["comprehensive"])

    headers = {
        "x-api-key": settings.claude_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.claude_model,
        "max_tokens": 2500,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": f"{context}\n\n---\n{user_prompt}"}],
        "stream": True,
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            async with client.stream("POST", ANTHROPIC_API_URL, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    try:
                        err = json.loads(body).get("error", {}).get("message", body.decode()[:200])
                    except Exception:
                        err = body.decode()[:200]
                    yield f"[Claude API 오류] {err}"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            return
                        try:
                            event = json.loads(data_str)
                            if event.get("type") == "content_block_delta":
                                text = event.get("delta", {}).get("text", "")
                                if text:
                                    yield text
                        except json.JSONDecodeError:
                            continue
    except httpx.ConnectError:
        yield "[오류] Claude API에 연결할 수 없습니다."
    except httpx.TimeoutException:
        yield "[오류] 응답 시간 초과."
    except Exception as e:
        yield f"[오류] {str(e)}"


async def interpret_saju_full(
    raw_calc: dict,
    category: str = "comprehensive",
) -> dict:
    """Claude API로 사주 해석을 한번에 생성 + LLM 로그 데이터 반환.

    Returns:
        {
            "text": "해석 텍스트",
            "log": {
                "provider": "anthropic",
                "model_name": "...",
                "input_tokens": N,
                "output_tokens": N,
                "latency_ms": N,
                "status_code": 200,
                "request_payload": {...},
                "response_payload": {...},
            }
        }
    """
    if not settings.claude_api_key:
        return {"text": "", "log": {"error_message": "CLAUDE_API_KEY not set", "status_code": 0}}

    context = build_context(raw_calc)
    user_prompt = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["comprehensive"])

    headers = {
        "x-api-key": settings.claude_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.claude_model,
        "max_tokens": 2500,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": f"{context}\n\n---\n{user_prompt}"}],
    }

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            resp = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
            latency = int((time.time() - start) * 1000)
            data = resp.json()

            if resp.status_code != 200:
                return {
                    "text": "",
                    "log": {
                        "provider": "anthropic",
                        "model_name": settings.claude_model,
                        "status_code": resp.status_code,
                        "latency_ms": latency,
                        "request_payload": payload,
                        "response_payload": data,
                        "error_message": data.get("error", {}).get("message", ""),
                    },
                }

            text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")

            usage = data.get("usage", {})
            return {
                "text": text,
                "log": {
                    "provider": "anthropic",
                    "model_name": data.get("model", settings.claude_model),
                    "input_tokens": usage.get("input_tokens"),
                    "output_tokens": usage.get("output_tokens"),
                    "latency_ms": latency,
                    "status_code": resp.status_code,
                    "request_payload": {"model": payload["model"], "max_tokens": payload["max_tokens"]},
                    "response_payload": {"id": data.get("id"), "usage": usage},
                },
            }
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return {
            "text": "",
            "log": {
                "provider": "anthropic",
                "model_name": settings.claude_model,
                "latency_ms": latency,
                "error_message": str(e),
                "status_code": 0,
            },
        }


async def check_claude_available() -> bool:
    """Claude API 키가 설정되어 있는지 확인."""
    return bool(settings.claude_api_key)
