# 용사주 (龍四柱) — 프로젝트 개발 가이드

## 절대 원칙

### 사주 계산 엔진 수정 금지 ⛔

`backend/app/services/saju_engine/` 디렉토리 내 **모든 파일**은 절대 수정·삭제·리팩토링하지 않는다.
전통 만세력과 100% 일치 검증 완료 상태이며, 버그로 의심되는 부분이 있어도 반드시 사용자 확인 후 진행한다.

잠금 대상 파일: orchestrator.py, pillar_calculator.py, ten_god_calculator.py,
hidden_stem_calculator.py, relation_calculator.py, daewoon_calculator.py,
gyeokguk_calculator.py, interpreter.py, interpretation_data.py, constants.py,
normalizer.py, dto.py, solar_term_finder.py, timezone_adjuster.py,
twelve_stage_calculator.py, ganzhi_math.py, exceptions.py

### 계산과 해석의 완전 분리

- **계산 엔진** (saju_engine/): 순수 수치/규칙 기반 — 해석 로직 삽입 금지
- **해석 계층** (llm/, prompts.py): 매핑 데이터 + LLM — 계산 로직 삽입 금지

### 표현 원칙

- 과학적 겸손: "~경향과 연결해 해석할 수 있습니다" (1:1 과학적 동일체 단정 금지)
- 건강 면책: 바이오 리듬 케어는 의학적 조언이 아닌 생활 습관 참고 정보
- 궁합 윤리: "궁합이 나쁘다" (X) → "소통 방식의 차이가 큰 부분" (O)

## 커맨드

```bash
# 로컬 실행
./run.command                              # macOS 원클릭 실행 (uvicorn + 브라우저)
cd backend && uvicorn app.main:app --reload --port 8000  # 수동 실행

# 테스트 (아직 미구축 — 추가 필요)
cd backend && python -m pytest             # 백엔드 테스트
# 프론트엔드: 단일 HTML, 별도 빌드/테스트 없음

# 배포
git push origin main                       # Render 자동 배포 (render.yaml 기반)
```

## 기술 스택

| 영역 | 기술 |
|------|------|
| 백엔드 | Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic 2.x |
| 데이터베이스 | SQLite (개발) / PostgreSQL (운영, Render free tier) |
| LLM | Claude API (claude-sonnet-4-20250514), httpx SSE 스트리밍 |
| 프론트엔드 | 단일 HTML (168KB, Vanilla JS + CSS, 빌드 스텝 없음) |
| 배포 | Render PaaS (saju-api + saju-web + saju-db) |

## 프로젝트 구조

```
saju-prod/
├── context.md                    ← 운영 원칙 & 현황 추적 (상세 참조용)
├── CLAUDE.md                     ← 이 파일 (gstack/Claude Code용 개발 가이드)
├── render.yaml                   ← Render 배포 설정
├── run.command                   ← macOS 로컬 실행 스크립트
│
├── frontend/
│   └── index.html                ← 단일 HTML 프론트엔드 (8페이지 SPA)
│
└── backend/
    ├── requirements.txt
    └── app/
        ├── main.py               ← FastAPI 진입점
        ├── api/
        │   ├── saju.py           ← API 엔드포인트 (7개)
        │   └── health.py         ← 헬스체크
        ├── core/
        │   ├── config.py         ← 환경 설정 (Pydantic Settings)
        │   └── database.py       ← DB 연결 (SQLAlchemy)
        ├── models/               ← ORM 모델 4개 (saju_request, saju_result, llm_log, shared_result)
        ├── schemas/              ← Pydantic 요청/응답 스키마
        └── services/
            ├── saju_engine/      ← ⛔ 수정 금지 (만세력 검증 완료, 18파일)
            └── llm/
                ├── claude_client.py  ← Claude API + Ollama 폴백
                └── prompts.py        ← 4대 시스템 프롬프트
```

## API 엔드포인트

Base prefix: `/api/saju`

| Method | Path | 설명 |
|--------|------|------|
| POST | `/calculate` | 사주 계산 (라이브 프리뷰, DB 미저장) |
| POST | `/analyze` | 전체 분석 (계산 + 해석 + DB 저장) |
| GET | `/ai/status` | Claude API 상태 확인 |
| POST | `/ai/interpret?category=` | AI 해석 SSE 스트리밍 |
| POST | `/ai/interpret-full` | AI 전체 해석 (non-streaming) |
| POST | `/share` | 공유 링크 생성 |
| GET | `/share/{share_id}` | 공유 결과 조회 |

## 프론트엔드 구조 (단일 HTML, 8페이지)

| 페이지 ID | 용도 |
|-----------|------|
| `page-home` | 메인 홈 (히어로 + 4카드) |
| `page-saju` | 사주 입력 폼 |
| `page-result` | AI 분석 결과 (2단계 스트리밍) |
| `page-free` | 무료진단 (AI 없이 데이터만) |
| `page-storage` | 보관함 (인물별 그룹핑) |
| `page-brain` | 뇌과학 설문 (15문항 카드 슬라이더) |
| `page-growth` | 자기계발 분석 (사주+뇌과학 전제조건) |
| `page-shared` | 공유 결과 보기 |

## UI 디자인 시스템

- 테마: 다크 럭셔리 (신비롭고, 차분하고, 지적이고, 고급스러운)
- 배경: #0B0A12 (메인), #15132A (서피스), #1E1B35 (카드)
- 강조: #E8A840 (파이어 골드), #7B4FBF (퍼플)
- 오행: 목=#27AE60, 화=#E74C3C, 토=#F39C12, 금=#95A5A6, 수=#3498DB
- 폰트: Noto Serif KR (제목), Noto Sans KR (본문)
- 배제: 무속적/주술적 이미지, 귀여운 캐릭터, 밝은 배경

## 배포 환경

| 서비스 | URL | 플랫폼 |
|--------|-----|--------|
| API | https://saju-api-thnp.onrender.com | Render Web Service (Python) |
| Web | https://saju-web-srjz.onrender.com | Render Static Site |
| DB | PostgreSQL (saju-db) | Render Free Tier |

배포 방식: `git push origin main` → Render가 자동 빌드/배포.
API와 Web은 별도 서비스로 분리되어 있으며, render.yaml로 설정 관리.

## 개발 진행 현황

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | 사주 계산 엔진 정확화 | ✅ 완료 & 🔒 잠금 |
| 2 | LLM 해석 기본 연동 | ✅ 완료 |
| 3 | UI 재설계 + 프롬프트 전환 + 문서화 | ✅ 완료 |
| 3-UI | UI 대개편 8대 요구사항 | ✅ 완료 (2026-03-27) |
| **4** | **뉴로 궁합 (2인 입력 + 교차 분석 + 해석)** | 🔲 대기 |
| **5** | **일진 기반 오늘의 루틴 + 결과 공유 확장** | 🔲 대기 |

## gstack 스킬 & 브라우저

웹 브라우징이 필요할 때는 `/browse` 스킬 또는 `$B <command>`로 browse 바이너리를
직접 실행한다. `mcp__claude-in-chrome__*` 도구는 사용하지 않는다.

**사용 가능한 스킬:**

| Skill | Description |
|-------|-------------|
| `/autoplan` | Auto-review pipeline — CEO, design, eng 리뷰를 순차 실행 |
| `/benchmark` | Performance regression detection (page load, Core Web Vitals) |
| `/browse` | Fast headless browser for QA testing and site dogfooding |
| `/canary` | Post-deploy canary monitoring (console errors, perf regressions) |
| `/careful` | Safety guardrails for destructive commands (rm -rf, DROP TABLE 등) |
| `/codex` | OpenAI Codex CLI wrapper — code review, challenge, second opinion |
| `/connect-chrome` | Launch real Chrome with Side Panel extension auto-loaded |
| `/cso` | Chief Security Officer mode — OWASP Top 10 + STRIDE security audit |
| `/design-consultation` | Design consultation — research landscape, propose design system |
| `/design-review` | Designer's eye QA — visual inconsistency, spacing, AI slop detection + fix |
| `/design-shotgun` | Generate multiple AI design variants, comparison board, feedback |
| `/document-release` | Post-ship documentation update (README, CLAUDE.md 등) |
| `/freeze` | Restrict file edits to a specific directory for the session |
| `/unfreeze` | Clear the freeze boundary, allow edits to all directories |
| `/guard` | Full safety mode — `/careful` + `/freeze` combined |
| `/gstack-upgrade` | Upgrade gstack to the latest version |
| `/investigate` | Systematic debugging — investigate, analyze, hypothesize, implement |
| `/land-and-deploy` | Merge PR → wait for CI/deploy → canary verify production |
| `/learn` | Manage project learnings — review, search, prune, export |
| `/office-hours` | YC Office Hours — startup diagnostic + builder brainstorm |
| `/plan-ceo-review` | CEO/founder-mode plan review — rethink problem, find 10-star product |
| `/plan-design-review` | Designer's eye plan review — rate each dimension 0-10 |
| `/plan-eng-review` | Eng manager-mode plan review — architecture, data flow, edge cases |
| `/qa` | QA test + iterative bug fix with atomic commits |
| `/qa-only` | Report-only QA — structured report with health score, no fixes |
| `/retro` | Weekly engineering retrospective — commit history, work patterns analysis |
| `/review` | Pre-landing PR review — SQL safety, trust boundaries, conditional side effects |
| `/setup-browser-cookies` | Import cookies from real Chromium browser into headless session |
| `/setup-deploy` | Configure deployment settings for `/land-and-deploy` |
| `/ship` | Ship workflow — tests, review diff, VERSION bump, CHANGELOG, PR create |
