"""격국(格局) 판정 및 용신(用神)·기신(忌神) 산출.

학술 근거:
- 나혁진(2020), 「明通賦를 통해 본 徐子平의 명리이론 연구」
  : 격국 판정은 월지 지장간 정기를 기준으로 하며,
    용신은 신강/신약 + 오행 균형을 종합 판단

- 김만태(2022): 용신은 확정론이 아니라 '가능성과 잠재성'의 추론

격국 판정 원리 (자평명리학 신법):
1. 월지의 정기(正氣)를 일간과 비교하여 십성을 구한다
2. 해당 십성이 격국의 이름이 된다 (예: 정기가 편재이면 편재격)
3. 특수격 (건록격, 양인격, 종격 등)은 별도 판정
"""

from dataclasses import dataclass

from app.services.saju_engine.constants import (
    BRANCH_INDEX,
    ELEMENT_CONTROL,
    ELEMENT_PRODUCTION,
    GEONROK_MAP,
    STEM_INDEX,
    YANGIN_MAP,
)
from app.services.saju_engine.dto import FullSajuResult, PillarResult
from app.services.saju_engine.ganzhi_math import get_element_relation, get_stem_meta
from app.services.saju_engine.hidden_stem_calculator import HiddenStemCalculator


@dataclass
class GyeokgukResult:
    """격국 판정 결과."""
    gyeokguk_name: str       # 격국 이름 (편재격, 정인격 등)
    gyeokguk_type: str       # 유형 (정격/외격)
    strength: str            # 신강/신약/중화
    strength_score: float    # 신강도 점수 (0~100, 50 중립)
    yongshin_element: str    # 용신 오행
    yongshin_reason: str     # 용신 선정 이유
    gishin_element: str      # 기신 오행
    details: list[str]       # 상세 분석 내역


# 십성 코드 → 격국 이름
SIPSUNG_TO_GYEOKGUK = {
    "bijeon": "건록격",     # 비견이면 건록격으로
    "geopjae": "양인격",    # 겁재이면 양인격으로
    "siksin": "식신격",
    "sanggwan": "상관격",
    "pyeonjae": "편재격",
    "jeongjae": "정재격",
    "pyeongwan": "편관격",
    "jeonggwan": "정관격",
    "pyeonin": "편인격",
    "jeongin": "정인격",
}


class GyeokgukCalculator:
    def __init__(self):
        self.hs_calc = HiddenStemCalculator()

    def calculate(self, result: FullSajuResult) -> GyeokgukResult:
        """격국, 신강/신약, 용신/기신을 판정."""
        day = next((p for p in result.pillars if p.pillar_type == "day"), None)
        month = next((p for p in result.pillars if p.pillar_type == "month"), None)

        if not day or not month:
            return self._default_result()

        day_stem = day.stem_code
        day_meta = get_stem_meta(day_stem)
        day_element = day_meta["stem_element"]

        # 1. 신강/신약 판정
        strength_score, strength, details = self._calc_strength(result, day_stem, day_element)

        # 2. 격국 판정 (월지 정기 기준)
        gyeokguk_name, gyeokguk_type = self._determine_gyeokguk(
            day_stem, month, result.pillars
        )

        # 3. 용신/기신 판정
        yongshin_el, yongshin_reason, gishin_el = self._determine_yongshin(
            day_element, strength, result.five_elements
        )

        details.append(f"격국: {gyeokguk_name} ({gyeokguk_type})")
        details.append(f"용신: {yongshin_el} / 기신: {gishin_el}")

        return GyeokgukResult(
            gyeokguk_name=gyeokguk_name,
            gyeokguk_type=gyeokguk_type,
            strength=strength,
            strength_score=strength_score,
            yongshin_element=yongshin_el,
            yongshin_reason=yongshin_reason,
            gishin_element=gishin_el,
            details=details,
        )

    def _calc_strength(
        self, result: FullSajuResult, day_stem: str, day_element: str
    ) -> tuple[float, str, list[str]]:
        """신강/신약 판정: 일간을 돕는 오행 vs 약화시키는 오행 비교."""
        details = []

        # 일간을 돕는 오행: 같은 오행(비겁) + 나를 생하는 오행(인성)
        helping_elements = {day_element}
        for el, produced in ELEMENT_PRODUCTION.items():
            if produced == day_element:
                helping_elements.add(el)

        # 일간을 약화시키는 오행: 내가 생하는 것(식상) + 내가 극하는 것(재성) + 나를 극하는 것(관성)
        weakening_elements = set()
        weakening_elements.add(ELEMENT_PRODUCTION[day_element])  # 식상
        weakening_elements.add(ELEMENT_CONTROL[day_element])     # 재성
        for el, controlled in ELEMENT_CONTROL.items():
            if controlled == day_element:
                weakening_elements.add(el)  # 관성

        fe = result.five_elements or {}
        help_score = sum(fe.get(el, 0) for el in helping_elements)
        weak_score = sum(fe.get(el, 0) for el in weakening_elements)
        total = help_score + weak_score

        if total == 0:
            return 50.0, "중화", details

        ratio = help_score / total * 100

        # 월령 가산: 월지가 일간을 돕는 오행이면 +10
        month = next((p for p in result.pillars if p.pillar_type == "month"), None)
        if month and month.branch_element in helping_elements:
            ratio += 10
            details.append("월령(月令)이 일간을 도움 → 신강 가산")
        elif month:
            ratio -= 5
            details.append("월령(月令)이 일간을 설기 → 신약 가산")

        # 건록/양인 여부
        for p in result.pillars:
            if p.branch_code == GEONROK_MAP.get(day_stem):
                ratio += 5
                details.append(f"{p.pillar_type}에 건록(建祿) → 신강 가산")
            if p.branch_code == YANGIN_MAP.get(day_stem):
                ratio += 5
                details.append(f"{p.pillar_type}에 양인(羊刃) → 신강 가산")

        ratio = max(0, min(100, ratio))

        if ratio >= 60:
            strength = "신강"
        elif ratio <= 40:
            strength = "신약"
        else:
            strength = "중화"

        details.insert(0, f"일간 도움 점수: {help_score:.1f} / 설기 점수: {weak_score:.1f}")
        details.insert(1, f"신강도: {ratio:.0f}점 → {strength}")

        return ratio, strength, details

    def _determine_gyeokguk(
        self, day_stem: str, month: PillarResult, pillars: list[PillarResult]
    ) -> tuple[str, str]:
        """월지 정기 기준 격국 판정."""
        # 월지 정기 추출
        jeonggi = self.hs_calc.get_jeonggi(month.branch_code)
        if not jeonggi:
            return "미상격", "외격"

        # 정기와 일간의 십성 관계
        day_meta = get_stem_meta(day_stem)
        jeonggi_meta = get_stem_meta(jeonggi)
        relation = get_element_relation(day_meta["stem_element"], jeonggi_meta["stem_element"])
        same_yy = day_meta["stem_yinyang"] == jeonggi_meta["stem_yinyang"]

        # 십성 코드 결정
        ten_god_code = self._relation_to_ten_god(relation, same_yy)

        # 특수격 확인: 건록격
        if month.branch_code == GEONROK_MAP.get(day_stem):
            return "건록격", "외격"

        # 특수격 확인: 양인격
        if month.branch_code == YANGIN_MAP.get(day_stem):
            return "양인격", "외격"

        gyeokguk = SIPSUNG_TO_GYEOKGUK.get(ten_god_code, "미상격")
        return gyeokguk, "정격"

    def _determine_yongshin(
        self, day_element: str, strength: str, five_elements: dict
    ) -> tuple[str, str, str]:
        """용신/기신 판정: 신강이면 설기가 용신, 신약이면 돕는 것이 용신."""
        if strength == "신강":
            # 신강 → 일간의 힘을 빼주는 오행이 용신
            # 우선순위: 식상(내가 생하는) > 재성(내가 극하는) > 관성(나를 극하는)
            yongshin = ELEMENT_PRODUCTION[day_element]  # 식상 오행
            reason = "신강하므로 일간의 기운을 설기(泄氣)하는 식상 오행이 용신"

            # 기신: 일간을 더 강하게 하는 오행
            for el, produced in ELEMENT_PRODUCTION.items():
                if produced == day_element:
                    gishin = el  # 인성 오행
                    break
            else:
                gishin = day_element

        elif strength == "신약":
            # 신약 → 일간을 도와주는 오행이 용신
            # 우선순위: 인성(나를 생하는) > 비겁(같은 오행)
            for el, produced in ELEMENT_PRODUCTION.items():
                if produced == day_element:
                    yongshin = el  # 인성 오행
                    break
            else:
                yongshin = day_element
            reason = "신약하므로 일간을 생조(生助)하는 인성 오행이 용신"

            # 기신: 일간을 더 약하게 하는 오행
            gishin = ELEMENT_CONTROL[day_element]  # 재성 오행

        else:  # 중화
            # 중화 → 가장 부족한 오행이 용신
            if five_elements:
                sorted_els = sorted(five_elements.items(), key=lambda x: x[1])
                yongshin = sorted_els[0][0]
                gishin = sorted_els[-1][0]
            else:
                yongshin = day_element
                gishin = ELEMENT_CONTROL[day_element]
            reason = "중화에 가까우므로 가장 부족한 오행으로 균형을 맞춤"

        return yongshin, reason, gishin

    @staticmethod
    def _relation_to_ten_god(relation: str, same_yinyang: bool) -> str:
        mapping = {
            ("same", True): "bijeon",
            ("same", False): "geopjae",
            ("produce", True): "siksin",
            ("produce", False): "sanggwan",
            ("control", True): "pyeonjae",
            ("control", False): "jeongjae",
            ("controlled", True): "pyeongwan",
            ("controlled", False): "jeonggwan",
            ("produced", True): "pyeonin",
            ("produced", False): "jeongin",
        }
        return mapping.get((relation, same_yinyang), "bijeon")

    @staticmethod
    def _default_result() -> GyeokgukResult:
        return GyeokgukResult(
            gyeokguk_name="미상격",
            gyeokguk_type="외격",
            strength="중화",
            strength_score=50.0,
            yongshin_element="wood",
            yongshin_reason="판정 불가",
            gishin_element="metal",
            details=["명식 정보 부족으로 격국 판정 불가"],
        )
