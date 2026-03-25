"""대운(大運) 계산기."""

from datetime import datetime

from app.services.saju_engine.dto import DaewoonResult, PillarResult
from app.services.saju_engine.ganzhi_math import add_branch, add_stem, get_branch_meta, get_stem_meta
from app.services.saju_engine.solar_term_finder import SolarTermFinder


class DaewoonCalculator:
    def __init__(self, solar_term_finder: SolarTermFinder | None = None):
        self.solar_term_finder = solar_term_finder or SolarTermFinder()

    def calculate(
        self, *,
        gender_for_daewoon: str | None,
        year_stem_code: str,
        month_pillar: PillarResult,
        birth_datetime: datetime,
        birth_year: int,
    ) -> list[DaewoonResult]:
        if gender_for_daewoon is None:
            return []

        year_meta = get_stem_meta(year_stem_code)

        # 순행/역행 결정
        if gender_for_daewoon == "male":
            forward = (year_meta["stem_yinyang"] == "yang")
        else:
            forward = (year_meta["stem_yinyang"] == "yin")

        # 대운 시작 나이 계산: 생일~가장 가까운 절기까지 일수 / 3
        try:
            if forward:
                nearest_jeol = self.solar_term_finder.find_next_jeol_after(birth_datetime)
            else:
                nearest_jeol = self.solar_term_finder.find_latest_jeol_before(birth_datetime)

            days_diff = abs((nearest_jeol.exact_datetime_kst - birth_datetime).days)
            start_age = round(days_diff / 3, 1)
        except Exception:
            start_age = 3.0  # 절기 데이터 없을 때 기본값

        if start_age < 1:
            start_age = 1.0

        # 대운 간지 배열 (10개)
        results = []
        for i in range(10):
            step = (i + 1) if forward else -(i + 1)
            dw_stem = add_stem(month_pillar.stem_code, step)
            dw_branch = add_branch(month_pillar.branch_code, step)

            s_meta = get_stem_meta(dw_stem)
            b_meta = get_branch_meta(dw_branch)

            s_age = start_age + (i * 10)
            e_age = s_age + 10

            s_year = birth_year + int(s_age)
            e_year = birth_year + int(e_age)

            results.append(DaewoonResult(
                cycle_index=i,
                start_age=s_age,
                end_age=e_age,
                start_year=s_year,
                end_year=e_year,
                stem_code=dw_stem,
                branch_code=dw_branch,
                stem_kr=s_meta["stem_kr"],
                branch_kr=b_meta["branch_kr"],
                direction="forward" if forward else "backward",
            ))

        return results
