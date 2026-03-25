"""4주(연주/월주/일주/시주) 정확 계산기."""

from datetime import date, datetime

from app.services.saju_engine.constants import (
    BRANCHES,
    DAY_STEM_GROUP_TO_FIRST_HOUR_STEM,
    HOUR_BRANCH_BY_HOUR,
    JEOL_NAME_TO_MONTH_BRANCH,
    MONTH_BRANCH_ORDER_FROM_IN,
    REFERENCE_DATE_DAY,
    REFERENCE_DATE_MONTH,
    REFERENCE_DATE_YEAR,
    REFERENCE_GANZHI_INDEX,
    STEMS,
    YEAR_STEM_GROUP_TO_FIRST_MONTH_STEM,
)
from app.services.saju_engine.dto import PillarResult
from app.services.saju_engine.ganzhi_math import add_stem, get_branch_meta, get_stem_meta, stem_group
from app.services.saju_engine.solar_term_finder import SolarTermFinder


class PillarCalculator:
    def __init__(self, solar_term_finder: SolarTermFinder | None = None):
        self.solar_term_finder = solar_term_finder or SolarTermFinder()

    def _make_pillar(self, pillar_type: str, pillar_order: int,
                     stem_code: str, branch_code: str) -> PillarResult:
        stem = get_stem_meta(stem_code)
        branch = get_branch_meta(branch_code)
        return PillarResult(
            pillar_type=pillar_type,
            pillar_order=pillar_order,
            **stem,
            **branch,
        )

    def calculate_year_pillar(self, dt: datetime) -> PillarResult:
        """입춘 기준 연주 계산. 입춘 이전이면 전년도 간지 사용."""
        ipchun = self.solar_term_finder.find_ipchun(dt.year)

        if dt < ipchun.exact_datetime_kst:
            base_year = dt.year - 1
        else:
            base_year = dt.year

        stem_code = STEMS[(base_year - 4) % 10][0]
        branch_code = BRANCHES[(base_year - 4) % 12][0]

        return self._make_pillar("year", 1, stem_code, branch_code)

    def calculate_month_pillar(self, dt: datetime, year_stem_code: str) -> PillarResult:
        """절입 시각 기준 월주 계산. 12절기(절)에 의해 월지 결정."""
        latest_jeol = self.solar_term_finder.find_latest_jeol_before(dt)
        month_branch_code = JEOL_NAME_TO_MONTH_BRANCH.get(latest_jeol.term_name_kr)

        if month_branch_code is None:
            # 절기 이름이 매핑에 없는 경우 (예: DB에 중기만 있는 경우) - 근사 계산
            approx_month_map = {
                1: "chuk", 2: "in", 3: "myo", 4: "jin", 5: "sa", 6: "o",
                7: "mi", 8: "sin_branch", 9: "yu", 10: "sul", 11: "hae", 12: "ja",
            }
            month_branch_code = approx_month_map[dt.month]

        group = stem_group(year_stem_code)
        first_month_stem = YEAR_STEM_GROUP_TO_FIRST_MONTH_STEM[group]
        offset = MONTH_BRANCH_ORDER_FROM_IN[month_branch_code]
        month_stem_code = add_stem(first_month_stem, offset)

        return self._make_pillar("month", 2, month_stem_code, month_branch_code)

    def calculate_day_pillar(self, dt: datetime) -> PillarResult:
        """60갑자 기준일 기반 정확한 일주 계산."""
        ref_date = date(REFERENCE_DATE_YEAR, REFERENCE_DATE_MONTH, REFERENCE_DATE_DAY)
        delta_days = (dt.date() - ref_date).days
        ganzhi_index = (REFERENCE_GANZHI_INDEX + delta_days) % 60

        stem_index = ganzhi_index % 10
        branch_index = ganzhi_index % 12

        stem_code = STEMS[stem_index][0]
        branch_code = BRANCHES[branch_index][0]

        return self._make_pillar("day", 3, stem_code, branch_code)

    def calculate_hour_pillar(self, dt: datetime, day_stem_code: str) -> PillarResult:
        """일상기시법 기반 시주 계산.

        시간 경계 규칙 (만세력 표준):
        - 홀수시 정각(01:00, 03:00, 05:00, 07:00 등)은 이전 시진에 포함
        - 예: 07:00 = 묘시(卯), 07:01 = 진시(辰)
        - 자시 경계: 23:00 = 해시(亥)의 끝이 아닌 자시(子)의 시작 (23:00은 자시)
        """
        hour_branch_code = self._get_hour_branch(dt.hour, dt.minute)

        # 일간 그룹으로 자시 시작 천간 결정
        group = stem_group(day_stem_code)
        first_hour_stem = DAY_STEM_GROUP_TO_FIRST_HOUR_STEM[group]

        # 지지 순서 (자=0, 축=1, 인=2, ...)
        branch_order_map = {
            "ja": 0, "chuk": 1, "in": 2, "myo": 3, "jin": 4, "sa": 5,
            "o": 6, "mi": 7, "sin_branch": 8, "yu": 9, "sul": 10, "hae": 11,
        }
        offset = branch_order_map[hour_branch_code]
        hour_stem_code = add_stem(first_hour_stem, offset)

        return self._make_pillar("hour", 4, hour_stem_code, hour_branch_code)

    @staticmethod
    def _get_hour_branch(hour: int, minute: int = 0) -> str:
        """시각 → 지지 변환. 홀수시 정각은 이전 시진에 포함.

        경계 규칙:
          23:00~01:00(미만) = 자시   ※ 23:00 정각부터 자시 시작
          01:00~03:00(미만) = 축시   ※ 01:00 정각은 자시가 아닌 축시? → 아님!
          만세력 표준: 홀수시 정각(01,03,05,07...)은 이전 시진

        즉:
          23:00 이상 ~ 01:01 미만 = 자시 (子)
          01:01 이상 ~ 03:01 미만 = 축시 (丑)
          ...
          05:01 이상 ~ 07:01 미만 = 묘시 (卯)  ← 07:00은 여기
          07:01 이상 ~ 09:01 미만 = 진시 (辰)
          ...

        정리: 홀수시 정각(minute=0)이면 이전 시진, 아니면 해당 시진
        """
        # 총 분으로 변환 (0~1439)
        total_min = hour * 60 + minute

        # 경계값 (시진 시작 시각, 분 단위) - 홀수시 정각은 이전 시진이므로 +1분
        boundaries = [
            (23 * 60, "ja"),        # 23:00~ = 자시
            (1 * 60 + 1, "chuk"),   # 01:01~ = 축시
            (3 * 60 + 1, "in"),     # 03:01~ = 인시
            (5 * 60 + 1, "myo"),    # 05:01~ = 묘시
            (7 * 60 + 1, "jin"),    # 07:01~ = 진시
            (9 * 60 + 1, "sa"),     # 09:01~ = 사시
            (11 * 60 + 1, "o"),     # 11:01~ = 오시
            (13 * 60 + 1, "mi"),    # 13:01~ = 미시
            (15 * 60 + 1, "sin_branch"),  # 15:01~ = 신시
            (17 * 60 + 1, "yu"),    # 17:01~ = 유시
            (19 * 60 + 1, "sul"),   # 19:01~ = 술시
            (21 * 60 + 1, "hae"),   # 21:01~ = 해시
        ]

        # 자시(23:00~) 특수 처리
        if total_min >= 23 * 60 or total_min <= 1 * 60:
            return "ja"

        # 나머지 시진
        result = "ja"
        for start_min, branch in boundaries[1:]:  # 축시부터
            if total_min >= start_min:
                result = branch
            else:
                break
        return result

    def calculate_all(self, dt: datetime) -> list[PillarResult]:
        year = self.calculate_year_pillar(dt)
        month = self.calculate_month_pillar(dt, year.stem_code)
        day = self.calculate_day_pillar(dt)
        hour = self.calculate_hour_pillar(dt, day.stem_code)
        return [year, month, day, hour]
