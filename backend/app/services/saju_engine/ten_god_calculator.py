"""십성(十星) 계산기. 일간 기준으로 다른 천간/지장간과의 관계를 산출."""

from app.services.saju_engine.dto import HiddenStemResult, PillarResult, TenGodResult
from app.services.saju_engine.ganzhi_math import get_element_relation, get_stem_meta

# 십성 매핑: (element_relation, same_yinyang) -> (code, kr, hanja)
TEN_GOD_MAP = {
    ("same", True): ("bijeon", "비견", "比肩"),
    ("same", False): ("geopjae", "겁재", "劫財"),
    ("produce", True): ("siksin", "식신", "食神"),
    ("produce", False): ("sanggwan", "상관", "傷官"),
    ("control", True): ("pyeonjae", "편재", "偏財"),
    ("control", False): ("jeongjae", "정재", "正財"),
    ("controlled", True): ("pyeongwan", "편관", "偏官"),
    ("controlled", False): ("jeonggwan", "정관", "正官"),
    ("produced", True): ("pyeonin", "편인", "偏印"),
    ("produced", False): ("jeongin", "정인", "正印"),
}


class TenGodCalculator:
    def _compute(self, day_master_stem_code: str, target_stem_code: str) -> tuple[str, str, str]:
        day_meta = get_stem_meta(day_master_stem_code)
        target_meta = get_stem_meta(target_stem_code)

        relation = get_element_relation(day_meta["stem_element"], target_meta["stem_element"])
        same_yinyang = (day_meta["stem_yinyang"] == target_meta["stem_yinyang"])

        return TEN_GOD_MAP[(relation, same_yinyang)]

    def calculate_for_stem(
        self, *, day_master_stem_code: str, target_stem_code: str,
        source_pillar_type: str, source_position_type: str = "stem",
    ) -> TenGodResult:
        code, kr, hanja = self._compute(day_master_stem_code, target_stem_code)
        day_meta = get_stem_meta(day_master_stem_code)
        target_meta = get_stem_meta(target_stem_code)

        return TenGodResult(
            source_pillar_type=source_pillar_type,
            source_position_type=source_position_type,
            source_code=target_stem_code,
            day_master_stem_code=day_master_stem_code,
            ten_god_code=code,
            ten_god_kr=kr,
            ten_god_hanja=hanja,
            relation_element_type=get_element_relation(
                day_meta["stem_element"], target_meta["stem_element"]
            ),
            relation_yinyang_type=(
                "same" if day_meta["stem_yinyang"] == target_meta["stem_yinyang"] else "different"
            ),
        )

    def calculate_all(
        self, pillars: list[PillarResult],
        hidden_stems: list[HiddenStemResult],
    ) -> list[TenGodResult]:
        """4주의 모든 천간 + 지장간에 대한 십성을 산출."""
        day_pillar = next(p for p in pillars if p.pillar_type == "day")
        day_master = day_pillar.stem_code
        results = []

        # 각 주의 천간에 대한 십성
        for pillar in pillars:
            if pillar.pillar_type == "day":
                continue  # 일간 자신은 건너뜀 (비견이므로)
            results.append(self.calculate_for_stem(
                day_master_stem_code=day_master,
                target_stem_code=pillar.stem_code,
                source_pillar_type=pillar.pillar_type,
                source_position_type="stem",
            ))

        # 각 주의 지장간에 대한 십성
        for hs in hidden_stems:
            results.append(self.calculate_for_stem(
                day_master_stem_code=day_master,
                target_stem_code=hs.hidden_stem_code,
                source_pillar_type=hs.pillar_type,
                source_position_type="branch_hidden",
            ))

        return results
