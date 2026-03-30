"""사주 계산 오케스트레이터 — DB 의존성 없이 순수 계산만 수행.

입력: 생년월일시, 성별, 캘린더타입
출력: raw_calculation_json (dict)
"""

from datetime import datetime

from app.services.saju_engine.normalizer import normalize_birth_datetime
from app.services.saju_engine.timezone_adjuster import apply_timezone_rules
from app.services.saju_engine.pillar_calculator import PillarCalculator
from app.services.saju_engine.hidden_stem_calculator import HiddenStemCalculator
from app.services.saju_engine.ten_god_calculator import TenGodCalculator
from app.services.saju_engine.twelve_stage_calculator import TwelveStageCalculator
from app.services.saju_engine.relation_calculator import RelationCalculator
from app.services.saju_engine.daewoon_calculator import DaewoonCalculator
from app.services.saju_engine.gyeokguk_calculator import GyeokgukCalculator
from app.services.saju_engine.interpreter import Interpreter
from app.services.saju_engine.dto import DaewoonResult, FullSajuResult, SewoonResult
from app.services.saju_engine.ganzhi_math import get_branch_meta, get_stem_meta
from app.services.saju_engine.constants import STEM_INDEX, BRANCH_INDEX, STEMS, BRANCHES


def calculate_saju(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int | None = None,
    birth_minute: int | None = None,
    gender: str = "male",
    calendar_type: str = "solar",
) -> dict:
    """사주 전체 계산을 수행하고 raw_calculation_json을 반환.

    이 함수는 DB에 의존하지 않는 순수 계산 함수다.
    Claude에게 계산을 맡기지 않는다.
    """
    # 1. 시간 정규화
    normalized = normalize_birth_datetime(
        birth_year=birth_year,
        birth_month=birth_month,
        birth_day=birth_day,
        birth_hour=birth_hour,
        birth_minute=birth_minute,
    )

    # 2. 시간대 보정 (KST 변천 + DST)
    normalized = apply_timezone_rules(
        normalized,
        use_dst_adjustment=True,
        use_historical_kst_adjust=True,
        use_true_solar_time=False,
    )

    calc_dt = normalized.adjusted_datetime or normalized.local_datetime
    hour_unknown = normalized.hour_unknown

    # 3. 4주 산출 (시간 미입력 시 시주 생략)
    pillar_calc = PillarCalculator()
    year_pillar = pillar_calc.calculate_year_pillar(calc_dt)
    month_pillar = pillar_calc.calculate_month_pillar(calc_dt, year_pillar.stem_code)
    day_pillar = pillar_calc.calculate_day_pillar(calc_dt)
    if hour_unknown:
        pillars = [year_pillar, month_pillar, day_pillar]
    else:
        hour_pillar = pillar_calc.calculate_hour_pillar(calc_dt, day_pillar.stem_code)
        pillars = [year_pillar, month_pillar, day_pillar, hour_pillar]

    # 4. 지장간
    hs_calc = HiddenStemCalculator()
    hidden_stems = hs_calc.calculate_for_pillars(pillars)

    # 5. 십성
    tg_calc = TenGodCalculator()
    ten_gods = tg_calc.calculate_all(pillars, hidden_stems)

    # 6. 십이운성
    ts_calc = TwelveStageCalculator()
    twelve_stages = ts_calc.calculate_all(pillars)

    # 7. 합충형해파
    rel_calc = RelationCalculator()
    relations = rel_calc.calculate(pillars)

    # 8. 오행 분포 (8자 정수 카운트 + 지장간 가중치 버전)
    five_elements = _summarize_five_elements(pillars, hidden_stems)
    five_elements_weighted = _summarize_five_elements_weighted(pillars, hidden_stems)

    # 9. 대운
    daewoon_calc = DaewoonCalculator()
    daewoon = daewoon_calc.calculate(
        gender_for_daewoon=gender,
        year_stem_code=year_pillar.stem_code,
        month_pillar=month_pillar,
        birth_datetime=calc_dt,
        birth_year=birth_year,
    )

    # 9-1. 대운에 십성/십이운성 부착
    day_master = day_pillar.stem_code
    _attach_ten_god_and_stage_to_daewoon(daewoon, day_master, tg_calc, ts_calc, hs_calc)

    # 9-2. 세운 계산 (올해 기준 ±5년, 총 10년)
    current_year = datetime.now().year
    sewoon = _calculate_sewoon(
        birth_year=birth_year,
        day_master=day_master,
        start_year=current_year - 3,
        end_year=current_year + 7,
        tg_calc=tg_calc,
        ts_calc=ts_calc,
        hs_calc=hs_calc,
    )

    # 10. 격국/용신
    full_result = FullSajuResult(
        pillars=pillars,
        hidden_stems=hidden_stems,
        ten_gods=ten_gods,
        twelve_stages=twelve_stages,
        relations=relations,
        five_elements=five_elements,
        daewoon=daewoon,
    )
    gk_calc = GyeokgukCalculator()
    gyeokguk = gk_calc.calculate(full_result)
    full_result.gyeokguk = gyeokguk

    # 11. 템플릿 해석
    interpreter = Interpreter()
    interpretation = interpreter.interpret(full_result)

    # 응답 구성
    return {
        "normalized_datetime": calc_dt.isoformat(sep=" "),
        "pillars": {
            p.pillar_type: {
                "stem_code": p.stem_code,
                "branch_code": p.branch_code,
                "stem_kr": p.stem_kr,
                "branch_kr": p.branch_kr,
                "stem_hanja": p.stem_hanja,
                "branch_hanja": p.branch_hanja,
                "stem_element": p.stem_element,
                "branch_element": p.branch_element,
                "stem_yinyang": getattr(p, "stem_yinyang", ""),
                "branch_yinyang": getattr(p, "branch_yinyang", ""),
            }
            for p in pillars
        },
        "hidden_stems": {
            hs.pillar_type: [
                {"code": h.hidden_stem_code, "kr": h.hidden_stem_kr, "weight": h.relative_weight}
                for h in hidden_stems if h.pillar_type == hs.pillar_type
            ]
            for hs in hidden_stems
        },
        "five_elements": five_elements,
        "five_elements_weighted": five_elements_weighted,
        "ten_gods": [
            {
                "source_pillar": tg.source_pillar_type,
                "source_position": tg.source_position_type,
                "source_code": tg.source_code,
                "ten_god_code": tg.ten_god_code,
                "ten_god_kr": tg.ten_god_kr,
            }
            for tg in ten_gods
        ],
        "twelve_stages": [
            {
                "pillar_type": ts.target_pillar_type,
                "branch_code": ts.target_branch_code,
                "stage_code": ts.stage_code,
                "stage_kr": ts.stage_kr,
            }
            for ts in twelve_stages
        ],
        "relations": [
            {
                "category": r.relation_category,
                "subtype": r.relation_subtype,
                "left": r.left_code,
                "right": r.right_code,
                "note": r.note,
            }
            for r in relations
        ],
        "daewoon": [
            {
                "index": d.cycle_index,
                "start_age": d.start_age,
                "end_age": d.end_age,
                "start_year": d.start_year,
                "end_year": d.end_year,
                "stem_code": d.stem_code,
                "branch_code": d.branch_code,
                "stem_kr": d.stem_kr,
                "branch_kr": d.branch_kr,
                "stem_hanja": d.stem_hanja,
                "branch_hanja": d.branch_hanja,
                "direction": d.direction,
                "stem_ten_god_kr": d.stem_ten_god_kr,
                "stem_ten_god_code": d.stem_ten_god_code,
                "branch_ten_god_kr": d.branch_ten_god_kr,
                "branch_ten_god_code": d.branch_ten_god_code,
                "twelve_stage_kr": d.twelve_stage_kr,
                "twelve_stage_code": d.twelve_stage_code,
            }
            for d in daewoon
        ],
        "sewoon": [
            {
                "year": s.year,
                "stem_code": s.stem_code,
                "branch_code": s.branch_code,
                "stem_kr": s.stem_kr,
                "branch_kr": s.branch_kr,
                "stem_hanja": s.stem_hanja,
                "branch_hanja": s.branch_hanja,
                "stem_ten_god_kr": s.stem_ten_god_kr,
                "stem_ten_god_code": s.stem_ten_god_code,
                "branch_ten_god_kr": s.branch_ten_god_kr,
                "branch_ten_god_code": s.branch_ten_god_code,
                "twelve_stage_kr": s.twelve_stage_kr,
                "twelve_stage_code": s.twelve_stage_code,
            }
            for s in sewoon
        ],
        "gyeokguk": {
            "name": gyeokguk.gyeokguk_name,
            "type": gyeokguk.gyeokguk_type,
            "strength": gyeokguk.strength,
            "strength_score": gyeokguk.strength_score,
            "yongshin_element": gyeokguk.yongshin_element,
            "gishin_element": gyeokguk.gishin_element,
            "yongshin_reason": gyeokguk.yongshin_reason,
            "details": gyeokguk.details,
        } if gyeokguk else None,
        "interpretation": interpretation,
    }


def _attach_ten_god_and_stage_to_daewoon(
    daewoon: list[DaewoonResult],
    day_master: str,
    tg_calc: TenGodCalculator,
    ts_calc: TwelveStageCalculator,
    hs_calc: HiddenStemCalculator,
) -> None:
    """대운 각 간지에 대해 일간 기준 십성·십이운성을 계산하여 부착."""
    for dw in daewoon:
        # 천간 십성
        stem_tg = tg_calc._compute(day_master, dw.stem_code)
        dw.stem_ten_god_code = stem_tg[0]
        dw.stem_ten_god_kr = stem_tg[1]

        # 지지 본기(正氣) 십성
        jeonggi = hs_calc.get_jeonggi(dw.branch_code)
        if jeonggi:
            branch_tg = tg_calc._compute(day_master, jeonggi)
            dw.branch_ten_god_code = branch_tg[0]
            dw.branch_ten_god_kr = branch_tg[1]

        # 십이운성
        stage_code, stage_kr, _ = ts_calc.calculate(day_master, dw.branch_code)
        dw.twelve_stage_code = stage_code
        dw.twelve_stage_kr = stage_kr


def _calculate_sewoon(
    *,
    birth_year: int,
    day_master: str,
    start_year: int,
    end_year: int,
    tg_calc: TenGodCalculator,
    ts_calc: TwelveStageCalculator,
    hs_calc: HiddenStemCalculator,
) -> list[SewoonResult]:
    """세운(歲運) 계산 — 지정된 년도 범위의 연간지 + 십성 + 십이운성.

    세운 간지 계산법:
    - 1984년 = 갑자년(甲子年), 60갑자 index 0
    - 임의 연도의 간지 = (연도 - 4) % 60
    """
    results = []
    for year in range(start_year, end_year + 1):
        ganzhi_idx = (year - 4) % 60
        stem_idx = ganzhi_idx % 10
        branch_idx = ganzhi_idx % 12

        stem_code = STEMS[stem_idx][0]
        branch_code = BRANCHES[branch_idx][0]

        s_meta = get_stem_meta(stem_code)
        b_meta = get_branch_meta(branch_code)

        # 천간 십성
        stem_tg = tg_calc._compute(day_master, stem_code)
        # 지지 본기 십성
        jeonggi = hs_calc.get_jeonggi(branch_code)
        branch_tg = tg_calc._compute(day_master, jeonggi) if jeonggi else ("", "", "")
        # 십이운성
        stage_code, stage_kr, _ = ts_calc.calculate(day_master, branch_code)

        results.append(SewoonResult(
            year=year,
            stem_code=stem_code,
            branch_code=branch_code,
            stem_kr=s_meta["stem_kr"],
            branch_kr=b_meta["branch_kr"],
            stem_hanja=s_meta["stem_hanja"],
            branch_hanja=b_meta["branch_hanja"],
            stem_ten_god_kr=stem_tg[1],
            stem_ten_god_code=stem_tg[0],
            branch_ten_god_kr=branch_tg[1] if branch_tg else "",
            branch_ten_god_code=branch_tg[0] if branch_tg else "",
            twelve_stage_kr=stage_kr,
            twelve_stage_code=stage_code,
        ))

    return results


def _summarize_five_elements(pillars, hidden_stems) -> dict:
    """오행 분포 계산 — 8자(천간4 + 지지4) 정수 카운트.

    전통 만세력 방식: 천간의 오행 + 지지의 오행을 각각 1로 카운트.
    지장간 가중치는 별도 필드(five_elements_weighted)로 제공.
    """
    result = {"wood": 0, "fire": 0, "earth": 0, "metal": 0, "water": 0}
    for p in pillars:
        result[p.stem_element] += 1
        result[p.branch_element] += 1
    return result


def _summarize_five_elements_weighted(pillars, hidden_stems) -> dict:
    """오행 분포 계산 — 천간 + 지장간 가중치 (상세 분석용)."""
    result = {"wood": 0.0, "fire": 0.0, "earth": 0.0, "metal": 0.0, "water": 0.0}
    for p in pillars:
        result[p.stem_element] += 1.0

    for hs in hidden_stems:
        meta = get_stem_meta(hs.hidden_stem_code)
        weight = hs.relative_weight if hs.relative_weight else 0.5
        result[meta["stem_element"]] += weight

    return result
