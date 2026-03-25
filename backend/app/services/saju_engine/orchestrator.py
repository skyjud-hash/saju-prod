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
from app.services.saju_engine.dto import FullSajuResult
from app.services.saju_engine.ganzhi_math import get_stem_meta


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

    # 3. 4주 산출
    pillar_calc = PillarCalculator()
    year_pillar = pillar_calc.calculate_year_pillar(calc_dt)
    month_pillar = pillar_calc.calculate_month_pillar(calc_dt, year_pillar.stem_code)
    day_pillar = pillar_calc.calculate_day_pillar(calc_dt)
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

    # 8. 오행 분포
    five_elements = _summarize_five_elements(pillars, hidden_stems)

    # 9. 대운
    daewoon_calc = DaewoonCalculator()
    daewoon = daewoon_calc.calculate(
        gender_for_daewoon=gender,
        year_stem_code=year_pillar.stem_code,
        month_pillar=month_pillar,
        birth_datetime=calc_dt,
        birth_year=birth_year,
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
                "direction": d.direction,
            }
            for d in daewoon
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


def _summarize_five_elements(pillars, hidden_stems) -> dict:
    """오행 분포 계산 — 천간 + 지장간 가중치."""
    result = {"wood": 0.0, "fire": 0.0, "earth": 0.0, "metal": 0.0, "water": 0.0}
    for p in pillars:
        result[p.stem_element] += 1.0

    for hs in hidden_stems:
        meta = get_stem_meta(hs.hidden_stem_code)
        weight = hs.relative_weight if hs.relative_weight else 0.5
        result[meta["stem_element"]] += weight

    return result
