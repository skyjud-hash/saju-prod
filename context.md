# context.md — 용사주 프로젝트 구동 원칙 & 현황 추적

> 이 문서는 개발 중 항상 참조해야 하는 핵심 원칙, 파일 구조, 현재 상태를 한눈에 파악하기 위한 운영 문서입니다.
> 최종 갱신: 2026-03-27 (세션 4차 업데이트 — UI 대개편 8대 요구사항 구현 완료)

---

## 1. 절대 원칙 (⛔ 위반 불가)

### 1-1. 사주 계산 엔진 수정 금지

`backend/app/services/saju_engine/` 디렉토리 내 **모든 파일**은 절대 수정·삭제·리팩토링하지 않는다.

- 전통 만세력과 **100% 일치** 검증 완료 상태
- 버그로 의심되는 부분이 있어도 **반드시 사용자 확인 후** 진행
- 해당 파일 목록:
  - `orchestrator.py` — 전체 계산 오케스트레이션
  - `pillar_calculator.py` — 4주(연월일시) 산출
  - `ten_god_calculator.py` — 십성 배치
  - `hidden_stem_calculator.py` — 지장간 산출
  - `relation_calculator.py` — 합충형해파 분석
  - `daewoon_calculator.py` — 대운 산출
  - `gyeokguk_calculator.py` — 격국 분석
  - `interpreter.py` — 템플릿 해석
  - `interpretation_data.py` — 해석 매핑 데이터
  - `constants.py` — 상수 정의
  - `normalizer.py` — 입력 정규화
  - `dto.py` — 데이터 전송 객체
  - `solar_term_finder.py` — 절입 시각 계산
  - `timezone_adjuster.py` — 시간대 보정
  - `twelve_stage_calculator.py` — 십이운성 산출
  - `ganzhi_math.py` — 간지 수학 연산
  - `exceptions.py` — 예외 정의

### 1-2. 계산과 해석의 완전 분리

- **계산 엔진**: 순수 수치/규칙 기반 (saju_engine/)
- **해석 계층**: 매핑 데이터 + LLM (llm/, prompts.py)
- 두 영역은 독립적으로 유지, 계산 엔진에 해석 로직을 삽입하지 않는다

### 1-3. 표현 원칙

- **과학적 겸손**: "~경향과 연결해 해석할 수 있습니다" (1:1 과학적 동일체 단정 금지)
- **건강 면책**: 바이오 리듬 케어는 의학적 조언이 아닌 생활 습관 참고 정보
- **궁합 윤리**: "궁합이 나쁘다" (X) → "소통 방식의 차이가 큰 부분" (O)

---

## 2. 프로젝트 파일 구조 (활성 파일만)

```
saju-prod/
├── context.md                          ← 이 파일 (구동 원칙 & 현황)
├── run.command                         ← 실행 스크립트
├── render.yaml                         ← 배포 설정
│
├── frontend/
│   ├── index.html                      ← 단일 HTML 프론트엔드 (HTML+CSS+JS 통합)
│   ├── images/
│   │   └── dragon-brain.png            ← 히어로 이미지 (용+뇌 일러스트)
│   ├── public/                         ← 정적 파일
│   └── src/                            ← (미사용, 향후 정리 대상)
│
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py                     ← FastAPI 앱 진입점
│       ├── __init__.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── saju.py                 ← API 엔드포인트 (개인분석 + 궁합)
│       │   └── health.py               ← 헬스체크
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py               ← 환경 설정
│       │   └── database.py             ← DB 연결 (SQLAlchemy)
│       │
│       ├── models/
│       │   ├── __init__.py             ← 모델 import 관리
│       │   ├── saju_request.py         ← 사주 요청 모델
│       │   ├── saju_result.py          ← 사주 결과 모델
│       │   ├── llm_log.py              ← LLM 호출 로그
│       │   └── shared_result.py        ← 공유 결과 (UUID 기반)
│       │
│       ├── schemas/
│       │   └── saju.py                 ← Pydantic 스키마
│       │
│       ├── services/
│       │   ├── saju_engine/            ← ⛔ 사주 계산 엔진 (수정 금지)
│       │   │   ├── orchestrator.py
│       │   │   ├── pillar_calculator.py
│       │   │   ├── ten_god_calculator.py
│       │   │   ├── hidden_stem_calculator.py
│       │   │   ├── relation_calculator.py
│       │   │   ├── daewoon_calculator.py
│       │   │   ├── gyeokguk_calculator.py
│       │   │   ├── interpreter.py
│       │   │   ├── interpretation_data.py
│       │   │   ├── constants.py
│       │   │   ├── normalizer.py
│       │   │   ├── dto.py
│       │   │   ├── solar_term_finder.py
│       │   │   ├── timezone_adjuster.py
│       │   │   ├── twelve_stage_calculator.py
│       │   │   ├── ganzhi_math.py
│       │   │   └── exceptions.py
│       │   │
│       │   └── llm/
│       │       ├── __init__.py
│       │       ├── claude_client.py    ← Claude API 클라이언트 (SSE 스트리밍)
│       │       └── prompts.py          ← 4대 콘텐츠 프롬프트
│       │
│       └── utils/                      ← 유틸리티
```

---

## 3. 기술 스택

| 영역 | 기술 |
|------|------|
| 백엔드 | Python 3.11+, FastAPI, SQLAlchemy 2.0 |
| 데이터베이스 | SQLite (개발) / PostgreSQL (운영) |
| LLM | Claude API (Anthropic SDK), SSE 스트리밍 |
| 프론트엔드 | 단일 HTML + Vanilla JS (FastAPI 직접 서빙) |
| 실행 | `run.command` → uvicorn |

---

## 4. UI 디자인 시스템

| 요소 | 값 |
|------|---|
| 배경 | #0B0A12 (메인), #15132A (서피스), #1E1B35 (카드) |
| 주 강조색 | #E8A840 (파이어 골드), #F0C060 (라이트), #C88A28 (다크) |
| 보조 강조색 | #7B4FBF (퍼플), #9B6FDF (퍼플 라이트), #D4AF37 (액센트) |
| 오행 컬러 | 목=#27AE60, 화=#E74C3C, 토=#F39C12, 금=#95A5A6, 수=#3498DB |
| 텍스트 | #F0EDE8 (메인), #B0A8C0 (서브), #8A8498 (디밍) |
| 폰트 | Noto Serif KR (제목), Noto Sans KR (본문) |
| 키워드 | 신비롭다, 차분하다, 지적이다, 고급스럽다 |
| 배제 | 무속적/주술적 이미지, 귀여운 캐릭터, 밝은 배경 |

### 주요 CSS 클래스 (UI 대개편 추가분)

| 클래스 | 용도 |
|--------|------|
| `.service-card.card-wide` | 가로형 카드 (grid-column: 1 / -1, flex-direction: row) |
| `.card-coming-soon` | 준비 중 카드 (opacity 0.7, 클릭 시 토스트) |
| `.badge-soon` | "준비중" 뱃지 (카드 제목 옆 태그) |
| `.card-cta` | 카드 우측 CTA 텍스트 ("시작하기", "Coming Soon") |
| `.brain-card` | 뇌과학 설문 카드 (카드 슬라이더 단위) |
| `.brain-progress` | 뇌과학 설문 진행률 바 |
| `.brain-option` | 설문 선택지 버튼 |
| `.growth-prereq` | 자기계발 전제조건 표시 영역 |
| `.growth-check-item` | 자기계발 체크리스트 아이템 |

---

## 5. 4대 핵심 콘텐츠

| # | 콘텐츠 | 핵심 질문 | 상태 |
|---|--------|----------|------|
| 1 | 운명 매뉴얼 (Saju & Mind Profile) | "나는 무엇에 민감하고 어떤 환경에서 강해지는가" | ✅ 7섹션 구조 적용 완료 |
| 2 | 맞춤형 자기계발 루틴 (Growth Routine) | "어떤 방식으로 일해야 효율이 나는가" | ✅ 프롬프트 전환 완료 |
| 3 | 바이오 리듬 케어 (Bio Rhythm Care) | "내 몸은 어떤 리듬에서 무너지는가" | ✅ 프롬프트 전환 완료 |
| 4 | 뉴로 궁합 (Neuro Matching) | "왜 자꾸 엇갈리고 어떻게 풀어야 하는가" | 🔲 신규 개발 예정 |

---

## 6. 분석 워크플로우

### 개인 분석 (현재 작동 중)
```
생년월일시 입력 → saju_engine 계산 → JSON 명식 산출
  → interpretation_data 매핑 → LLM 프롬프트 주입
  → Claude API SSE 스트리밍 → 프론트엔드 실시간 렌더링
```

### 궁합 분석 (Phase 4 예정)
```
두 사람 입력 → 각각 saju_engine 계산 → 교차 분석
  → 일간 관계 + 십성 교차 + 지지 합충 + 용신 보완
  → LLM 궁합 해석 → 뉴로 궁합 리포트
```

---

## 7. 개발 진행 현황

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | 사주 계산 엔진 정확화 | ✅ 완료 & 🔒 잠금 |
| 2 | LLM 해석 기본 연동 | ✅ 완료 |
| 3-1 | 문서 재정의 (CLAUDE.md, plan.md, context.md) | ✅ 완료 |
| 3-2 | 프론트엔드 다크 프리미엄 UI 전면 재설계 | ✅ 완료 |
| 3-3 | 프롬프트 시스템 전면 교체 (7섹션 구조, 명리학자+임상심리 페르소나) | ✅ 완료 |
| 3-4 | 해석 데이터 행동과학·건강 매핑 추가 | ✅ 완료 (build_context에 통합) |
| **3-UI** | **UI 대개편 (8대 요구사항)** | **✅ 완료 (2026-03-27)** |
| 4-1 | 뉴로 궁합 2인 입력 UI + API | 🔲 대기 |
| 4-2 | 교차 사주 분석 로직 | 🔲 대기 |
| 4-3 | 궁합 해석 프롬프트 | 🔲 대기 |
| 5-1 | 일진 기반 "오늘의 루틴" 자동 갱신 | 🔲 대기 |
| 5-2 | 결과 공유/저장 기능 확장 | 🔲 대기 |

### 3-UI 상세: UI 대개편 8대 요구사항 (2026-03-27 완료)

| # | 요구사항 | 구현 내용 |
|---|---------|----------|
| 1 | 홈 카드→독립 페이지, 궁합 준비중 | 4카드 onclick → showPage/goToGrowth/showToast, card-coming-soon 클래스 |
| 2 | 하단 네비 5탭 | 홈🏛/사주✦/무료진단🔮/뇌과학🧠/보관함📦 |
| 3 | 보관함 인물 그룹핑 | name\|birthdate 키 그룹핑, 프로필 아바타, 양력/음력 병기 |
| 4 | 뇌과학 설문 카드 슬라이더 | 15문항 8영역, 자동진행, 터치 스와이프, 완료상태 관리 |
| 5 | 자기계발 전제조건 | 사주 완료 + 뇌과학 완료 필수, updateGrowthStatus() 체크 |
| 6 | 결과 페이지 양력+음력 표시 | result-birth-info 요소, 성별·시간 포함 |
| 7 | 인터랙티브 체크리스트 | 습관설계 추출 → 체크박스 → localStorage 영속 |
| 8 | 가로형 wide 카드 | 자기계발·궁합 card-wide (grid-column: 1/-1) |

### 현재 프론트엔드 페이지 구조 (8페이지)

| 페이지 ID | 용도 | 네비 하이라이트 |
|-----------|------|---------------|
| `page-home` | 메인 홈 (히어로 + 4카드) | nav-home |
| `page-saju` | 사주 입력 폼 | nav-saju |
| `page-result` | 사주 분석 결과 (AI 포함) | nav-saju |
| `page-shared` | 공유 결과 보기 | — |
| `page-storage` | 보관함 (인물 그룹핑) | nav-storage |
| `page-free` | 무료진단 (AI 없이 데이터만) | nav-free |
| `page-brain` | 뇌과학 설문 (15문항 카드 슬라이더) | nav-brain |
| `page-growth` | 자기계발 분석 (사주+뇌과학 기반) | nav-brain |

### 홈 카드 레이아웃

```
[grid 2열]
┌──────────────┐ ┌──────────────┐
│ 🔮 사주분석    │ │ 🧠 건강-뇌과학  │
└──────────────┘ └──────────────┘
┌─────────────────────────────────┐
│ ⚡ 자기계발 (wide)    [시작하기]   │
└─────────────────────────────────┘
┌─────────────────────────────────┐
│ ∞ 궁합 (wide, 준비중) [Coming Soon]│
└─────────────────────────────────┘
```

### localStorage 데이터 관리

| 키 | 용도 | 데이터 형태 |
|----|------|-----------|
| `saju_storage` | 사주 분석 결과 보관 | JSON 배열 [{id, name, birthdate, birthtime, gender, date, dayMaster, gyeokguk, strength, calcResult}] (최대 50건) |
| `brain_answers` | 뇌과학 설문 응답 | JSON 배열 [0~3 인덱스, 15개] |
| `brain_completed` | 뇌과학 설문 완료 여부 | "true" / null |
| `growth_result` | 자기계발 분석 결과 | 텍스트 (AI 응답 전문) |
| `growth_checks` | 체크리스트 상태 | JSON 배열 [true/false, ...] |

---

## 8. 삭제된 파일 기록 (2026-03-27)

아래 파일들은 불필요하여 삭제 완료. FK 참조도 정리됨.

- `backend/app/core/security.py` — JWT 인증 (미사용)
- `backend/app/models/user.py` — users 테이블 (미사용)
- `backend/app/models/payment.py` — 결제 모델 (미사용)
- `backend/app/models/subscription.py` — 구독 모델 (미사용)
- `backend/app/models/prompt_version.py` — 프롬프트 버전 (미사용)
- `frontend/package.json` — Node.js 의존성 (Vanilla JS 전환)
- `frontend/package-lock.json` — 잠금 파일
- `frontend/vite.config.ts` — Vite 설정
- `backend/saju_local.db` — 로컬 DB 파일
- `backend/sql/init_schema.sql` — 초기 스키마

---

## 9. 주요 프론트엔드 함수 참조 (47개, 2026-03-27 기준)

### 핵심 라우팅 & 렌더링

| 함수 | 역할 |
|------|------|
| `showPage(pageId)` | 8페이지 전환 + 네비 하이라이트 + 페이지별 초기화(renderFreeDiagnosis, renderStorageList 등) |
| `renderResult(data)` | 사주 분석 결과 렌더링 (오행 바, 원국표, 일간해석, 양력/음력 생년월일) → loadSajuTitles 자동 호출 |
| `tryLivePreview()` | 입력 중 실시간 미리보기 (사주 입력 폼) |

### AI 스트리밍 (2단계 시스템)

| 함수 | 역할 |
|------|------|
| `loadSajuTitles()` | 1단계: SSE로 소제목 수신 → `tryRenderNewLines()`로 1개씩 즉시 카드 렌더링 + 프로그레스 바 |
| `tryRenderNewLines(isFinal)` | `\n`으로 확정된 줄만 파싱 (미완성 줄 건너뜀 방지) |
| `parseSajuTitleLine(line)` | 소제목 파싱: 번호 제거 → #태그 추출 → 이모지 분리 → `{icon, title, tag}` |
| `appendSajuTitleCard(t, idx, listEl)` | 소제목 카드 DOM 생성 + fadeIn |
| `toggleSajuDetail(idx)` | 2단계: 소제목 클릭 → 개별 상세 해석 SSE 호출 (캐싱, 멀티 오픈) |
| `formatAI(text)` | AI 텍스트 → HTML 포맷팅 |

### 심층 분석 & 결과

| 함수 | 역할 |
|------|------|
| `toggleAnalysis(id)` | 결과 페이지 심층 분석 아코디언 토글 (6개) |
| `getStemTenGod(...)` | 천간 십성 조회 |
| `getBranchTenGod(...)` | 지지 십성 조회 |
| `getTwelveStage(...)` | 십이운성 조회 |
| `checkAIStatus()` | AI 서비스 상태 확인 |
| `shareResult()` | 결과 공유 링크 생성 |
| `renderShared()` | 공유 결과 렌더링 |

### 보관함

| 함수 | 역할 |
|------|------|
| `saveToStorage(name, birthdate, calcResult)` | 분석 결과를 localStorage에 저장 (성별, 시간 포함) |
| `getStorageItems()` | localStorage에서 보관함 데이터 조회 |
| `renderStorageList()` | 인물별 그룹핑 보관함 렌더링 (프로필 아바타, 양력/음력 병기) |
| `loadStorageItem(idx)` | 보관함 항목 불러와서 분석 재표시 |
| `deleteStorageItem(idx)` | 보관함 항목 삭제 |
| `getLunarDateStr(item)` | 음력 날짜 문자열 생성 |

### 무료진단

| 함수 | 역할 |
|------|------|
| `renderFreeDiagnosis()` | 무료진단 페이지 초기 렌더링 (보관함에서 데이터 로드) |
| `renderFreeDetail(item)` | 무료진단 상세 — 결과페이지와 동일 아코디언 구조 (AI 해설 제외) |
| `toggleFreeAnalysis(id)` | 무료진단 아코디언 토글 (결과페이지의 toggleAnalysis와 분리) |

### 뇌과학 설문

| 함수 | 역할 |
|------|------|
| `loadBrainAnswers()` | localStorage에서 기존 설문 답변 복원 |
| `renderBrainCard(idx)` | 설문 카드 1장 렌더링 (진행률 바 + 질문 + 선택지) |
| `selectBrainOption(qIdx, optIdx)` | 답변 선택 → localStorage 저장 → 0.4초 후 자동 진행 |
| `brainNav(dir)` | 이전/다음 네비게이션, 마지막 문항 완료 시 상태 저장 |
| `resetBrainSurvey()` | 설문 초기화 (localStorage 삭제, 질문 0으로 리셋) |

### 자기계발 분석

| 함수 | 역할 |
|------|------|
| `goToGrowth()` | 자기계발 페이지 이동 (전제조건 체크: 사주+뇌과학 완료 필수) |
| `goToGrowthPrereq()` | 전제조건 미충족 시 안내 표시 |
| `updateGrowthStatus()` | 전제조건 상태 확인 + 이전 결과 존재 시 복원 |
| `startGrowthAnalysis()` | SSE 스트리밍 `/ai/interpret?category=growth_routine` 호출 (뇌과학 요약 포함) |
| `buildBrainSummary(answers)` | 뇌과학 설문 응답 → 영역별 점수 텍스트 요약 변환 |
| `formatGrowthContent(text)` | 마크다운 → HTML 변환 (자기계발 전용) |
| `extractChecklist(text)` | AI 응답의 "습관 설계" 섹션에서 실천 항목 추출 |
| `renderChecklist(items)` | 인터랙티브 체크박스 렌더링 |
| `toggleCheckItem(idx)` | 체크 상태 토글 + localStorage 저장 |
| `loadChecklistState()` | localStorage에서 체크 상태 복원 |

### 유틸리티

| 함수 | 역할 |
|------|------|
| `showToast(msg)` | 토스트 알림 표시 (3초 자동 소멸) |
| `getElementColor(element)` | 오행명 → CSS 컬러 반환 |
| `checkShareUrl()` | URL 파라미터에서 공유 ID 확인 |

---

## 10. API 엔드포인트 (prefix: `/api/saju`)

| Method | Path | 설명 | 프론트엔드 호출 |
|--------|------|------|---------------|
| GET | `/` | 프론트엔드 index.html 서빙 | 직접 |
| GET | `/health` | 헬스체크 | — |
| POST | `/api/saju/calculate` | 사주 계산 (명식 산출) | `fetch(\`\${API}/calculate\`)` |
| POST | `/api/saju/analyze` | 사주 분석 (계산+해석) | — |
| GET | `/api/saju/ai/status` | AI 서비스 상태 확인 | `fetch(\`\${API}/ai/status\`)` |
| POST | `/api/saju/ai/interpret?category=` | AI 해석 SSE 스트리밍 | saju_titles, saju_detail, growth_routine |
| POST | `/api/saju/ai/interpret-full` | AI 전체 해석 (non-stream) | — |
| POST | `/api/saju/share` | 결과 공유 링크 생성 | `fetch(\`\${API}/share\`)` |
| GET | `/api/saju/share/{share_id}` | 공유 결과 조회 | `fetch(\`\${API}/share/\${id}\`)` |

> **참고**: 프론트엔드의 `API` 변수는 `'/api/saju'`로 설정됨. 모든 fetch 호출은 `\`\${API}/endpoint\`` 형태.

---

## 11. LLM 프롬프트 시스템 (2026-03-27 전면 교체)

### 시스템 프롬프트 페르소나

"20년 경력의 명리학자이자 임상심리 상담사"로 설정. 점술적 예언이 아닌 자기 이해를 돕는 심리적 통찰을 제공.

### 핵심 역할 원칙

| # | 원칙 | 설명 |
|---|------|------|
| 1 | 심리적 통찰 | 점술 예언 아닌 자기 이해 중심 |
| 2 | 2인칭 현재형 | "당신은 ~하고 있을 가능성이 높아요" |
| 3 | 용어 풀이 | 한자·전문 용어 후 괄호로 쉬운 설명 |
| 4 | 양면 해석 | 강점 + 그림자(과잉 시 부작용) 함께 |
| 5 | 구체적 시나리오 | 추상적 표현 금지, 상황 묘사 필수 |

### 메인 분석 출력 구조 (7섹션, 순서 강제)

```
## ✦ 한 줄 핵심 요약
## 1. 에너지 구조 — 나는 어떤 사람인가
## 2. 관계 패턴 — 나는 사람들과 어떻게 얽히는가
## 3. 커리어·재물 구조 — 나는 어떻게 성공하는 사람인가
## 4. 반복되는 삶의 패턴 — 내가 평생 마주하는 과제
## 5. 건강·에너지 관리
## 6. 지금 이 시기 — 현재 대운·세운 분석
## 7. 이번 달 실천 가이드
```

### 문체 규칙

- 존댓말, 친근하되 날카롭게
- 한 문장에 하나의 개념, 각 섹션 800~1,200자
- 금지어: "운명입니다", "타고났습니다", "무조건", "반드시"
- 대안: "~하는 경향이 있어요", "~일 가능성이 높아요"

### 입력 데이터 (build_context가 생성)

사주팔자, 일간 강약, 용신/기신, 격국, 오행 분포(바 차트 + 과다/부족),
십신 분포(개수), 십성 배치(위치별), 십이운성, 합충형해파,
공망, 대운 흐름(현재 표시), 세운(올해 간지), 나이/성별,
행동과학 매핑, 건강 매핑

### 카테고리별 프롬프트 (CATEGORY_PROMPTS)

| 카테고리 키 | 용도 | max_tokens | 호출 시점 |
|------------|------|-----------|----------|
| `saju_titles` | 소제목 리스트 생성 (10~15개) | 1024 | 결과 페이지 로딩 시 자동 |
| `saju_detail` | 개별 소제목 상세 해석 | 1500 | 소제목 클릭 시 개별 |
| `destiny_manual` | 메인 종합 분석 (7섹션) | 4096 | (레거시) |
| `growth_routine` | 자기계발 루틴 (5섹션) | 4096 | |
| `bio_rhythm` | 바이오 리듬 케어 (5섹션) | 4096 | |

### 2단계 AI 시스템 (프로그레스 바 + 점진적 렌더링)

> **핵심 UX 원칙**:
> - 소제목이 **스트리밍 중 1개씩 즉시 등장** (완료까지 기다리지 않음)
> - 🔮 여의주 + 가로 프로그레스 바 + 퍼센트 표시 (소제목/상세 해설 모두)
> - 카드를 클릭해도 **이전에 열었던 카드 내용은 그대로 유지** (접지 않음)
> - 새 카드 해설은 아래로 자연스럽게 펼쳐짐 (위로 스크롤되지 않음)
> - 용(🐉) 이모지 없음 — 여의주(🔮)만 사용

```
[1단계] 결과 페이지 로딩 → saju_titles 자동 호출
        → 🔮 프로그레스 바 표시 (0%~100%)
        → 소제목이 1개씩 완성될 때마다 즉시 카드 렌더링 (fadeIn 애니메이션)
        → 완료 후 프로그레스 바 자동 숨김

[2단계] 소제목 카드 클릭 → saju_detail 개별 호출
        → 카드 내부에 🔮 프로그레스 바 표시 (0%~100%)
        → SSE 스트리밍 텍스트가 프로그레스 바 아래로 실시간 렌더링
        → 완료 시 프로그레스 바 제거, 텍스트만 표시
        → 이전에 열었던 다른 카드는 닫지 않음 (멀티 오픈)
        → 캐시 저장 (_titleDetailCache, 재클릭 시 즉시 표시)
```

### SSE 파싱 구현 (주의사항)

SSE 프로토콜에서 하나의 이벤트 내 여러 `data:` 라인은 `\n`으로 연결해야 함 (SSE 스펙).
프론트엔드에서는 `\n\n`으로 이벤트를 분리한 후, 각 이벤트 내 `data:` 라인들을 `\n`으로 조인하여 원본 텍스트의 줄바꿈을 복원.

```javascript
// 올바른 SSE 파싱 패턴 (loadSajuTitles, toggleSajuDetail 공통)
sseBuffer += decoder.decode(value, {stream:true});
const events = sseBuffer.split('\n\n');
sseBuffer = events.pop(); // 미완성 이벤트는 버퍼에 유지
for(const event of events) {
  const dataLines = event.split('\n')
    .filter(l => l.startsWith('data: '))
    .map(l => l.slice(6));
  const eventData = dataLines.join('\n'); // 핵심: \n으로 연결
  text += eventData;
}
```

### 소제목 파싱 규칙 (renderSajuTitles)

LLM 출력 형식이 다양할 수 있으므로 robust 파싱:
- 번호 접두사 (`1.`, `2)`) 자동 제거
- `#태그` 추출 (여러 개 가능, 첫 번째만 표시)
- 유니코드 이모지 감지 → 아이콘으로 분리
- 이모지 없으면 기본 아이콘 `✦` 사용
- 제목 3자 미만이면 스킵

### CSS 스타일

- 각 소제목 항목이 `border-radius: 14px` 카드
- 카드 사이 `gap: 10px` 간격
- 제목 텍스트 `font-size: 1.1em`, `font-weight: 700` (큰 글씨)
- 활성 상태: 골드 테두리 + 은은한 그림자
- 해석 본문: 카드 내부 border-top 구분선 아래 표시
- 프로그레스 바: `linear-gradient(90deg, primary, #E8D5B5)` + `box-shadow` 글로우
- 소제목 등장: `saju-title-enter` → `opacity:0, translateY(12px)` → fade+slide in

### 소제목 점진적 렌더링 핵심 로직 (⚠️ 반드시 준수)

LLM은 2~3글자씩 스트리밍하므로 **줄바꿈(`\n`)으로 확정된 줄만** 파싱해야 한다.

```javascript
// ✅ 올바른 패턴 — tryRenderNewLines(isFinal)
function tryRenderNewLines(isFinal) {
  const parts = text.split('\n');
  // 스트리밍 중: 마지막 줄은 미완성이므로 제외
  // 최종 완료(isFinal=true): 마지막 줄도 포함
  const linesToCheck = isFinal ? parts : parts.slice(0, -1);
  while(completedLineCount < linesToCheck.length) {
    const line = linesToCheck[completedLineCount];
    completedLineCount++;
    if(line.trim().length <= 2) continue;
    const parsed = parseSajuTitleLine(line);
    if(parsed) { /* 카드 렌더링 */ }
  }
}
```

```javascript
// ❌ 금지 패턴 — 미완성 줄을 파싱하면 영구 스킵 버그 발생
const allLines = text.split('\n').filter(l => l.trim().length > 2);
while(lastRendered < allLines.length) {
  parseSajuTitleLine(allLines[lastRendered]); // 미완성 "🔮 당" → null → skip
  lastRendered++; // 이 줄은 다시 돌아오지 않음!
}
```

### 심층 분석 메뉴 section 키 매핑 (⚠️ 반드시 준수)

프론트엔드에서 `interp.find(s => s.section === '키')` 검색 시, 백엔드 `interpreter.py`의 반환 section 값과 일치해야 한다.

| 메뉴 | 프론트엔드 검색 키 | 백엔드 section 값 | 비고 |
|------|------------------|------------------|------|
| 격국분석 | `'gyeokguk'` | `'gyeokguk'` | ✅ |
| 오행균형분석 | `'oheng'` | `'oheng'` | ✅ (이전 `'five_elements'` 버그 수정 완료) |
| 십성 강세 분석 | `'sipsung'` | `'sipsung'` | ✅ (이전 `'ten_gods'` 버그 수정 완료) |
| 합충형해파 | `'relations'` | `'relations'` | ✅ |
| 십이운성 | `'twelve_stages'` | `'twelve_stages'` | ✅ |
| 대운흐름 | `'daewoon'` | `'daewoon'` | ✅ |

### 품질 핵심 포인트

1. **관계망 해석**: 입력 데이터를 단일 글자가 아닌 전체 구조로 종합 해석
2. **2단계 분리**: 소제목만 빠르게 생성 → 사용자가 관심 있는 항목만 상세 해석 (토큰 절약)
3. **트렌디 소제목**: MZ세대 감성 표현 + 카테고리 태그 (#기질, #커리어, #연애 등)
4. **캐싱**: 한 번 열어본 해석은 메모리에 저장, 재클릭 시 API 재호출 없음
5. **멀티 오픈**: 여러 카드를 동시에 열 수 있음 — 이전 해설 내용 보존
6. **점진적 로딩**: 소제목 1개씩 즉시 등장, 프로그레스 바로 진행도 표시

---

## 12. 수정 이력 & 해결된 버그 로그 (2026-03-27)

### 버그 1: SSE 줄바꿈 손실 → 소제목 전체가 한 줄로 합쳐짐
- **원인**: `text += d` (줄바꿈 없이 이어붙임). 백엔드가 `chunk.split("\n")`으로 보낸 여러 `data:` 라인을 프론트엔드가 `\n` 없이 연결
- **해결**: `\n\n`으로 SSE 이벤트 분리 → 이벤트 내 `data:` 라인들을 `\n`으로 조인하는 올바른 SSE 파싱 적용
- **영향 범위**: `loadSajuTitles()`, `toggleSajuDetail()` 모두 수정

### 버그 2: 미완성 줄 조기 파싱 → 소제목 로딩 0%에서 멈춤
- **원인**: LLM이 2~3글자씩 스트리밍 → 미완성 줄 "🔮 당"을 파싱 시도 → 3자 미만으로 null → `lastRenderedLineCount++` 실행 → 줄이 완성되어도 재처리 안 됨
- **해결**: `tryRenderNewLines(isFinal)` — `text.split('\n').slice(0, -1)`로 마지막 미완성 줄 제외, 줄바꿈으로 확정된 줄만 파싱
- **핵심 원칙**: 절대 미완성 줄을 파싱하지 않는다

### 버그 3: 오행균형분석·십성강세 분석 클릭 시 빈 내용
- **원인**: 프론트엔드 section 검색 키(`'five_elements'`, `'ten_gods'`)와 백엔드 반환 값(`'oheng'`, `'sipsung'`)이 불일치
- **해결**: 프론트엔드 키를 백엔드와 일치시킴 (`'oheng'`, `'sipsung'`)
- **핵심 원칙**: saju_engine 파일은 수정 금지 → 프론트엔드 쪽에서 맞춤

### 버그 4: 모든 카드가 동시에 열리고 닫히는 문제
- **원인**: 단일 아코디언 동작(다른 카드 자동 닫힘) + scrollIntoView 로 화면이 위로 점프
- **해결**: 멀티 오픈 방식으로 전환 (이전 카드 유지), scrollIntoView 제거

### UX 개선: 로딩 화면
- 용(🐉) 이모지 제거, 여의주(🔮) + 가로 프로그레스 바 + 퍼센트 표시로 교체
- 소제목: 스트리밍 중 1개씩 fadeIn 등장 (완료까지 기다리지 않음)
- 상세 해설: 카드 내부에 프로그레스 바 + 스트리밍 텍스트 동시 표시

### 버그 5: 무료진단 relations 데이터 구조 불일치 (UI 대개편 중)
- **원인**: 초기 무료진단 코드가 relations를 `{천간합: [...], 지지충: [...]}` 형태의 중첩 딕셔너리로 가정
- **실제**: orchestrator.py는 `[{category, subtype, left, right, note}]` 형태의 플랫 배열 반환
- **해결**: 플랫 배열을 직접 순회하며 category별 그룹핑하여 렌더링
- **핵심 원칙**: saju_engine 출력 구조는 변경 불가 → 프론트엔드에서 맞춤

---

## 13. 무료진단 페이지 구조 (결과 페이지 미러링)

무료진단(page-free)은 결과 페이지(page-result)의 구조를 AI 해설 없이 그대로 재현한다.
기존 결과 페이지의 CSS 클래스(`.analysis-menu-card`, `.interp-body`, `.ohang-bars`, `.preview-table`, `.daewoon-scroll`)를 공유하여 시각적 일관성 유지.

**출력 섹션 (순서대로):**
1. 헤더 (이름, 해시태그, 양력/음력 생년월일)
2. 오행 에너지 분포 (ohang-bars + 아이콘)
3. 사주 원국표 (preview-table)
4. 일간 해석
5. 심층 분석 메뉴 — 6개 아코디언 (`toggleFreeAnalysis(id)` 사용):
   - 격국분석(gyeokguk), 오행균형(oheng), 십성강세(sipsung),
   - 합충형해파(relations), 십이운성(twelve_stages), 대운흐름(daewoon)
6. 대운 (10년 주기) — daewoon-scroll 카드
7. 세운 (연간 흐름) — daewoon-scroll 카드
8. 럭키 아이템 (있는 경우)
9. Footer — "AI 사주분석 하러가기" 버튼

---

## 14. 뇌과학 설문 시스템

### BRAIN_QUESTIONS (15문항, 8영역)

| # | 영역 | 문항 주제 |
|---|------|----------|
| 1~2 | 수면 | 수면 패턴, 기상 후 컨디션 |
| 3~4 | 집중력 | 집중 유지 방식, 멀티태스킹 성향 |
| 5~6 | 운동 | 운동 빈도, 선호 운동 유형 |
| 7~8 | 스트레스 | 스트레스 해소법, 스트레스 인지 방식 |
| 9~10 | 학습 | 학습 선호 방식, 새로운 정보 습득 |
| 11 | 동기부여 | 동기 유발 요인 |
| 12~13 | 자기조절 | 감정 조절, 충동 통제 |
| 14~15 | 마음챙김 | 현재 인식, 자기 관찰 |

### 카드 슬라이더 UX
- 1문항씩 카드 형태로 표시 (renderBrainCard)
- 선택지 클릭 → 0.4초 딜레이 → 자동 다음 문항 진행
- 터치 스와이프 지원 (touchstart/touchend)
- 진행률 바 상단 표시 (현재/전체)
- 완료 시: "재진단하기" + "자기계발 분석 보기" 버튼

### buildBrainSummary(answers) 스코어링
- 각 영역별 선택지 인덱스(0~3) → 점수로 환산
- 영역 평균 점수 → "양호/보통/주의필요" 텍스트 생성
- growth_routine 프롬프트에 뇌과학 요약으로 주입
