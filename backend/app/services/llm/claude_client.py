"""LLM 클라이언트 — Ollama(로컬) / Claude(API) 자동 선택.

사용법:
    result = await interpret_saju_stream(raw_calculation_json, "comprehensive")

로컬 환경: Ollama + EXAONE 3.5 사용 (무료, 빠름)
프로덕션: Claude API 사용 (유료, 고품질)
"""

import json
import logging
import re
import time
from collections.abc import AsyncGenerator

import httpx

from app.core.config import settings
from app.services.llm.prompts import (
    CATEGORY_PROMPTS, SYSTEM_PROMPT, SYSTEM_PROMPT_DETAIL,
    SYSTEM_PROMPT_BRAIN, SYSTEM_PROMPT_BRAIN_DETAIL,
    SYSTEM_PROMPT_GROWTH, SYSTEM_PROMPT_GROWTH_DETAIL,
    build_context, build_context_lite,
    build_brain_context, build_brain_context_lite,
    build_growth_context, build_growth_context_lite,
)

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# 카테고리별 max_tokens 설정
CATEGORY_MAX_TOKENS = {
    "saju_titles": 3000,   # 소제목 + 미니 해석 포함 — 토큰 최적화
    "saju_detail": 1500,   # 개별 해석 1건 — 600~1000자
    "destiny_manual": 4096,
    "growth_routine": 4096,
    "bio_rhythm": 4096,
    "growth_titles": 3000, # 자기계발 소제목 + 미니 해석
    "growth_detail": 1500, # 자기계발 개별 해석 1건
    "brain_titles": 3000,  # 뇌과학 소제목 + 미니 해석
    "brain_detail": 1500,  # 뇌과학 개별 해석 1건
    "comprehensive": 4096,
    "personality": 4096,
    "fortune": 4096,
    "lifestyle": 4096,
}


# ─── Provider 자동 감지 ───

def _use_ollama() -> bool:
    """Ollama를 사용할지 결정. ollama_model이 설정되어 있으면 Ollama 우선."""
    return bool(settings.ollama_model)


# ─── Ollama 스트리밍 ───

async def _ollama_stream(
    raw_calc: dict,
    category: str = "comprehensive",
    title: str = "",
    tag: str = "",
) -> AsyncGenerator[str, None]:
    """Ollama API로 사주 해석을 스트리밍 생성."""
    # 카테고리별 컨텍스트 + 시스템 프롬프트 분기
    if category == "growth_titles":
        context = build_growth_context(raw_calc)
        system_prompt = SYSTEM_PROMPT_GROWTH
    elif category == "growth_detail":
        context = build_growth_context_lite(raw_calc, title=title, tag=tag)
        system_prompt = SYSTEM_PROMPT_GROWTH_DETAIL
    elif category == "brain_titles":
        context = build_brain_context(raw_calc)
        system_prompt = SYSTEM_PROMPT_BRAIN
    elif category == "brain_detail":
        context = build_brain_context_lite(raw_calc, title=title, tag=tag)
        system_prompt = SYSTEM_PROMPT_BRAIN_DETAIL
    elif category == "saju_detail":
        context = build_context_lite(raw_calc, title=title, tag=tag)
        system_prompt = SYSTEM_PROMPT_DETAIL
    else:
        context = build_context(raw_calc)
        system_prompt = SYSTEM_PROMPT

    user_prompt = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["comprehensive"])
    # detail 카테고리인 경우 소제목을 프롬프트에 삽입 (입력 새니타이징)
    if category in ("saju_detail", "brain_detail", "growth_detail") and title:
        import re
        safe_title = re.sub(r'[^\w\s가-힣·\-()（）]', '', title)[:100]
        user_prompt = user_prompt.replace("{title}", safe_title)

    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context}\n\n---\n{user_prompt}"},
        ],
        "stream": True,
        "options": {
            "temperature": 0.6,
            "num_predict": 8192,
            "repeat_penalty": 1.3,
        },
    }

    total_chars = 0
    max_chars = 15000
    prev_chunk = ""

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=5.0)) as client:
            async with client.stream(
                "POST",
                f"{settings.ollama_base_url}/api/chat",
                json=payload,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    yield f"[Ollama 오류] {body.decode()[:200]}"
                    return

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if data.get("done"):
                        break

                    text = data.get("message", {}).get("content", "")
                    if not text:
                        continue

                    # <thought> 태그 필터링 (일부 모델)
                    text = re.sub(r"<thought>.*?</thought>", "", text, flags=re.DOTALL)
                    # HTML 태그 제거
                    text = re.sub(r"<[^>]+>", "", text)

                    if not text:
                        continue

                    total_chars += len(text)
                    if total_chars > max_chars:
                        break

                    # 반복 감지 (같은 25자 이상 구간이 반복되면 중단)
                    if len(text) >= 25 and text == prev_chunk:
                        logger.warning("반복 감지, 스트리밍 중단")
                        break
                    prev_chunk = text

                    yield text

    except httpx.ConnectError:
        yield "[오류] Ollama 서버에 연결할 수 없습니다. (http://localhost:11434)"
    except httpx.TimeoutException:
        yield "[오류] Ollama 응답 시간 초과."
    except Exception as e:
        yield f"[오류] {str(e)}"


# ─── Claude 스트리밍 ───

async def _claude_stream(
    raw_calc: dict,
    category: str = "comprehensive",
    title: str = "",
    tag: str = "",
) -> AsyncGenerator[str, None]:
    """Claude API로 사주 해석을 스트리밍 생성."""
    if not settings.claude_api_key:
        yield "[오류] CLAUDE_API_KEY가 설정되지 않았습니다."
        return

    # 카테고리별 컨텍스트 + 시스템 프롬프트 분기
    if category == "growth_titles":
        context = build_growth_context(raw_calc)
        system_prompt = SYSTEM_PROMPT_GROWTH
    elif category == "growth_detail":
        context = build_growth_context_lite(raw_calc, title=title, tag=tag)
        system_prompt = SYSTEM_PROMPT_GROWTH_DETAIL
    elif category == "brain_titles":
        context = build_brain_context(raw_calc)
        system_prompt = SYSTEM_PROMPT_BRAIN
    elif category == "brain_detail":
        context = build_brain_context_lite(raw_calc, title=title, tag=tag)
        system_prompt = SYSTEM_PROMPT_BRAIN_DETAIL
    elif category == "saju_detail":
        context = build_context_lite(raw_calc, title=title, tag=tag)
        system_prompt = SYSTEM_PROMPT_DETAIL
    else:
        context = build_context(raw_calc)
        system_prompt = SYSTEM_PROMPT

    user_prompt = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["comprehensive"])
    # detail 카테고리인 경우 소제목을 프롬프트에 삽입 (입력 새니타이징)
    if category in ("saju_detail", "brain_detail", "growth_detail") and title:
        import re
        safe_title = re.sub(r'[^\w\s가-힣·\-()（）]', '', title)[:100]
        user_prompt = user_prompt.replace("{title}", safe_title)

    max_tokens = CATEGORY_MAX_TOKENS.get(category, 4096)

    headers = {
        "x-api-key": settings.claude_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.claude_model,
        "max_tokens": max_tokens,
        "system": system_prompt,
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


# ─── 통합 인터페이스 ───

async def interpret_saju_stream(
    raw_calc: dict,
    category: str = "comprehensive",
    title: str = "",
    tag: str = "",
) -> AsyncGenerator[str, None]:
    """사주 해석 스트리밍 — Ollama 또는 Claude 자동 선택."""
    if _use_ollama():
        logger.info("LLM 프로바이더: Ollama (%s), category=%s", settings.ollama_model, category)
        async for chunk in _ollama_stream(raw_calc, category, title=title, tag=tag):
            yield chunk
    else:
        logger.info("LLM 프로바이더: Claude (%s), category=%s", settings.claude_model, category)
        async for chunk in _claude_stream(raw_calc, category, title=title, tag=tag):
            yield chunk


async def interpret_saju_full(
    raw_calc: dict,
    category: str = "comprehensive",
) -> dict:
    """사주 해석 전체 (비스트리밍) — 로그 데이터 포함."""
    if _use_ollama():
        # Ollama: 스트리밍을 모아서 전체 텍스트로 반환
        start = time.time()
        text_parts = []
        async for chunk in _ollama_stream(raw_calc, category):
            text_parts.append(chunk)
        latency = int((time.time() - start) * 1000)
        text = "".join(text_parts)
        return {
            "text": text,
            "log": {
                "provider": "ollama",
                "model_name": settings.ollama_model,
                "input_tokens": None,
                "output_tokens": len(text),
                "latency_ms": latency,
                "status_code": 200 if text else 0,
            },
        }
    else:
        # Claude API (기존 로직)
        return await _claude_interpret_full(raw_calc, category)


async def _claude_interpret_full(raw_calc: dict, category: str) -> dict:
    """Claude API 비스트리밍 호출 + LLM 로그."""
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
        "max_tokens": 4096,
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
    """LLM 사용 가능 여부 확인 — Ollama 또는 Claude."""
    if _use_ollama():
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    return any(m.get("name", "").startswith(settings.ollama_model.split(":")[0])
                              for m in models)
        except Exception:
            return False
    return bool(settings.claude_api_key)
