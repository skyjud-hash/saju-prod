"""Claude API용 프롬프트 생성 — 계산은 하지 않고 해석만 수행.

핵심 원칙 (김만태 2022):
- Claude에게 명식 계산, 천간지지 계산, 오행 산출, 십성 계산을 맡기지 않는다
- Claude는 제공된 계산 결과 JSON을 바탕으로 자연어 설명만 생성한다
"""

ELEMENT_KR = {"wood": "목(木)", "fire": "화(火)", "earth": "토(土)", "metal": "금(金)", "water": "수(水)"}

TEN_GOD_KR = {
    "bijeon": "비견(比肩)", "geopjae": "겁재(劫財)",
    "siksin": "식신(食神)", "sanggwan": "상관(傷官)",
    "pyeonjae": "편재(偏財)", "jeongjae": "정재(正財)",
    "pyeongwan": "편관(偏官)", "jeonggwan": "정관(正官)",
    "pyeonin": "편인(偏印)", "jeongin": "정인(正印)",
}

SYSTEM_PROMPT = """당신은 30년 경력의 사주명리학 전문 상담사입니다.

핵심 규칙:
- 제공된 계산 결과만 바탕으로 설명하세요. 계산을 다시 하지 마세요.
- 천간지지, 오행 점수, 십성, 격국, 용신은 이미 계산되어 제공됩니다.
- 이 수치들을 절대 재계산하거나 변경하지 마세요.

해석 원칙:
- "~할 수 있습니다", "~하는 경향이 있습니다" 등 가능성 표현 사용
- 부정적 요소도 성장의 기회로 해석
- 비유와 구체적 사례로 읽는 재미 제공

글쓰기 형식:
- 한국어로만 답변
- HTML 태그 절대 금지
- **소주제 제목**은 이모지 + 굵은 제목. 예: **🌊 바다처럼 깊은 내면**
- 소주제별 2~4문장 문단, 문단 사이 빈 줄
- 전체 2000자 이내"""


def build_context(raw_calc: dict) -> str:
    """raw_calculation_json을 프롬프트용 텍스트로 변환."""
    pillars = raw_calc.get("pillars", {})
    fe = raw_calc.get("five_elements", {})
    gk = raw_calc.get("gyeokguk", {})
    ten_gods = raw_calc.get("ten_gods", [])
    twelve_stages = raw_calc.get("twelve_stages", [])
    relations = raw_calc.get("relations", [])
    daewoon = raw_calc.get("daewoon", [])

    lines = ["[사주 명식 — 계산 엔진 산출 결과]"]
    for key, label in [("year", "년주"), ("month", "월주"), ("day", "일주"), ("hour", "시주")]:
        p = pillars.get(key, {})
        if p:
            lines.append(
                f"  {label}: {p.get('stem_hanja','')}{p.get('branch_hanja','')} "
                f"({p.get('stem_kr','')}{p.get('branch_kr','')}) — "
                f"천간 {ELEMENT_KR.get(p.get('stem_element',''),'')} "
                f"지지 {ELEMENT_KR.get(p.get('branch_element',''),'')}"
            )

    day_p = pillars.get("day", {})
    if day_p:
        yy = "양(陽)" if day_p.get("stem_yinyang") == "yang" else "음(陰)"
        lines.append(f"\n[일간] {day_p.get('stem_hanja','')}({day_p.get('stem_kr','')}) "
                     f"— {ELEMENT_KR.get(day_p.get('stem_element',''),'')} {yy}")

    lines.append("\n[오행 분포]")
    total = sum(fe.get(el, 0) for el in ["wood", "fire", "earth", "metal", "water"])
    for el in ["wood", "fire", "earth", "metal", "water"]:
        s = fe.get(el, 0)
        pct = (s / total * 100) if total > 0 else 0
        lines.append(f"  {ELEMENT_KR.get(el, el)}: {s:.1f}점 ({pct:.0f}%)")

    if gk:
        lines.append(f"\n[격국] {gk.get('name','')} ({gk.get('type','')})")
        lines.append(f"[신강도] {gk.get('strength_score',50):.0f}점 → {gk.get('strength','')}")
        lines.append(f"[용신] {ELEMENT_KR.get(gk.get('yongshin_element',''),'')}")
        lines.append(f"[기신] {ELEMENT_KR.get(gk.get('gishin_element',''),'')}")

    if ten_gods:
        lines.append("\n[십성 배치]")
        for t in ten_gods:
            if t.get("source_position") == "stem":
                pl = {"year": "년주", "month": "월주", "hour": "시주"}.get(t.get("source_pillar", ""), "")
                god = TEN_GOD_KR.get(t.get("ten_god_code", ""), t.get("ten_god_kr", ""))
                lines.append(f"  {pl}: {god}")

    if twelve_stages:
        lines.append("\n[십이운성]")
        for ts in twelve_stages:
            pl = {"year": "년주", "month": "월주", "day": "일주", "hour": "시주"}.get(ts.get("pillar_type", ""), "")
            lines.append(f"  {pl}: {ts.get('stage_kr','')}")

    if relations:
        lines.append("\n[합충형해파]")
        for r in relations:
            lines.append(f"  {r.get('category','')}: {r.get('note','')}")

    if daewoon:
        lines.append("\n[대운]")
        for d in daewoon[:8]:
            lines.append(f"  {d.get('start_age',0):.0f}~{d.get('end_age',0):.0f}세: "
                         f"{d.get('stem_kr','')}{d.get('branch_kr','')}")

    return "\n".join(lines)


CATEGORY_PROMPTS = {
    "comprehensive": """위 계산 결과를 종합 해석해주세요. 소주제:
**1**: 일간의 본질 (자연물 비유)
**2**: 격국과 용신이 삶에 미치는 영향
**3**: 오행 밸런스 — 강한/부족한 오행의 영향
**4**: 십성으로 본 대인관계
**5**: 추천 직업 3가지 + 전공 3가지
**6**: 대운 시기별 조언
**7**: 이 사주를 가진 사람에게 전하는 말""",

    "personality": """위 계산 결과로 성격과 기질을 해석해주세요. 소주제:
**1**: 일간이 드러내는 본질적 기질
**2**: 격국과 용신의 성격 방향성
**3**: 오행 균형의 일상 영향
**4**: 십성 배치의 인간관계 스타일
**5**: 합충형해파의 내면 역동
**6**: 따뜻한 조언""",

    "career": """위 계산 결과로 진로와 직업을 추천해주세요. 소주제:
**1**: 용신 오행이 가리키는 방향
**2**: 십성 강세의 직업 적성
**3**: 딱 맞는 직업 5가지 (이유 포함)
**4**: 추천 대학 전공 5가지
**5**: 기신 오행 관련 주의사항
**6**: 대운으로 본 최적 타이밍""",

    "study": """위 계산 결과로 학업·입시 전략을 조언해주세요. 소주제:
**1**: 타고난 학습 스타일
**2**: 잘하는 과목 vs 전략 필요 과목
**3**: 적합한 입시 전형 (교과/종합/논술/실기)
**4**: 추천 비교과 활동
**5**: 대운의 학업 유리 시기
**6**: 학기별 준비 로드맵""",
}
