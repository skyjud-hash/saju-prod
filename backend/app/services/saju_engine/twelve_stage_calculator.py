"""십이운성(十二運星) 계산기."""

from app.services.saju_engine.constants import (
    BRANCH_INDEX,
    TWELVE_STAGE_NAMES,
    YANG_STEM_JANGSEANG_BRANCH,
    YIN_STEM_JANGSEANG_BRANCH,
)
from app.services.saju_engine.dto import PillarResult, TwelveStageResult
from app.services.saju_engine.ganzhi_math import get_stem_meta


class TwelveStageCalculator:
    def calculate(self, day_master_stem_code: str, target_branch_code: str) -> tuple[str, str, str]:
        """일간 기준으로 대상 지지의 십이운성을 산출."""
        meta = get_stem_meta(day_master_stem_code)

        if meta["stem_yinyang"] == "yang":
            jangseang_branch = YANG_STEM_JANGSEANG_BRANCH[day_master_stem_code]
            direction = 1  # 순방향
        else:
            jangseang_branch = YIN_STEM_JANGSEANG_BRANCH[day_master_stem_code]
            direction = -1  # 역방향

        jangseang_idx = BRANCH_INDEX[jangseang_branch]
        target_idx = BRANCH_INDEX[target_branch_code]

        offset = (target_idx - jangseang_idx) * direction
        stage_index = offset % 12

        code, kr, hanja = TWELVE_STAGE_NAMES[stage_index]
        return code, kr, hanja

    def calculate_all(self, pillars: list[PillarResult]) -> list[TwelveStageResult]:
        day_pillar = next(p for p in pillars if p.pillar_type == "day")
        day_master = day_pillar.stem_code
        results = []

        for pillar in pillars:
            code, kr, hanja = self.calculate(day_master, pillar.branch_code)
            results.append(TwelveStageResult(
                target_pillar_type=pillar.pillar_type,
                day_master_stem_code=day_master,
                target_branch_code=pillar.branch_code,
                stage_code=code,
                stage_kr=kr,
                stage_hanja=hanja,
            ))

        return results
