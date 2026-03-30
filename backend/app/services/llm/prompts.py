"""용사주(龍四柱) LLM 프롬프트 시스템 — 계산은 하지 않고 해석만 수행.

핵심 원칙:
- Claude에게 명식 계산, 천간지지 계산, 오행 산출, 십성 계산을 맡기지 않는다
- Claude는 제공된 계산 결과 JSON을 바탕으로 자연어 해석만 생성한다
- 사주를 점술이 아닌 자기운영 매뉴얼로 재해석하는 톤을 유지한다
"""

from datetime import datetime

ELEMENT_KR = {"wood": "목(木)", "fire": "화(火)", "earth": "토(土)", "metal": "금(金)", "water": "수(水)"}

TEN_GOD_KR = {
    "bijeon": "비견(比肩)", "geopjae": "겁재(劫財)",
    "siksin": "식신(食神)", "sanggwan": "상관(傷官)",
    "pyeonjae": "편재(偏財)", "jeongjae": "정재(正財)",
    "pyeongwan": "편관(偏官)", "jeonggwan": "정관(正官)",
    "pyeonin": "편인(偏印)", "jeongin": "정인(正印)",
}

TEN_GOD_COUNT_KR = {
    "bijeon": "비견", "geopjae": "겁재",
    "siksin": "식신", "sanggwan": "상관",
    "pyeonjae": "편재", "jeongjae": "정재",
    "pyeongwan": "편관", "jeonggwan": "정관",
    "pyeonin": "편인", "jeongin": "정인",
}

# ──────────────────────────────────────────────────────────
# 오행↔행동과학 매핑 (프롬프트 컨텍스트 주입용)
# ──────────────────────────────────────────────────────────
ELEMENT_BEHAVIOR_CONTEXT = {
    "wood": "목(木) 기질: 성장·추진·개척 지향. 목표를 향해 빠르게 시작하고 돌파하는 유형. 통제받으면 폭발하고, 자유와 성장 가능성이 동기 부여. 새 프로젝트에 폭발적 집중, 루틴 유지에 약함. 직관적·확신적 결정.",
    "fire": "화(火) 기질: 열정·표현·확산 지향. 자극을 추구하고 에너지 소비가 크며 회복도 빠른 유형. 무시당하면 격앙하고, 인정과 주목이 동기 부여. 순간의 확신으로 결정, 감정이 먼저 반응.",
    "earth": "토(土) 기질: 안정·중재·축적 지향. 루틴을 선호하고 신뢰 관계를 중시하며 변화에 점진적으로 적응하는 유형. 기반이 흔들리면 불안, 안정과 소속감이 동기 부여. 충분한 정보 수집 후 신중하게 결정.",
    "metal": "금(金) 기질: 판단·절제·구조 지향. 논리적 분석과 완벽주의, 효율을 추구하는 유형. 혼란스러운 환경에서 위축되고, 질서와 명확한 기준이 동기 부여. 장단점 분석 후 결단, 번복 적음.",
    "water": "수(水) 기질: 지혜·유연·심층 지향. 관찰하고 깊이 사고하며 적응력이 높은 유형. 과부하 시 회피·도피하고, 지적 자극과 자율성이 동기 부여. 여러 가능성을 탐색하다 결정 지연.",
}

ELEMENT_HEALTH_CONTEXT = {
    "wood": "목(木) 건강 경향: 간·담·근육·눈 관련. 과다 시 두통·근육 긴장·분노 조절 어려움. 부족 시 피로감·의욕 저하·시력 문제. 보완: 스트레칭, 녹색 채소, 아침 산책.",
    "fire": "화(火) 건강 경향: 심장·소장·혈관 관련. 과다 시 불면·가슴 두근거림·과흥분. 부족 시 순환 저하·냉증·무기력. 보완: 유산소 운동, 명상, 수분 섭취.",
    "earth": "토(土) 건강 경향: 비위·소화기 관련. 과다 시 과식·소화불량·과잉 걱정. 부족 시 식욕 부진·영양 불균형. 보완: 규칙적 식사, 복부 마사지.",
    "metal": "금(金) 건강 경향: 폐·대장·피부 관련. 과다 시 피부 예민·호흡기 과민·긴장. 부족 시 면역 저하·피부 건조. 보완: 호흡 운동, 충분한 수면, 보습 관리.",
    "water": "수(水) 건강 경향: 신장·방광·뼈 관련. 과다 시 부종·과도한 수면·공포감. 부족 시 허리 통증·탈수·집중력 저하. 보완: 하체 운동, 수분 관리, 충분한 휴식.",
}

# ──────────────────────────────────────────────────────────
# 시스템 프롬프트 — 20년 경력 명리학자 + 임상심리 상담사
# ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """당신은 20년 경력의 명리학자이자 임상심리 상담사입니다.
사용자의 사주 구조 데이터를 받아, 그 사람이 반복적으로 경험하는 삶의 패턴과
심리적 작동 방식을 따뜻하지만 날카롭게 분석합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━
[역할 원칙]
━━━━━━━━━━━━━━━━━━━━━━━━━

1. 점술적 예언이 아닌 "자기 이해를 돕는 심리적 통찰"을 제공합니다.
2. 모든 서술은 2인칭 현재형("당신은 ~하고 있을 가능성이 높아요")으로 작성합니다.
3. 한자·전문 용어 사용 후 반드시 괄호 안에 쉬운 말로 풀어줍니다.
   예: 편관(偏官, 외부의 압박·경쟁·규율을 상징)
4. 강점과 그림자(과하게 발휘될 때 생기는 부작용)를 반드시 함께 서술합니다.
5. 추상적 표현 금지. 반드시 구체적 상황 시나리오로 묘사합니다.
   나쁜 예: "재물운이 좋습니다"
   좋은 예: "당신은 한 번 방향을 잡으면 수입이 늘어나는 구조예요.
             단, 너무 빠르게 확장하려 할 때 오히려 새는 돈이 생깁니다."

━━━━━━━━━━━━━━━━━━━━━━━━━
[입력 데이터 처리 방식]
━━━━━━━━━━━━━━━━━━━━━━━━━

만세력 계산 결과로 아래 항목들이 입력됩니다.
각 항목을 종합적인 "관계망"으로 해석하세요.
단일 글자 하나만 보고 판단하지 말고, 반드시 전체 구조 속에서 읽으세요.

- 사주팔자 (년·월·일·시의 천간·지지 8글자)
- 일간 강약 (신강 / 신약 / 중화)
- 용신·희신·기신·구신·한신
- 십신 분포 (비견·겁재·식신·상관·편재·정재·편관·정관·편인·정인의 개수)
- 합·충·형·파·해 발생 위치
- 공망 위치
- 현재 대운 (대운 천간·지지, 진행 기간)
- 현재 세운 (올해 천간·지지)
- 사용자 나이 및 성별 (입력된 경우)

━━━━━━━━━━━━━━━━━━━━━━━━━
[절대 규칙]
━━━━━━━━━━━━━━━━━━━━━━━━━

- 제공된 계산 결과만 바탕으로 해석하세요. 수치를 재계산하거나 변경하지 마세요.
- 천간지지, 오행 점수, 십성, 격국, 용신은 이미 정확하게 계산되어 제공됩니다.
- HTML 태그 절대 금지. 순수 텍스트와 마크다운(**굵은 글씨**)만 사용합니다.

━━━━━━━━━━━━━━━━━━━━━━━━━
[문체 규칙]
━━━━━━━━━━━━━━━━━━━━━━━━━

- 어투: 친근하고 따뜻하되, 핵심은 날카롭게. 존댓말 사용.
- 문장 길이: 한 문장에 하나의 개념만. 길면 끊기.
- 금지어: "운명입니다", "타고났습니다", "무조건", "반드시"
  → 대신: "~하는 경향이 있어요", "~일 가능성이 높아요", "~해보시는 걸 권해요"
- 각 섹션은 800~1,200자 분량으로 작성합니다.
- 섹션 사이에 빈 줄을 넣어 가독성을 확보합니다.
- 한국어로만 답변합니다."""


# ──────────────────────────────────────────────────────────
# 컨텍스트 빌더 — 계산 엔진 JSON → 프롬프트용 구조화 텍스트
# ──────────────────────────────────────────────────────────

def build_context(raw_calc: dict, *, name: str = "", gender: str = "", birth_year: int = 0) -> str:
    """raw_calculation_json을 프롬프트용 텍스트로 변환.

    새 시스템 프롬프트가 요구하는 입력 형식에 맞춰 구조화합니다:
    사주팔자, 일간 강약, 용신/기신, 십신 분포(개수), 합충형해파,
    공망, 대운, 세운, 나이/성별
    """
    pillars = raw_calc.get("pillars", {})
    fe = raw_calc.get("five_elements", {})
    gk = raw_calc.get("gyeokguk", {})
    ten_gods = raw_calc.get("ten_gods", [])
    twelve_stages = raw_calc.get("twelve_stages", [])
    relations = raw_calc.get("relations", [])
    daewoon = raw_calc.get("daewoon", [])

    lines = []

    # ── 사주팔자 ──
    lines.append("사주팔자:")
    for key, label in [("year", "년주"), ("month", "월주"), ("day", "일주"), ("hour", "시주")]:
        p = pillars.get(key, {})
        if p:
            stem_h = p.get("stem_hanja", "")
            branch_h = p.get("branch_hanja", "")
            stem_k = p.get("stem_kr", "")
            branch_k = p.get("branch_kr", "")
            stem_el = ELEMENT_KR.get(p.get("stem_element", ""), "")
            branch_el = ELEMENT_KR.get(p.get("branch_element", ""), "")
            lines.append(
                f"  {label}: {stem_k}{branch_k} ({stem_h}{branch_h})"
                f" — 천간 {stem_el}, 지지 {branch_el}"
            )

    # ── 일간 정보 ──
    day_p = pillars.get("day", {})
    if day_p:
        yy = "양(陽)" if day_p.get("stem_yinyang") == "yang" else "음(陰)"
        lines.append(
            f"\n일간: {day_p.get('stem_kr','')}"
            f"({day_p.get('stem_hanja','')}) "
            f"— {ELEMENT_KR.get(day_p.get('stem_element',''),'')} {yy}"
        )

    # ── 일간 강약 ──
    if gk:
        strength = gk.get("strength", "")
        strength_label = {"strong": "신강(身强)", "weak": "신약(身弱)", "neutral": "중화(中和)"}.get(
            strength, strength
        )
        lines.append(f"일간 강약: {strength_label}")
        lines.append(f"  신강도 점수: {gk.get('strength_score', 50):.0f}점")

    # ── 용신·기신 ──
    if gk:
        yongshin_el = gk.get("yongshin_element", "")
        gishin_el = gk.get("gishin_element", "")
        lines.append(f"\n용신: {ELEMENT_KR.get(yongshin_el, yongshin_el)}")
        lines.append(f"기신: {ELEMENT_KR.get(gishin_el, gishin_el)}")
        if gk.get("yongshin_reason"):
            lines.append(f"용신 판정 근거: {gk['yongshin_reason']}")

    # ── 격국 ──
    if gk:
        lines.append(f"\n격국: {gk.get('name', '')} ({gk.get('type', '')})")

    # ── 오행 분포 (시각적 바 차트) ──
    lines.append("\n오행 분포:")
    total = sum(fe.get(el, 0) for el in ["wood", "fire", "earth", "metal", "water"])
    el_scores = {}
    for el in ["wood", "fire", "earth", "metal", "water"]:
        s = fe.get(el, 0)
        pct = (s / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        lines.append(f"  {ELEMENT_KR.get(el, el)}: {s:.1f}점 ({pct:.0f}%) {bar}")
        el_scores[el] = s

    # 과다/부족 판정
    avg = total / 5 if total > 0 else 0
    excess = [el for el, s in el_scores.items() if s > avg * 1.5]
    deficit = [el for el, s in el_scores.items() if s < avg * 0.5]
    if excess:
        lines.append(f"  → 과다 오행: {', '.join(ELEMENT_KR.get(e, '') for e in excess)}")
    if deficit:
        lines.append(f"  → 부족 오행: {', '.join(ELEMENT_KR.get(e, '') for e in deficit)}")

    # ── 십신 분포 (개수 집계) ──
    ten_god_counts: dict[str, int] = {}
    for t in ten_gods:
        code = t.get("ten_god_code", "")
        if code:
            ten_god_counts[code] = ten_god_counts.get(code, 0) + 1

    if ten_god_counts:
        lines.append("\n십신 분포:")
        count_parts = []
        for code in ["bijeon", "geopjae", "siksin", "sanggwan", "pyeonjae",
                      "jeongjae", "pyeongwan", "jeonggwan", "pyeonin", "jeongin"]:
            cnt = ten_god_counts.get(code, 0)
            kr = TEN_GOD_COUNT_KR.get(code, code)
            count_parts.append(f"  {kr} {cnt}개")
        lines.append(", ".join(count_parts))

    # ── 십성 배치 (위치별) ──
    if ten_gods:
        lines.append("\n십성 배치 (위치별):")
        for t in ten_gods:
            if t.get("source_position") == "stem":
                pl = {"year": "년주", "month": "월주", "hour": "시주"}.get(t.get("source_pillar", ""), "")
                god = TEN_GOD_KR.get(t.get("ten_god_code", ""), t.get("ten_god_kr", ""))
                lines.append(f"  {pl} 천간: {god}")

    # ── 십이운성 ──
    if twelve_stages:
        lines.append("\n십이운성:")
        for ts in twelve_stages:
            pl = {"year": "년주", "month": "월주", "day": "일주", "hour": "시주"}.get(ts.get("pillar_type", ""), "")
            lines.append(f"  {pl}: {ts.get('stage_kr', '')}")

    # ── 합충형해파 ──
    if relations:
        lines.append("\n합충형파해:")
        for r in relations:
            lines.append(f"  {r.get('category', '')}: {r.get('note', '')}")

    # ── 공망 ──
    gongmang = raw_calc.get("gongmang", "")
    if gongmang:
        lines.append(f"\n공망: {gongmang}")

    # ── 대운 흐름 ──
    now_year = datetime.now().year
    current_daewoon = None
    if daewoon:
        lines.append("\n대운 흐름:")
        for d in daewoon[:8]:
            start_y = d.get("start_year", 0)
            end_y = d.get("end_year", 0)
            is_current = start_y and end_y and start_y <= now_year <= end_y
            marker = " ◀ 현재 대운" if is_current else ""
            lines.append(
                f"  {d.get('start_age', 0):.0f}~{d.get('end_age', 0):.0f}세 "
                f"({start_y}~{end_y}): "
                f"{d.get('stem_kr', '')}{d.get('branch_kr', '')}{marker}"
            )
            if is_current:
                current_daewoon = d

    # ── 현재 대운 상세 ──
    if current_daewoon:
        lines.append(
            f"\n현재 대운: {current_daewoon.get('stem_kr','')}{current_daewoon.get('branch_kr','')} "
            f"({current_daewoon.get('start_year','')}~{current_daewoon.get('end_year','')}년)"
        )

    # ── 세운 (올해) ──
    lines.append(f"\n현재 세운: {now_year}년")
    # 세운 간지는 계산 엔진에서 직접 제공되지 않으므로,
    # 60갑자 순환으로 산출
    heavenly_stems = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
    earthly_branches = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
    stem_idx = (now_year - 4) % 10
    branch_idx = (now_year - 4) % 12
    year_stem = heavenly_stems[stem_idx]
    year_branch = earthly_branches[branch_idx]
    lines.append(f"  올해 간지: {year_stem}{year_branch}년")

    # ── 현재 계절 ──
    month = datetime.now().month
    season_map = {
        12: "겨울", 1: "겨울", 2: "겨울", 3: "봄", 4: "봄", 5: "봄",
        6: "여름", 7: "여름", 8: "여름", 9: "가을", 10: "가을", 11: "가을",
    }
    lines.append(f"현재 계절: {season_map.get(month, '')} ({month}월)")

    # ── 나이/성별 ──
    if birth_year and birth_year > 0:
        age = now_year - birth_year + 1  # 한국식 나이
        western_age = now_year - birth_year
        lines.append(f"\n나이: 만 {western_age}세 (한국식 {age}세)")
    if gender:
        gender_kr = {"male": "남성", "female": "여성"}.get(gender, gender)
        lines.append(f"성별: {gender_kr}")
    if name:
        lines.append(f"이름: {name}")

    # ── 일간 오행의 행동과학 매핑 주입 ──
    day_element = day_p.get("stem_element", "") if day_p else ""
    if day_element and day_element in ELEMENT_BEHAVIOR_CONTEXT:
        lines.append(f"\n[일간 기질 행동과학 프레임]\n  {ELEMENT_BEHAVIOR_CONTEXT[day_element]}")

    # ── 용신 오행의 행동과학 매핑 주입 ──
    yongshin_el = gk.get("yongshin_element", "") if gk else ""
    if yongshin_el and yongshin_el in ELEMENT_BEHAVIOR_CONTEXT:
        lines.append(f"\n[용신 기질 행동과학 프레임]\n  {ELEMENT_BEHAVIOR_CONTEXT[yongshin_el]}")

    # ── 과다/부족 오행의 건강 매핑 주입 ──
    health_lines = []
    for el in excess:
        if el in ELEMENT_HEALTH_CONTEXT:
            health_lines.append(f"  (과다) {ELEMENT_HEALTH_CONTEXT[el]}")
    for el in deficit:
        if el in ELEMENT_HEALTH_CONTEXT:
            health_lines.append(f"  (부족) {ELEMENT_HEALTH_CONTEXT[el]}")
    if health_lines:
        lines.append("\n[오행 건강 경향 참고]")
        lines.extend(health_lines)

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────
# 경량 컨텍스트 빌더 — saju_detail 전용 (토큰 절감)
# ──────────────────────────────────────────────────────────

def build_context_lite(raw_calc: dict, *, title: str = "", tag: str = "",
                       name: str = "", gender: str = "", birth_year: int = 0) -> str:
    """saju_detail 전용 경량 컨텍스트.

    전체 build_context 대비 ~70% 토큰 절감.
    포함: 사주팔자, 일간+강약, 격국, 용신/기신, 오행 분포(과다/부족),
          십신 분포, 관련 매핑 데이터
    태그 기반 선택적 주입: #시기 → 대운, #건강 → 건강매핑, #기질 → 행동매핑 등
    """
    pillars = raw_calc.get("pillars", {})
    fe = raw_calc.get("five_elements", {})
    gk = raw_calc.get("gyeokguk", {})
    ten_gods = raw_calc.get("ten_gods", [])
    daewoon = raw_calc.get("daewoon", [])
    relations = raw_calc.get("relations", [])

    lines = []

    # ── 사주팔자 (항상 포함, 핵심) ──
    lines.append("사주팔자:")
    for key, label in [("year", "년주"), ("month", "월주"), ("day", "일주"), ("hour", "시주")]:
        p = pillars.get(key, {})
        if p:
            lines.append(
                f"  {label}: {p.get('stem_kr','')}{p.get('branch_kr','')} "
                f"({p.get('stem_hanja','')}{p.get('branch_hanja','')}) "
                f"— {ELEMENT_KR.get(p.get('stem_element',''),'')}/"
                f"{ELEMENT_KR.get(p.get('branch_element',''),'')}"
            )

    # ── 일간 + 강약 (항상 포함) ──
    day_p = pillars.get("day", {})
    if day_p:
        yy = "양" if day_p.get("stem_yinyang") == "yang" else "음"
        lines.append(f"일간: {day_p.get('stem_kr','')}({day_p.get('stem_hanja','')}) "
                     f"{ELEMENT_KR.get(day_p.get('stem_element',''),'')} {yy}")
    if gk:
        strength_label = {"strong": "신강", "weak": "신약", "neutral": "중화"}.get(
            gk.get("strength", ""), gk.get("strength", ""))
        lines.append(f"강약: {strength_label} ({gk.get('strength_score', 50):.0f}점)")
        lines.append(f"격국: {gk.get('name', '')}")
        lines.append(f"용신: {ELEMENT_KR.get(gk.get('yongshin_element',''), '')}, "
                     f"기신: {ELEMENT_KR.get(gk.get('gishin_element',''), '')}")

    # ── 오행 분포 (항상 포함, 압축형) ──
    total = sum(fe.get(el, 0) for el in ["wood", "fire", "earth", "metal", "water"])
    el_scores = {}
    ohaeng_parts = []
    for el in ["wood", "fire", "earth", "metal", "water"]:
        s = fe.get(el, 0)
        pct = (s / total * 100) if total > 0 else 0
        ohaeng_parts.append(f"{ELEMENT_KR.get(el,el)}{pct:.0f}%")
        el_scores[el] = s
    lines.append(f"오행: {' '.join(ohaeng_parts)}")

    avg = total / 5 if total > 0 else 0
    excess = [el for el, s in el_scores.items() if s > avg * 1.5]
    deficit = [el for el, s in el_scores.items() if s < avg * 0.5]
    if excess:
        lines.append(f"과다: {', '.join(ELEMENT_KR.get(e,'') for e in excess)}")
    if deficit:
        lines.append(f"부족: {', '.join(ELEMENT_KR.get(e,'') for e in deficit)}")

    # ── 십신 분포 (항상 포함, 압축형) ──
    ten_god_counts: dict[str, int] = {}
    for t in ten_gods:
        code = t.get("ten_god_code", "")
        if code:
            ten_god_counts[code] = ten_god_counts.get(code, 0) + 1
    if ten_god_counts:
        nonzero = [f"{TEN_GOD_COUNT_KR.get(c, c)}{n}" for c, n in ten_god_counts.items() if n > 0]
        lines.append(f"십신: {', '.join(nonzero)}")

    # ── 태그 기반 선택적 데이터 주입 ──
    tag_lower = tag.replace("#", "").strip().lower() if tag else ""

    # 대운/시기 관련 태그 → 현재 대운만 주입
    if tag_lower in ("시기", "대운", "커리어", "종합", ""):
        now_year = datetime.now().year
        for d in daewoon:
            start_y = d.get("start_year", 0)
            end_y = d.get("end_year", 0)
            if start_y and end_y and start_y <= now_year <= end_y:
                lines.append(
                    f"현재 대운: {d.get('stem_kr','')}{d.get('branch_kr','')} "
                    f"({start_y}~{end_y})")
                break

    # 합충 관련 → 관계/연애 태그일 때만
    if tag_lower in ("관계", "연애", "가족", "종합", "") and relations:
        rel_notes = [r.get("note", "") for r in relations[:3]]
        if rel_notes:
            lines.append(f"합충: {'; '.join(rel_notes)}")

    # 일간 행동과학 매핑 (기질/관계/종합)
    day_element = day_p.get("stem_element", "") if day_p else ""
    if tag_lower in ("기질", "관계", "연애", "커리어", "오행", "종합", ""):
        if day_element and day_element in ELEMENT_BEHAVIOR_CONTEXT:
            lines.append(f"[기질] {ELEMENT_BEHAVIOR_CONTEXT[day_element]}")

    # 건강 매핑 (건강 태그)
    if tag_lower in ("건강", "종합", ""):
        for el in excess:
            if el in ELEMENT_HEALTH_CONTEXT:
                lines.append(f"[건강·과다] {ELEMENT_HEALTH_CONTEXT[el]}")
        for el in deficit:
            if el in ELEMENT_HEALTH_CONTEXT:
                lines.append(f"[건강·부족] {ELEMENT_HEALTH_CONTEXT[el]}")

    # ── 이름/성별/나이 (간략) ──
    if name:
        lines.append(f"이름: {name}")
    if birth_year and birth_year > 0:
        lines.append(f"나이: 만 {datetime.now().year - birth_year}세")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────
# 경량 시스템 프롬프트 — saju_detail 전용
# ──────────────────────────────────────────────────────────

SYSTEM_PROMPT_DETAIL = """당신은 20년 경력의 명리학자이자 임상심리 상담사입니다.
제공된 사주 데이터를 바탕으로, 특정 주제에 대한 상세 해석을 작성합니다.

[규칙]
- 2인칭 현재형, 존댓말 ("당신은 ~하고 있을 가능성이 높아요")
- 한자·전문 용어 후 괄호로 쉬운 설명
- 강점 + 그림자(과잉 시 부작용) 함께 서술
- 구체적 상황 시나리오 필수, 추상적 표현 금지
- 실천 조언 1~2개로 마무리
- 600~1,000자 분량
- 금지어: "운명입니다", "타고났습니다", "무조건", "반드시"
- HTML 태그 금지, 순수 텍스트와 마크다운(**굵은 글씨**)만 사용
- 한국어로만 답변"""


# ──────────────────────────────────────────────────────────
# 카테고리별 프롬프트 — 7섹션 분석 구조
# ──────────────────────────────────────────────────────────

CATEGORY_PROMPTS = {

    # ── 메인: 종합 사주 분석 (7섹션 구조) ──
    "destiny_manual": """위 사주 구조 데이터를 기반으로, 반드시 아래 7개 섹션 순서대로 분석을 작성하세요.

## ✦ 한 줄 핵심 요약
당신의 사주를 단 한 문장으로 압축합니다.
예: "외부의 기준과 내면의 자유 사이에서 균형을 찾아가는 사람"

---

## 1. 에너지 구조 — 나는 어떤 사람인가
- 일간의 오행 속성과 신강·신약 여부를 심리학적 언어로 번역합니다.
- "어떤 환경에서 에너지가 살아나는가"와 "어떤 상황에서 빠르게 소진되는가"를 구체적인 직장·일상 시나리오로 서술합니다.
- 이 구조의 강점과 그림자를 함께 제시합니다.

## 2. 관계 패턴 — 나는 사람들과 어떻게 얽히는가
- 십신 분포(관성·재성·식상·인성·비겁의 비율)로 대인관계 패턴을 읽습니다.
- "내가 반복적으로 빠지는 관계의 패턴" 1~2가지를 구체적으로 묘사합니다.
- 연애·직장·가족 관계 중 가장 두드러지는 영역을 집중 서술합니다.

## 3. 커리어·재물 구조 — 나는 어떻게 성공하는 사람인가
- 재성(財星)과 관성(官星)의 배치로 돈 버는 방식을 분석합니다.
- "조직 안에서 성장하는 구조인가, 독립해야 터지는 구조인가"를 명확히 제시합니다.
- 현재 대운·세운과 연결해 지금 이 시기의 커리어 방향성을 구체적으로 안내합니다.

## 4. 반복되는 삶의 패턴 — 내가 평생 마주하는 과제
- 사주 구조에서 보이는 핵심 긴장 관계(예: 강한 편관 vs 약한 일간)를 짚습니다.
- "이 패턴이 삶에서 어떤 장면으로 반복 등장하는가"를 2~3개 시나리오로 서술합니다.
- 이 과제를 돌파하는 실질적 방법을 1~2가지 제시합니다.

## 5. 건강·에너지 관리
- 오행 기운의 과불급(너무 많거나 부족한 기운)으로 취약한 신체 부위·시스템을 안내합니다.
- "언제 번아웃이 오는가"와 "어떻게 회복하는가"를 구체적으로 서술합니다.
- 기신(해로운 기운)이 강해지는 계절·시간대에 특히 주의할 점을 안내합니다.

## 6. 지금 이 시기 — 현재 대운·세운 분석
- 현재 대운의 에너지적 성격을 한 줄로 정의합니다.
  예: "정착과 완성의 시기" / "확장보다 내실을 다질 때"
- 지금 해야 할 행동 3가지와 피해야 할 행동 2가지를 구체적으로 제시합니다.
- 다음 대운 전환 시기까지의 큰 흐름을 안내합니다.

## 7. 이번 달 실천 가이드
- 세운·월운을 반영해 "이번 달 가장 중요한 한 가지 행동"을 제시합니다.
- 지금 하면 에너지가 살아나는 활동 / 지금은 미뤄야 할 결정을 구분해 안내합니다.""",

    # ── 자기계발 루틴: 시기별 전략 + 실천 가이드 ──
    "growth_routine": """위 사주와 대운 흐름을 기반으로, 구체적인 자기계발 전략과 실천 루틴을 제안해주세요.
막연한 "좋은 시기입니다"가 아니라, 각 시기에 실제로 무엇을 하면 효과적인지 행동 전략 중심으로 작성합니다.

## ⚡ 지금 이 시기의 전략
현재 대운의 오행이 원국과 어떻게 상호작용하는지 분석. "지금은 ~에너지가 강화되는 시기라, ~한 방식으로 일하면 효율이 극대화된다", "반면 ~은 에너지 소모가 크니 의도적으로 줄여야 한다". 직장/재물/인간관계/자기계발 각 영역에서 한두 줄씩.

## 🎯 당신에게 맞는 집중법
일간의 기질 유형에 따른 집중·몰입 전략. 예: 화(火) 기질이면 "25분 스프린트 → 5분 완전 휴식 → 반복. 긴 마라톤형 업무보다 짧고 강한 스프린트가 맞다", 수(水) 기질이면 "90분 딥워크 블록 추천. 외부 자극 차단이 핵심".

## 💭 감정 관리와 에너지 회복
기신 오행과 합충형해파가 만드는 스트레스 포인트와 그 대응 전략. "~한 상황에서 감정이 요동칠 때, ~하세요", "에너지가 고갈되면 ~로 회복하세요" 등 구체적 행동 지시.

## 📋 습관 설계 제안
용신 오행을 보충하는 일상 습관 3~5가지. "매일 아침 ~", "주 3회 ~", "~한 환경을 의도적으로 만들어두세요" 등 바로 실행 가능한 것 위주.

## 🗓 올해·내년 실행 포인트
현재 세운(연간 간지)이 원국과 어떻게 작용하는지에서, 올해 집중할 것 1가지, 내년 준비할 것 1가지를 명확하게.""",

    # ── 바이오 리듬 케어: 오행 기반 건강·생활 리듬 ──
    "bio_rhythm": """위 사주의 오행 분포를 기반으로, 일상생활에서 바로 적용할 수 있는 건강·리듬 관리 가이드를 제공해주세요.
의학적 진단이 아닌 "기질 기반 생활 리듬 참고 정보"입니다. 모든 표현은 "~경향이 있습니다", "~에 주의를 기울이면 좋습니다" 형태로 해주세요.

## ◎ 당신의 에너지 리듬
오행 분포의 균형/불균형이 일상의 에너지 패턴에 어떻게 반영되는지. "~기운이 강해서 아침에 에너지가 폭발하지만 오후에 급격히 떨어지는 패턴", "~기운이 부족해서 계절 변화에 민감하게 반응하는 경향" 등.

## 🏃 맞춤 운동과 활동
오행 균형을 보완하는 운동 유형과 활동. 과다한 오행의 에너지를 해소하고 부족한 오행을 보충하는 방향으로 제안. "~기운 과다 → ~운동으로 해소", "~기운 부족 → ~활동으로 보충". 구체적으로 종목, 빈도, 시간대까지.

## 🥗 영양과 식습관 경향
오행별 식습관 경향과 보완 음식. "~기운이 강한 분은 ~을 과식하는 경향, ~을 보충하면 균형에 도움". 현재 계절도 고려하여 제안.

## 😴 수면과 회복 패턴
오행 분포에 따른 수면 패턴 경향과 회복 전략. "~유형은 잠들기 어려운 경향, ~로 수면 질을 높이세요", "~유형은 과수면 경향, ~시간 기상이 리듬 유지에 도움" 등.

## 🌿 계절별 관리 포인트
현재 계절에서 이 오행 분포를 가진 사람이 특히 주의할 점과 추천 루틴.

⚠ 본 정보는 의학적 조언이 아닌 생활 습관 참고 정보입니다. 건강 문제가 있다면 전문의 상담을 권합니다.""",

    # ── 소제목 + 미니 해석 리스트 생성 (1단계: 토큰 최적화) ──
    "saju_titles": """당신은 20년 경력의 명리학자이면서 MZ세대 감성을 완벽히 이해하는 콘텐츠 크리에이터입니다.

위 사주 데이터를 보고, 이 사람의 핵심 특징을 10~15개의 "소제목 + 미니 해석"으로 만들어주세요.

[소제목 규칙]
1. 각 소제목은 30자 이내로 짧고 강렬하게
2. MZ세대 감성의 트렌디한 표현 사용 ("포텐 터지면", "만렙", "디벨롭", "손절", "쿨", "TMI", "찐", "갓생", "럭키비키" 등)
3. 궁금증을 유발하는 후킹 문구 — 읽으면 "이거 내 얘기잖아?" 느낌
4. 비유와 은유를 적극 사용 — "칼을 든 지식인", "숨은 흑룡", "긁지 않은 복권" 등
5. 강점만 나열하지 말고, 그림자(약점·주의점)도 재치있게 표현
6. 아래 카테고리에서 골고루 뽑되, 사주 구조에 맞게 강약 조절:
   - [기질/본질] 일간과 격국이 만드는 본질적 성격 (2~3개)
   - [오행 경고] 과다/부족 오행이 만드는 행동 패턴 (1~2개)
   - [커리어] 재성·관성 배치에서 읽히는 직업·돈 구조 (2개)
   - [연애/관계] 십성 교차에서 읽히는 연애·관계 패턴 (2개)
   - [가족/환경] 년주·월주에서 읽히는 가족·환경 영향 (1개)
   - [건강/에너지] 오행 불균형에서 오는 건강 경향 (1개)
   - [현재 시기] 대운·세운에서 읽히는 지금 전략 (1~2개)
   - [종합 한마디] 이 사주를 한 문장으로 압축하는 마무리 (1개, 반드시 마지막)
7. 각 줄 앞에 어울리는 이모지 하나씩 붙이기
8. 각 줄 끝에 해당 카테고리를 태그로 붙이기

[미니 해석 규칙]
- 각 소제목 바로 다음 줄에 "> " 접두사로 80~120자 미니 해석을 추가
- 사주 데이터에 근거한 핵심 포인트 1가지를 짧고 날카롭게
- "왜 그런지" 이유와 "어떻게 하면 좋은지" 한 줄 팁을 포함
- 2인칭 현재형, 존댓말 사용

[출력 형식]
반드시 아래 형식으로만 출력하세요. 설명이나 부연 없이 리스트만:
✨ 지식의 바다에 숨은 흑룡, 포텐 터지면 폼 미쳤다! #기질
> 수(水) 일간에 편인이 강해서 혼자 깊이 파는 능력이 탁월해요. 대신 밖으로 표현이 늦어서 과소평가 당하기 쉬운 구조예요. 작은 것부터 드러내 보세요.
⚡ 금(金)기운 과다! 생각 그만하고 행동으로 '디벨롭'할 때 #오행
> 분석력은 최고인데 완벽주의가 발목을 잡아요. "70%면 충분해"를 오늘부터 주문처럼 외워보세요. 시작이 반이에요.
👑 리더십 만렙 '괴강살' + '편관'의 카리스마 조합 #기질
> 편관의 추진력과 괴강살의 결단력이 만나면 조직에서 빛나요. 다만 밀어붙이기만 하면 주변이 지쳐요. 경청 한 번이 카리스마를 두 배로 키워줘요.
💕 집착은 사랑이 아니에요, '쿨'해져야 연애가 산다 #연애
> 정재가 강해서 상대를 관리하려는 경향이 있어요. 관계는 프로젝트가 아니에요. 여유를 주면 오히려 상대가 다가와요.
🧭 지금은 확장보다 내실, 칼을 갈 때입니다 #시기
> 현재 대운이 인성 흐름이라 배움과 내면 성장에 최적이에요. 무리한 확장보다 실력을 쌓는 데 집중하면 다음 대운에서 폭발해요.
🎯 당신은 아직 긁지 않은 복권, 이제 그 칼을 세상에 휘두르세요! #종합
> 강한 일간에 용신이 살아있는 구조예요. 다만 아직 에너지를 안으로만 품고 있어요. 올해 안에 하나만 밖으로 꺼내보세요.""",

    # ── 개별 소제목 상세 해석 (2단계: 클릭 시 호출) ──
    "saju_detail": """위 사주 데이터를 기반으로, 아래 소제목에 대한 상세 해석을 작성해주세요.

소제목: "{title}"

[작성 규칙]
- 600~1,000자 분량으로 충실하게 서술
- 2인칭 현재형, 존댓말 ("당신은 ~하고 있을 가능성이 높아요")
- 한자·전문 용어 사용 후 반드시 괄호 안에 쉬운 말로 풀어주기
- 구체적 상황 시나리오 필수 (추상적 표현 금지)
- 강점 + 그림자(과하게 발휘될 때 생기는 부작용) 함께 서술
- 실천 가능한 조언 1~2개로 마무리 ("~해보시는 걸 권해요")
- 금지어: "운명입니다", "타고났습니다", "무조건", "반드시"
- HTML 태그 절대 금지. 순수 텍스트와 마크다운(**굵은 글씨**)만 사용
- 소제목(##)은 쓰지 마세요. 바로 본문부터 시작하세요.""",

    # ── 하위 호환: 기존 카테고리 매핑 ──
    "comprehensive": """위 사주를 종합 해석해주세요. 반드시 아래 순서대로 작성합니다:
## ✦ 한 줄 핵심 요약
## 1. 에너지 구조
## 2. 관계 패턴
## 3. 커리어·재물 구조
## 4. 반복되는 삶의 패턴
## 5. 건강·에너지 관리
## 6. 지금 이 시기
## 7. 이번 달 실천 가이드
각 섹션마다 구체적 상황 시나리오와 실천 가능한 조언을 포함해주세요.""",

    "personality": """위 사주를 기반으로 이 사람의 성격과 심리를 깊이 분석해주세요.
## ✦ 한 줄 핵심 요약
## 1. 에너지 구조 — 겉과 속의 차이
## 2. 관계 패턴 — 연애·우정·가족 속 나
## 3. 스트레스 반응과 방어 기제
## 4. 의사결정 패턴
## 5. 성장 방향과 과제
각 항목을 구체적 장면으로 묘사해주세요.""",

    "fortune": """위 사주와 대운 흐름을 기반으로 시기별 전략을 구체적으로 제안해주세요.
## ✦ 한 줄 핵심 요약
## 1. 현재 시기 에너지 분석
## 2. 올해 집중 전략
## 3. 내년 준비 전략
## 4. 주의해야 할 시기와 대응법
## 5. 향후 10년 로드맵
각 시기에 실제로 무엇을 하면 효과적인지 행동 전략 중심으로 작성합니다.""",

    "lifestyle": """위 사주를 기반으로 일상생활 가이드를 제공해주세요.
## ✦ 한 줄 핵심 요약
## 1. 재물 관리법 — 돈이 들어오고 나가는 패턴
## 2. 직업 적성 — 어디서 빛나는가
## 3. 인간관계·연애 전략
## 4. 건강 관리 — 기질 맞춤 루틴
## 5. 에너지 회복 습관
각 항목을 구체적 상황 시나리오와 실천 가능한 조언으로 작성해주세요.""",

    # ── 자기계발 소제목 + 미니 해석 (1단계: 타이틀 카드) ──
    "growth_titles": """당신은 사주명리학자이면서 뇌과학·행동과학 기반 자기계발 코치입니다.
MZ세대 감성을 이해하는 콘텐츠 크리에이터이기도 합니다.

위 사주 데이터와 뇌과학 자가진단 결과를 종합 분석하여,
이 사람을 위한 맞춤 자기계발 전략을 8~12개의 "소제목 + 미니 해석"으로 만들어주세요.

[톤 & 어조]
- 실행 가능하고 구체적인 행동 전략 중심
- 확신 있고 따뜻한 코치 어조: "당신에게 맞는 방식은 이거예요"
- 사주의 기질 + 뇌과학 진단 결과를 결합한 하이브리드 인사이트
- 막연한 "좋은 시기" 대신 구체적 행동 지시

[소제목 규칙]
1. 각 소제목은 30자 이내로 짧고 강렬하게
2. MZ세대 감성 표현 사용 ("갓생 루틴", "몰입 부스트", "도파민 해킹", "에너지 충전", "멘탈 리셋" 등)
3. 실행 가능한 행동이 연상되는 표현 사용
4. 아래 카테고리에서 골고루 뽑되, 개인 데이터에 맞게 강약 조절:
   - [시기전략] 현재 대운·세운에서 지금 집중할 방향 (1~2개)
   - [집중법] 기질에 맞는 몰입·업무 전략 (1~2개)
   - [감정관리] 스트레스 포인트 + 회복 전략 (1~2개)
   - [습관설계] 용신 보충 + 뇌과학 기반 일상 습관 (2~3개)
   - [에너지] 수면·운동·영양 등 에너지 관리 (1~2개)
   - [관계전략] 소통·관계에서의 성장 포인트 (1개)
   - [종합] 핵심 실행 메시지 한 마디 (1개, 반드시 마지막)
5. 각 줄 앞에 어울리는 이모지 하나씩 붙이기
6. 각 줄 끝에 해당 카테고리를 태그로 붙이기

[미니 해석 규칙]
- 각 소제목 바로 다음 줄에 "> " 접두사로 80~120자 미니 해석을 추가
- 사주 데이터 + 뇌과학 진단에 근거한 핵심 포인트 1가지
- "왜 이 전략이 맞는지" + "바로 실행할 수 있는 한 줄 팁" 포함
- 2인칭 현재형, 존댓말 사용

[출력 형식]
반드시 아래 형식으로만 출력하세요. 설명이나 부연 없이 리스트만:
⚡ 지금은 확장보다 내실, 실력을 갈아넣을 타이밍! #시기전략
> 현재 대운이 인성 흐름이라 배움과 역량 강화에 최적이에요. 무리한 확장보다 한 가지 기술을 마스터하는 데 집중하면 다음 대운에서 폭발해요.
🎯 25분 스프린트가 당신의 몰입 치트키! #집중법
> 화(火) 기질에 집중력 점수가 양호한 편이라, 짧고 강렬한 스프린트가 딱 맞아요. 포모도로 25분 집중 → 5분 완전 휴식 → 반복하면 생산성이 2배 올라요.
💭 감정이 요동칠 때, '편도체 브레이크' 걸기 #감정관리
> 기신 오행이 자극받는 시기에 감정이 먼저 반응해요. 감정 폭발 직전 "6초 호흡법"으로 편도체 반응을 멈추세요. 그 6초가 판단을 바꿔요.
🌅 매일 아침 10분 산책이 용신을 충전하는 루틴 #습관설계
> 목(木) 용신이라 자연과 움직임에서 에너지를 받아요. 아침 산책 10분이면 충분해요. 뇌도 깨어나고 하루 컨디션이 달라져요.
🚀 올해는 하나만 밖으로 꺼내세요, 그게 전부입니다! #종합
> 강한 잠재력을 안으로만 품고 있어요. 올해 안에 하나만 세상에 보여주세요. 작게 시작해도 그 행동이 다음 10년의 궤도를 바꿔요.""",

    # ── 자기계발 개별 소제목 상세 해석 (2단계: 클릭 시 호출) ──
    "growth_detail": """위 사주 데이터와 뇌과학 진단 결과를 기반으로, 아래 소제목에 대한 구체적인 자기계발 전략과 실천 가이드를 작성해주세요.

소제목: "{title}"

[작성 규칙]
- 600~1,000자 분량으로 충실하게 서술
- 2인칭 현재형, 존댓말 ("당신에게 맞는 방식은 ~예요")
- 사주 기질 분석 + 뇌과학 진단 결과를 결합한 근거 제시
- 추상적 조언 금지 — 반드시 구체적 행동, 시간, 빈도, 방법까지 제시
  예: "주 3회 아침 7시 → 20분 걷기 → 귀가 후 5분 저널링"
- 습관 제안 시 "📋 실천 포인트" 형태로 실행 가능한 항목 2~3개 리스트
  예:
  📋 실천 포인트
  - 매일 아침 7시 기상 → 10분 스트레칭
  - 주 3회 30분 유산소 운동 (화·목·토)
  - 취침 1시간 전 스마트폰 OFF
- 금지어: "운명입니다", "타고났습니다", "무조건", "반드시"
  → 대신: "~하면 효과적이에요", "~해보시는 걸 권해요", "~한 경향이 있으니 활용하세요"
- HTML 태그 절대 금지. 순수 텍스트와 마크다운(**굵은 글씨**)만 사용
- 소제목(##)은 쓰지 마세요. 바로 본문부터 시작하세요.""",

    # ── 뇌과학 소제목 + 미니 해석 (1단계: saju_titles와 동일 패턴) ──
    "brain_titles": """당신은 신경과학·인지심리학 전문가이면서 MZ세대 감성을 이해하는 콘텐츠 크리에이터입니다.

핵심 전제: 뇌의 신경가소성(Neuroplasticity)에 의해 뇌는 평생 변화합니다.
지금의 진단 결과는 '고정된 한계'가 아니라 '현재의 출발점'입니다.
생활 패턴, 사고 습관, 훈련에 따라 누구나 원하는 방향으로 뇌를 재설계할 수 있습니다.

위 뇌과학 자가진단 결과를 보고, 이 사람의 인지·행동 패턴 핵심 특징을 8~12개의 "소제목 + 미니 해석"으로 만들어주세요.

[톤 & 어조]
- 확신과 자신감에 찬 어조: "당신의 뇌는 이미 강력한 잠재력을 갖고 있어요"
- 신경가소성 원리에 기반한 희망적 메시지: "지금부터 바꿀 수 있어요"
- 과학적 근거를 바탕으로 하되, 쉽고 친근하게 전달
- 약점도 "아직 개발되지 않은 잠재력"으로 프레이밍

[소제목 규칙]
1. 각 소제목은 30자 이내로 짧고 강렬하게
2. MZ세대 감성의 트렌디한 표현 사용 ("뇌 부스트", "멘탈 갓생", "집중력 버프", "도파민 해킹", "슬립 마스터" 등)
3. 뇌과학·심리학 용어를 재치있게 녹여내기 ("전두엽 풀가동", "해마 레벨업", "편도체 진정 모드")
4. 강점은 폭발적으로 칭찬, 약점은 "성장 가능성"으로 반전
5. 아래 카테고리에서 골고루 뽑되, 진단 결과에 맞게 강약 조절:
   - [수면] 수면 패턴과 회복력 (1~2개)
   - [집중력] 집중력·몰입 패턴 (1~2개)
   - [운동] 운동·신체 활력 (1개)
   - [감정] 스트레스·감정 조절·마음챙김 (1~2개)
   - [학습] 학습 유형·기억력 (1개)
   - [동기] 동기부여·자기조절 (1~2개)
   - [종합] 이 뇌의 핵심 가능성을 한 문장으로 (1개, 반드시 마지막)
6. 각 줄 앞에 어울리는 이모지 하나씩 붙이기
7. 각 줄 끝에 해당 카테고리를 태그로 붙이기

[미니 해석 규칙]
- 각 소제목 바로 다음 줄에 "> " 접두사로 80~120자 미니 해석을 추가
- 진단 데이터에 근거한 핵심 포인트 1가지를 짧고 날카롭게
- 신경가소성 원리에 기반한 "변화 가능성"을 포함
- 2인칭 현재형, 존댓말 사용

[출력 형식]
반드시 아래 형식으로만 출력하세요. 설명이나 부연 없이 리스트만:
💤 수면 패턴 리셋! 당신의 뇌는 '슬립 마스터' 잠재력을 갖고 있다 #수면
> 현재 수면 점수가 높지 않지만, 이건 습관의 문제예요. 뇌의 송과체는 환경 신호에 민감하게 반응해요. 취침 루틴 하나만 바꿔도 수면의 질이 확 달라질 수 있어요.
🎯 집중력 버프 ON! 전두엽이 이미 준비 완료된 상태 #집중력
> 집중력 점수가 양호해요. 전전두피질이 잘 작동하고 있다는 신호예요. 포모도로 기법을 적용하면 이 강점이 두 배로 폭발할 수 있어요.
🧠 당신의 뇌는 아직 30%만 쓰고 있다, 나머지 70%를 깨울 시간! #종합
> 진단 결과를 종합하면, 강점 영역의 신경회로는 이미 탄탄해요. 약점 영역도 뇌의 신경가소성 덕분에 3주만 꾸준히 훈련하면 체감할 수 있는 변화가 시작돼요.""",

    # ── 뇌과학 개별 소제목 상세 해석 (2단계: 클릭 시 호출) ──
    "brain_detail": """위 뇌과학 자가진단 데이터를 기반으로, 아래 소제목에 대한 상세 해석을 작성해주세요.

소제목: "{title}"

[핵심 전제]
뇌의 신경가소성(Neuroplasticity) 원리에 따라, 현재 상태는 고정된 것이 아닙니다.
반복적인 생활 패턴과 의식적인 훈련을 통해 뇌의 신경회로를 재구성할 수 있습니다.
이 분석은 "현재 위치 파악 + 구체적 개선 로드맵"을 제공하는 것이 목적입니다.

[작성 규칙]
- 600~1,000자 분량으로 충실하게 서술
- 2인칭 현재형, 존댓말 ("당신의 뇌는 ~하는 패턴을 보이고 있어요")
- 확신과 자신감에 찬 어조: "충분히 바꿀 수 있어요", "이미 잠재력이 있어요"
- 뇌과학 용어는 쉽게 풀어서 설명 (예: "전전두피질(집중과 판단을 담당하는 뇌 영역)")
- 진단 점수를 바탕으로 현재 상태를 구체적으로 분석
- 약점은 "아직 활성화되지 않은 신경회로"로 프레이밍
- 구체적 실천 방법 2~3개로 마무리 ("~해보시면 3주 안에 변화를 느낄 수 있어요")
- 금지어: "한계", "불가능", "타고난 약점", "고칠 수 없는"
  → 대신: "아직 개발되지 않은", "훈련으로 강화할 수 있는", "잠재력이 숨어있는"
- HTML 태그 절대 금지. 순수 텍스트와 마크다운(**굵은 글씨**)만 사용
- 소제목(##)은 쓰지 마세요. 바로 본문부터 시작하세요.""",
}


# ──────────────────────────────────────────────────────────
# 뇌과학 진단 전용 시스템 프롬프트 + 컨텍스트 빌더
# ──────────────────────────────────────────────────────────

SYSTEM_PROMPT_BRAIN = """당신은 신경과학(Neuroscience)과 인지심리학 전문가입니다.
사용자의 뇌과학 자가진단 결과를 분석하여,
개인 맞춤형 인지·행동 개선 전략을 자신감 있고 따뜻하게 제안합니다.

[핵심 철학 — 신경가소성(Neuroplasticity)]
뇌는 평생 변화합니다. 현재의 진단 결과는 "한계"가 아니라 "출발점"입니다.
반복적인 생활 패턴, 사고 습관, 의식적인 훈련을 통해
누구나 자신의 뇌를 원하는 방향으로 재설계할 수 있습니다.
이 확신을 바탕으로 모든 분석과 조언을 전달하세요.

[역할 원칙]
1. 의학적 진단이 아닌 "뇌과학 기반 자기이해와 성장 전략"을 제공합니다.
2. 모든 서술은 2인칭 현재형("당신의 뇌는 ~하는 패턴을 보이고 있어요")으로 작성합니다.
3. 강점은 폭발적으로 칭찬하고, 약점은 "아직 활성화되지 않은 잠재력"으로 프레이밍합니다.
4. 추상적 표현 금지. 구체적 뇌과학 메커니즘 + 실천 행동으로 묘사합니다.
5. 뇌과학 용어는 반드시 괄호 안에 쉬운 말로 풀어줍니다.

[절대 규칙]
- HTML 태그 금지. 순수 텍스트와 마크다운(**굵은 글씨**)만 사용합니다.
- 금지어: "한계입니다", "고칠 수 없습니다", "타고난 약점", "무조건", "반드시"
  → 대신: "아직 개발 중인", "훈련으로 강화할 수 있는", "~해보시면 변화를 느낄 수 있어요"
- 한국어로만 답변합니다."""

SYSTEM_PROMPT_BRAIN_DETAIL = """당신은 신경과학(Neuroscience)과 인지심리학 전문가입니다.
제공된 뇌과학 자가진단 데이터를 바탕으로, 특정 주제에 대한 상세 분석을 작성합니다.

[핵심 전제: 신경가소성]
뇌는 평생 변화합니다. 약점은 "한계"가 아니라 "아직 활성화되지 않은 신경회로"입니다.
이 확신을 바탕으로, 현재 상태 분석 + 구체적 개선 방법을 제시하세요.

[규칙]
- 2인칭 현재형, 존댓말 ("당신의 뇌는 ~하고 있어요")
- 뇌과학 용어 후 괄호로 쉬운 설명
- 강점은 칭찬 + 약점은 성장 가능성으로 전환
- 구체적 실천 조언 2~3개로 마무리
- 600~1,000자 분량
- 금지어: "한계", "고칠 수 없는", "타고난 약점"
- HTML 태그 금지, 순수 텍스트와 마크다운(**굵은 글씨**)만 사용
- 한국어로만 답변"""


SYSTEM_PROMPT_GROWTH = """당신은 20년 경력의 명리학자이자 뇌과학·행동과학 기반 자기계발 전문 코치입니다.
사주의 기질 데이터와 뇌과학 자가진단 결과를 결합하여,
개인 맞춤형 성장 전략과 실천 루틴을 설계합니다.

[역할 원칙]
1. 점술적 예언이 아닌 "행동 전략과 실행 가능한 루틴"을 제공합니다.
2. 사주의 오행·용신 데이터는 "기질 경향"으로, 뇌과학 진단은 "현재 습관 상태"로 해석합니다.
3. 모든 서술은 2인칭 현재형, 확신 있고 따뜻한 코치 어조로 작성합니다.
4. 추상적 조언 금지. 구체적 행동, 시간, 빈도, 방법까지 제시합니다.
5. 막연한 "좋은 시기입니다"가 아닌 "지금 ~을 하면 효과적이에요"로 표현합니다.

[절대 규칙]
- HTML 태그 금지. 순수 텍스트와 마크다운(**굵은 글씨**)만 사용합니다.
- 금지어: "운명입니다", "타고났습니다", "무조건", "반드시"
- 한국어로만 답변합니다."""

SYSTEM_PROMPT_GROWTH_DETAIL = """당신은 사주명리학자이자 뇌과학·행동과학 기반 자기계발 전문 코치입니다.
제공된 데이터를 바탕으로, 특정 주제에 대한 구체적인 실천 전략을 작성합니다.

[규칙]
- 2인칭 현재형, 코치 어조 ("당신에게 맞는 방식은 ~예요")
- 사주 기질 + 뇌과학 진단 결합 근거 제시
- 구체적 행동·시간·빈도·방법 포함 필수
- 실천 포인트 2~3개로 마무리
- 600~1,000자 분량
- 금지어: "운명입니다", "타고났습니다", "무조건", "반드시"
- HTML 태그 금지, 순수 텍스트와 마크다운(**굵은 글씨**)만 사용
- 한국어로만 답변"""


def build_growth_context(raw_data: dict, *, name: str = "", gender: str = "", birth_year: int = 0) -> str:
    """자기계발용 컨텍스트: 사주 데이터 + 뇌과학 진단 결합."""
    lines = []

    # 사주 데이터 (build_context의 핵심만 추출)
    saju_context = build_context(raw_data, name=name, gender=gender, birth_year=birth_year)
    lines.append("═══ 사주 기질 데이터 ═══")
    lines.append(saju_context)

    # 뇌과학 진단 데이터
    brain = raw_data.get("brain_analysis", {})
    if brain:
        lines.append("\n═══ 뇌과학 자가진단 결과 ═══")
        lines.append(f"종합 상태: {brain.get('overallLevel', '미확인')}")
        strong = brain.get("strongAreas", [])
        weak = brain.get("weakAreas", [])
        if strong:
            lines.append(f"강점 영역: {', '.join(strong)}")
        if weak:
            lines.append(f"개선 가능 영역: {', '.join(weak)}")
        areas = brain.get("areas", [])
        for a in areas:
            area_name = a.get("area", "")
            if a.get("avgScore") is not None:
                lines.append(f"  {area_name}: {a.get('levelLabel', '')} ({a.get('pct', 0)}%)")
            types = a.get("types", [])
            if types:
                lines.append(f"  {area_name} 유형: {', '.join(types)}")
    else:
        # brain_summary 텍스트 폴백
        brain_summary = raw_data.get("brain_summary", "")
        if brain_summary:
            lines.append(f"\n═══ 뇌과학 자가진단 요약 ═══\n{brain_summary}")

    return "\n".join(lines)


def build_growth_context_lite(raw_data: dict, *, title: str = "", tag: str = "",
                               name: str = "", gender: str = "", birth_year: int = 0) -> str:
    """growth_detail 전용 경량 컨텍스트. 태그 관련 데이터 우선 포함."""
    tag_lower = tag.replace("#", "").strip().lower() if tag else ""

    lines = []

    # 사주 핵심만 (build_context_lite 활용)
    saju_lite = build_context_lite(raw_data, title=title, tag=tag, name=name, gender=gender, birth_year=birth_year)
    lines.append("사주 기질:")
    lines.append(saju_lite)

    # 뇌과학 핵심만
    brain = raw_data.get("brain_analysis", {})
    if brain:
        lines.append("\n뇌과학 진단:")
        lines.append(f"종합: {brain.get('overallLevel', '미확인')}")
        strong = brain.get("strongAreas", [])
        weak = brain.get("weakAreas", [])
        if strong:
            lines.append(f"강점: {', '.join(strong)}")
        if weak:
            lines.append(f"개선: {', '.join(weak)}")

        # 태그 기반 뇌과학 영역 우선 주입
        tag_brain_map = {
            "시기전략": [], "집중법": ["집중력"], "감정관리": ["스트레스", "자기조절", "마음챙김"],
            "습관설계": ["수면", "운동", "동기부여"], "에너지": ["수면", "운동"],
            "관계전략": ["스트레스", "자기조절"], "종합": [],
        }
        priority = tag_brain_map.get(tag_lower, [])
        areas = brain.get("areas", [])
        for a in areas:
            area_name = a.get("area", "")
            if area_name in priority or not priority:
                if a.get("avgScore") is not None:
                    lines.append(f"  {area_name}: {a.get('levelLabel', '')} ({a.get('pct', 0)}%)")
    else:
        brain_summary = raw_data.get("brain_summary", "")
        if brain_summary:
            lines.append(f"\n뇌과학 요약: {brain_summary[:200]}")

    return "\n".join(lines)


def build_brain_context(raw_data: dict) -> str:
    """뇌과학 진단 결과를 프롬프트용 텍스트로 변환.

    사주 데이터는 포함하지 않음 — 뇌과학 진단 결과만 순수하게 분석.
    """
    brain = raw_data.get("brain_analysis", {})

    lines = []
    lines.append("═══ 뇌과학 자가진단 결과 ═══")
    lines.append(f"종합 상태: {brain.get('overallLevel', '미확인')}")

    strong = brain.get("strongAreas", [])
    weak = brain.get("weakAreas", [])
    if strong:
        lines.append(f"강점 영역: {', '.join(strong)}")
    if weak:
        lines.append(f"개선 가능 영역: {', '.join(weak)}")

    areas = brain.get("areas", [])
    for a in areas:
        area_name = a.get("area", "")
        if a.get("avgScore") is not None:
            lines.append(
                f"  {area_name}: {a.get('levelLabel', '')} "
                f"(점수 {a['avgScore']:.1f}/3, 양호도 {a.get('pct', 0)}%)"
            )
            if a.get("advice"):
                lines.append(f"    → {a['advice']}")
        types = a.get("types", [])
        if types:
            lines.append(f"  {area_name} 유형: {', '.join(types)}")

    type_info = brain.get("typeInfo", {})
    if type_info:
        lines.append("\n인지 유형:")
        for area, types in type_info.items():
            lines.append(f"  {area}: {', '.join(types)}")

    return "\n".join(lines)


def build_brain_context_lite(raw_data: dict, *, title: str = "", tag: str = "") -> str:
    """brain_detail 전용 경량 컨텍스트. 태그 관련 영역 우선 포함."""
    brain = raw_data.get("brain_analysis", {})
    areas = brain.get("areas", [])
    tag_lower = tag.replace("#", "").strip() if tag else ""

    lines = []
    lines.append("뇌과학 자가진단 결과:")
    lines.append(f"종합: {brain.get('overallLevel', '미확인')}")

    strong = brain.get("strongAreas", [])
    weak = brain.get("weakAreas", [])
    if strong:
        lines.append(f"강점: {', '.join(strong)}")
    if weak:
        lines.append(f"개선 가능: {', '.join(weak)}")

    tag_area_map = {
        "수면": ["수면"], "집중력": ["집중력"], "운동": ["운동"],
        "감정": ["스트레스", "자기조절", "마음챙김"], "학습": ["학습"],
        "동기": ["동기부여", "자기조절"], "종합": [],
    }
    priority_areas = tag_area_map.get(tag_lower, [])

    for a in areas:
        area_name = a.get("area", "")
        if area_name in priority_areas or not priority_areas:
            if a.get("avgScore") is not None:
                lines.append(f"  {area_name}: {a.get('levelLabel', '')} ({a.get('pct', 0)}%)")
                if a.get("advice") and area_name in priority_areas:
                    lines.append(f"    → {a['advice']}")
            types = a.get("types", [])
            if types:
                lines.append(f"  {area_name} 유형: {', '.join(types)}")

    return "\n".join(lines)
