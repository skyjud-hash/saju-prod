"""지장간(藏干) 계산기.

학술 근거:
- 이현아·박가현(2025): 지장간 중심 해석 체계 (신법)
- 나혁진(2020): 지장간의 여기/중기/정기 분류와 비율

지장간 구조: 각 지지에 숨어있는 천간 (여기→중기→정기 순)
가중치는 30일 기준 일수 비율 (전통 명리서 『연해자평』 기준):
- 정기(正氣): 해당 지지의 본기, 가장 힘이 강함
- 중기(中氣): 중간 기운
- 여기(餘氣): 이전 월의 잔여 기운, 가장 약함
"""

from app.services.saju_engine.dto import HiddenStemResult, PillarResult
from app.services.saju_engine.ganzhi_math import get_stem_meta

# 지장간 규칙: (천간코드, 일수/30일 가중치, 유형)
# 순서: 여기(餘氣) → 중기(中氣) → 정기(正氣)
# 『연해자평(淵海子平)』 + 『삼명통회(三命通會)』 기준
HIDDEN_STEM_RULES: dict[str, list[tuple[str, float, str]]] = {
    # 子 (자): 계수만 있음 - 순수한 수(水)의 기운
    "ja": [
        ("im", 0.33, "여기"),   # 壬 10일
        ("gye", 0.67, "정기"),  # 癸 20일
    ],
    # 丑 (축): 토왕용사 - 겨울에서 봄으로 넘어가는 토
    "chuk": [
        ("gye", 0.30, "여기"),  # 癸 9일 (子월의 잔기)
        ("sin", 0.10, "중기"),  # 辛 3일
        ("gi", 0.60, "정기"),   # 己 18일
    ],
    # 寅 (인): 봄의 시작, 목기(木氣) 왕성
    "in": [
        ("mu", 0.23, "여기"),   # 戊 7일 (丑월의 잔기)
        ("byeong", 0.23, "중기"),  # 丙 7일
        ("gap", 0.53, "정기"),  # 甲 16일
    ],
    # 卯 (묘): 순수한 목(木)의 기운
    "myo": [
        ("gap", 0.33, "여기"),  # 甲 10일
        ("eul", 0.67, "정기"),  # 乙 20일
    ],
    # 辰 (진): 봄에서 여름으로 넘어가는 토
    "jin": [
        ("eul", 0.30, "여기"),  # 乙 9일 (卯월의 잔기)
        ("gye", 0.10, "중기"),  # 癸 3일
        ("mu", 0.60, "정기"),   # 戊 18일
    ],
    # 巳 (사): 여름의 시작, 화기(火氣) + 금(金) 잉태
    "sa": [
        ("mu", 0.23, "여기"),   # 戊 7일 (辰월의 잔기)
        ("gyeong", 0.23, "중기"),  # 庚 7일
        ("byeong", 0.53, "정기"),  # 丙 16일
    ],
    # 午 (오): 화(火) 왕성, 토(土) 내포
    "o": [
        ("byeong", 0.33, "여기"),  # 丙 10일
        ("gi", 0.30, "중기"),   # 己 9일
        ("jeong", 0.37, "정기"),  # 丁 11일
    ],
    # 未 (미): 여름에서 가을로 넘어가는 토
    "mi": [
        ("jeong", 0.30, "여기"),  # 丁 9일 (午월의 잔기)
        ("eul", 0.10, "중기"),  # 乙 3일
        ("gi", 0.60, "정기"),   # 己 18일
    ],
    # 申 (신): 가을의 시작, 금기(金氣) 왕성
    "sin_branch": [
        ("gi", 0.23, "여기"),   # 己 7일 (未월의 잔기)
        ("im", 0.23, "중기"),   # 壬 7일
        ("gyeong", 0.53, "정기"),  # 庚 16일
    ],
    # 酉 (유): 순수한 금(金)의 기운
    "yu": [
        ("gyeong", 0.33, "여기"),  # 庚 10일
        ("sin", 0.67, "정기"),  # 辛 20일
    ],
    # 戌 (술): 가을에서 겨울로 넘어가는 토
    "sul": [
        ("sin", 0.30, "여기"),  # 辛 9일 (酉월의 잔기)
        ("jeong", 0.10, "중기"),  # 丁 3일
        ("mu", 0.60, "정기"),   # 戊 18일
    ],
    # 亥 (해): 겨울의 시작, 수기(水氣) 왕성
    "hae": [
        ("mu", 0.23, "여기"),   # 戊 7일 (戌월의 잔기)
        ("gap", 0.23, "중기"),  # 甲 7일
        ("im", 0.53, "정기"),   # 壬 16일
    ],
}


class HiddenStemCalculator:
    def calculate_for_branch(self, branch_code: str) -> list[dict]:
        rules = HIDDEN_STEM_RULES.get(branch_code, [])
        results = []
        for order, (stem_code, weight, qi_type) in enumerate(rules, start=1):
            meta = get_stem_meta(stem_code)
            results.append({
                "hidden_stem_order": order,
                "hidden_stem_code": stem_code,
                "hidden_stem_kr": meta["stem_kr"],
                "hidden_stem_hanja": meta["stem_hanja"],
                "relative_weight": weight,
                "qi_type": qi_type,
            })
        return results

    def calculate_for_pillars(self, pillars: list[PillarResult]) -> list[HiddenStemResult]:
        results = []
        for pillar in pillars:
            branch_results = self.calculate_for_branch(pillar.branch_code)
            for item in branch_results:
                results.append(HiddenStemResult(
                    pillar_type=pillar.pillar_type,
                    branch_code=pillar.branch_code,
                    hidden_stem_order=item["hidden_stem_order"],
                    hidden_stem_code=item["hidden_stem_code"],
                    hidden_stem_kr=item["hidden_stem_kr"],
                    hidden_stem_hanja=item["hidden_stem_hanja"],
                    relative_weight=item["relative_weight"],
                ))
        return results

    def get_jeonggi(self, branch_code: str) -> str | None:
        """해당 지지의 정기(正氣) 천간 코드를 반환."""
        rules = HIDDEN_STEM_RULES.get(branch_code, [])
        for stem_code, _, qi_type in rules:
            if qi_type == "정기":
                return stem_code
        return rules[-1][0] if rules else None
