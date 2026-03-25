"""절기 조회 모듈. DB에 절기 데이터가 없으면 알고리즘 기반 근사 계산을 사용."""

from datetime import datetime

from app.services.saju_engine.constants import JEOL_NAME_TO_MONTH_BRANCH, SOLAR_TERM_NAMES
from app.services.saju_engine.exceptions import SolarTermNotFoundError

# 절기(절)만 필터링 - 홀수 term_order만 절기
JEOL_TERM_ORDERS = {1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23}

# 24절기 태양 황경 (도 단위), term_order 1~24
SOLAR_LONGITUDE_BY_ORDER = {
    1: 285,   # 소한
    2: 300,   # 대한
    3: 315,   # 입춘
    4: 330,   # 우수
    5: 345,   # 경칩
    6: 0,     # 춘분
    7: 15,    # 청명
    8: 30,    # 곡우
    9: 45,    # 입하
    10: 60,   # 소만
    11: 75,   # 망종
    12: 90,   # 하지
    13: 105,  # 소서
    14: 120,  # 대서
    15: 135,  # 입추
    16: 150,  # 처서
    17: 165,  # 백로
    18: 180,  # 추분
    19: 195,  # 한로
    20: 210,  # 상강
    21: 225,  # 입동
    22: 240,  # 소설
    23: 255,  # 대설
    24: 270,  # 동지
}

# 근사 절기 시각 계산 (DB 없이 사용 가능한 방식)
# 주의: 이것은 ±1일 오차가 있는 근사값. 정확한 계산은 pyswisseph 또는 DB 절기 데이터 필요.
_APPROX_JEOL_DATES = {
    # (month, day_approx) - 대략적인 양력 날짜
    "소한": (1, 5), "입춘": (2, 4), "경칩": (3, 6),
    "청명": (4, 5), "입하": (5, 6), "망종": (6, 6),
    "소서": (7, 7), "입추": (8, 7), "백로": (9, 8),
    "한로": (10, 8), "입동": (11, 7), "대설": (12, 7),
}


class SolarTermData:
    """절기 데이터를 나타내는 간단한 객체."""

    def __init__(self, *, solar_year: int, term_order: int,
                 term_name_kr: str, exact_datetime_kst: datetime):
        self.solar_year = solar_year
        self.term_order = term_order
        self.term_name_kr = term_name_kr
        self.exact_datetime_kst = exact_datetime_kst


class SolarTermFinder:
    """절기 조회기. DB 세션이 있으면 DB에서, 없으면 근사 계산으로 조회."""

    def __init__(self, db=None):
        self.db = db
        self._cache: dict[tuple[int, int], SolarTermData] = {}

    def _get_approx_jeol(self, year: int, jeol_name: str) -> SolarTermData:
        """근사 절기 시각 계산."""
        month, day = _APPROX_JEOL_DATES[jeol_name]
        term_order = None
        for order, name_kr, _, _ in SOLAR_TERM_NAMES:
            if name_kr == jeol_name:
                term_order = order
                break
        return SolarTermData(
            solar_year=year,
            term_order=term_order,
            term_name_kr=jeol_name,
            exact_datetime_kst=datetime(year, month, day, 0, 0),
        )

    def _get_from_db(self, year: int, term_order: int) -> SolarTermData | None:
        if self.db is None:
            return None
        from app.models.solar_term import SolarTerm
        from sqlalchemy import and_, select
        stmt = select(SolarTerm).where(
            and_(SolarTerm.solar_year == year, SolarTerm.term_order == term_order)
        )
        row = self.db.execute(stmt).scalar_one_or_none()
        if row:
            return SolarTermData(
                solar_year=row.solar_year,
                term_order=row.term_order,
                term_name_kr=row.term_name_kr,
                exact_datetime_kst=row.exact_datetime_kst,
            )
        return None

    def find_ipchun(self, year: int) -> SolarTermData:
        """해당 연도 입춘 조회."""
        db_result = self._get_from_db(year, 3)  # term_order 3 = 입춘
        if db_result:
            return db_result
        return self._get_approx_jeol(year, "입춘")

    def find_latest_jeol_before(self, dt: datetime) -> SolarTermData:
        """주어진 시각 직전의 절기(절만) 조회."""
        # 현재 연도와 전년도의 12절기를 모두 확인하여 가장 가까운 이전 절기를 찾음
        candidates = []
        for year in [dt.year - 1, dt.year, dt.year + 1]:
            for jeol_name in JEOL_NAME_TO_MONTH_BRANCH:
                term_data = self._get_approx_jeol(year, jeol_name)
                # DB에서 더 정확한 데이터 시도
                if term_data.term_order:
                    db_data = self._get_from_db(year, term_data.term_order)
                    if db_data:
                        term_data = db_data
                if term_data.exact_datetime_kst <= dt:
                    candidates.append(term_data)

        if not candidates:
            raise SolarTermNotFoundError(f"No jeol found before {dt}")

        candidates.sort(key=lambda x: x.exact_datetime_kst, reverse=True)
        return candidates[0]

    def find_next_jeol_after(self, dt: datetime) -> SolarTermData:
        """주어진 시각 직후의 절기(절만) 조회."""
        candidates = []
        for year in [dt.year - 1, dt.year, dt.year + 1]:
            for jeol_name in JEOL_NAME_TO_MONTH_BRANCH:
                term_data = self._get_approx_jeol(year, jeol_name)
                if term_data.term_order:
                    db_data = self._get_from_db(year, term_data.term_order)
                    if db_data:
                        term_data = db_data
                if term_data.exact_datetime_kst > dt:
                    candidates.append(term_data)

        if not candidates:
            raise SolarTermNotFoundError(f"No jeol found after {dt}")

        candidates.sort(key=lambda x: x.exact_datetime_kst)
        return candidates[0]
