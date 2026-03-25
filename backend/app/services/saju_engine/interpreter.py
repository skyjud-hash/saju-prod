"""사주 해석 엔진 - 7레이어 템플릿 기반 다각도 해석."""

from app.services.saju_engine.dto import FullSajuResult
from app.services.saju_engine.ganzhi_math import get_stem_meta
from app.services.saju_engine.interpretation_data import (
    ELEMENT_CAREER_MAP,
    ELEMENT_DEFICIT,
    ELEMENT_EXCESS,
    ILGAN_INTERPRETATION,
    RELATION_INTERPRETATION,
    TEN_GOD_GROUP_INTERPRETATION,
    TWELVE_STAGE_INTERPRETATION,
)

ELEMENT_KR = {"wood": "목(木)", "fire": "화(火)", "earth": "토(土)", "metal": "금(金)", "water": "수(水)"}


class Interpreter:
    def interpret(self, result: FullSajuResult) -> list[dict]:
        """7레이어 해석 결과를 섹션별 딕셔너리 리스트로 반환."""
        sections = []

        sections.append(self._layer1_ilgan(result))
        sections.append(self._layer_gyeokguk(result))
        sections.append(self._layer2_oheng(result))
        sections.append(self._layer3_sipsung(result))
        sections.append(self._layer4_relations(result))
        sections.append(self._layer5_twelve_stages(result))
        sections.append(self._layer6_daewoon(result))
        sections.append(self._layer7_career(result))

        return [s for s in sections if s is not None]

    def _layer1_ilgan(self, result: FullSajuResult) -> dict | None:
        """레이어 1: 일간 성격론."""
        day = next((p for p in result.pillars if p.pillar_type == "day"), None)
        if not day:
            return None

        data = ILGAN_INTERPRETATION.get(day.stem_code)
        if not data:
            return None

        return {
            "section": "ilgan",
            "icon": "🌟",
            "title": data["title"],
            "content": data["personality"],
            "details": [
                f"강점: {data['strength']}",
                f"약점: {data['weakness']}",
                f"이미지: {data['image']}",
            ],
        }

    def _layer_gyeokguk(self, result: FullSajuResult) -> dict | None:
        """격국·용신 해석 (나혁진 2020 기반)."""
        gk = result.gyeokguk
        if not gk:
            return None

        strength_desc = {
            "신강": "일간의 힘이 강한 편입니다. 자신감과 추진력이 있지만, 자기중심적일 수 있어 기운을 분산시키는 활동이 도움됩니다.",
            "신약": "일간의 힘이 약한 편입니다. 섬세하고 협조적이지만, 자신감이 부족할 수 있어 자기 역량을 키우는 활동이 도움됩니다.",
            "중화": "일간의 힘이 균형을 이루고 있습니다. 안정적인 성향으로, 어느 방향으로든 유연하게 대처할 수 있습니다.",
        }

        content = (
            f"격국은 {gk.gyeokguk_name}({gk.gyeokguk_type})이며, "
            f"신강도는 {gk.strength_score:.0f}점으로 {gk.strength} 상태입니다. "
            f"{strength_desc.get(gk.strength, '')}"
        )

        details = [
            f"용신(用神): {ELEMENT_KR.get(gk.yongshin_element, gk.yongshin_element)} — {gk.yongshin_reason}",
            f"기신(忌神): {ELEMENT_KR.get(gk.gishin_element, gk.gishin_element)} — 이 오행이 과도하면 불리",
        ]
        details.extend(gk.details[:3])

        return {
            "section": "gyeokguk",
            "icon": "⚖",
            "title": f"격국 분석 — {gk.gyeokguk_name} ({gk.strength})",
            "content": content,
            "details": details,
        }

    def _layer2_oheng(self, result: FullSajuResult) -> dict | None:
        """레이어 2: 오행 균형 분석."""
        fe = result.five_elements
        if not fe:
            return None

        total = sum(fe.values())
        if total == 0:
            return None

        avg = total / 5
        lines = []

        # 분포 요약
        dist_parts = []
        for el in ["wood", "fire", "earth", "metal", "water"]:
            score = fe.get(el, 0)
            pct = score / total * 100
            dist_parts.append(f"{ELEMENT_KR[el]} {score:.1f}점({pct:.0f}%)")
        lines.append(" | ".join(dist_parts))

        # 과다/부족 분석
        excess = [(el, fe[el]) for el in fe if fe[el] > avg * 1.4]
        deficit = [(el, fe[el]) for el in fe if fe[el] < avg * 0.5]

        for el, _ in sorted(excess, key=lambda x: -x[1]):
            lines.append(ELEMENT_EXCESS.get(el, ""))

        for el, _ in sorted(deficit, key=lambda x: x[1]):
            lines.append(ELEMENT_DEFICIT.get(el, ""))

        if not excess and not deficit:
            lines.append("오행이 비교적 고르게 분포되어 있어 균형 잡힌 성향을 가지고 있습니다. 어느 한 쪽으로 치우치지 않아 다방면에서 능력을 발휘할 수 있습니다.")

        return {
            "section": "oheng",
            "icon": "☯",
            "title": "오행 균형 분석",
            "content": lines[0],
            "details": lines[1:],
        }

    def _layer3_sipsung(self, result: FullSajuResult) -> dict | None:
        """레이어 3: 십성 강세 그룹별 적성."""
        if not result.ten_gods:
            return None

        # 십성별 카운트
        counts = {}
        for tg in result.ten_gods:
            code = tg.ten_god_code
            counts[code] = counts.get(code, 0) + 1

        # 그룹별 합산
        group_scores = {
            "비겁": counts.get("bijeon", 0) + counts.get("geopjae", 0),
            "식상": counts.get("siksin", 0) + counts.get("sanggwan", 0),
            "재성": counts.get("pyeonjae", 0) + counts.get("jeongjae", 0),
            "관성": counts.get("pyeongwan", 0) + counts.get("jeonggwan", 0),
            "인성": counts.get("pyeonin", 0) + counts.get("jeongin", 0),
        }

        # 상위 2개 그룹
        top_groups = sorted(group_scores.items(), key=lambda x: -x[1])[:2]
        primary = top_groups[0][0] if top_groups[0][1] > 0 else None

        if not primary:
            return None

        data = TEN_GOD_GROUP_INTERPRETATION.get(primary)
        if not data:
            return None

        content = data["text"]

        # 개별 십성 상세
        details = []
        god_kr_map = {
            "bijeon": "비견", "geopjae": "겁재", "siksin": "식신", "sanggwan": "상관",
            "pyeonjae": "편재", "jeongjae": "정재", "pyeongwan": "편관", "jeonggwan": "정관",
            "pyeonin": "편인", "jeongin": "정인",
        }
        stem_gods = [tg for tg in result.ten_gods if tg.source_position_type == "stem"]
        if stem_gods:
            god_parts = []
            for tg in stem_gods:
                pillar_kr = {"year": "연주", "month": "월주", "hour": "시주"}.get(tg.source_pillar_type, tg.source_pillar_type)
                god_parts.append(f"{pillar_kr}: {tg.ten_god_kr}")
            details.append("천간 십성 배치: " + ", ".join(god_parts))

        if len(top_groups) > 1 and top_groups[1][1] > 0:
            sub_data = TEN_GOD_GROUP_INTERPRETATION.get(top_groups[1][0])
            if sub_data:
                details.append(f"보조 성향 ({top_groups[1][0]}): {sub_data['text'][:80]}...")

        return {
            "section": "sipsung",
            "icon": "⭐",
            "title": data["title"],
            "content": content,
            "details": details,
        }

    def _layer4_relations(self, result: FullSajuResult) -> dict | None:
        """레이어 4: 합충형해파 해석."""
        if not result.relations:
            return {
                "section": "relations",
                "icon": "🔗",
                "title": "합충형해파 관계",
                "content": "명식 내 특별한 합충형해파 관계가 없어 안정적인 구조를 가지고 있습니다.",
                "details": [],
            }

        lines = []
        seen_categories = set()
        for r in result.relations:
            cat = r.relation_category
            if cat not in seen_categories:
                seen_categories.add(cat)
                interp = RELATION_INTERPRETATION.get(cat, "")
                if interp:
                    lines.append(interp)

        detail_tags = [f"{r.relation_category}: {r.note or ''}" for r in result.relations]

        return {
            "section": "relations",
            "icon": "🔗",
            "title": "합충형해파 관계",
            "content": lines[0] if lines else "관계 분석 결과입니다.",
            "details": (lines[1:] if len(lines) > 1 else []) + [" | ".join(detail_tags)],
        }

    def _layer5_twelve_stages(self, result: FullSajuResult) -> dict | None:
        """레이어 5: 십이운성 해석."""
        if not result.twelve_stages:
            return None

        lines = []
        for ts in result.twelve_stages:
            pillar_kr = {"year": "연주", "month": "월주", "day": "일주", "hour": "시주"}.get(
                ts.target_pillar_type, ts.target_pillar_type
            )
            interp = TWELVE_STAGE_INTERPRETATION.get(ts.stage_code, ts.stage_kr)
            lines.append(f"{pillar_kr}: {interp}")

        # 일주의 십이운성을 대표 문장으로
        day_stage = next((ts for ts in result.twelve_stages if ts.target_pillar_type == "day"), None)
        if day_stage:
            main = TWELVE_STAGE_INTERPRETATION.get(day_stage.stage_code, day_stage.stage_kr)
            content = f"일주의 십이운성은 {day_stage.stage_kr}입니다. {main}"
        else:
            content = "십이운성 분석 결과입니다."

        return {
            "section": "twelve_stages",
            "icon": "🔄",
            "title": "십이운성 (생명 에너지 흐름)",
            "content": content,
            "details": [l for l in lines if "일주" not in l],
        }

    def _layer6_daewoon(self, result: FullSajuResult) -> dict | None:
        """레이어 6: 대운 흐름 해석."""
        if not result.daewoon:
            return None

        lines = []
        for d in result.daewoon[:6]:
            stem_meta = get_stem_meta(d.stem_code)
            el_kr = ELEMENT_KR.get(stem_meta["stem_element"], "")
            lines.append(
                f"{d.start_age:.0f}~{d.end_age:.0f}세 ({d.start_year}~{d.end_year}): "
                f"{d.stem_kr}{d.branch_kr} - {el_kr} 기운의 시기"
            )

        direction = result.daewoon[0].direction
        dir_kr = "순행(順行)" if direction == "forward" else "역행(逆行)"

        content = (
            f"대운이 {dir_kr}으로 흐릅니다. "
            f"대운은 10년 단위로 바뀌는 큰 운의 흐름으로, "
            f"각 시기에 어떤 오행의 에너지가 강해지는지에 따라 학업과 진로에 유리한 시기가 달라집니다."
        )

        return {
            "section": "daewoon",
            "icon": "📈",
            "title": "대운 흐름 (10년 주기 운세)",
            "content": content,
            "details": lines,
        }

    def _layer7_career(self, result: FullSajuResult) -> dict | None:
        """레이어 7: 종합 진로 추천 (격국 용신 기반)."""
        fe = result.five_elements
        if not fe:
            return None

        total = sum(fe.values())
        if total == 0:
            return None

        # 격국 판정에서 산출된 용신 사용 (학술적으로 정확)
        if result.gyeokguk and result.gyeokguk.yongshin_element:
            yongshin_el = result.gyeokguk.yongshin_element
        else:
            # fallback: 가장 부족한 오행
            deficit_elements = sorted(fe.items(), key=lambda x: x[1])
            yongshin_el = deficit_elements[0][0]

        career_data = ELEMENT_CAREER_MAP.get(yongshin_el)

        # 십성 기반 보조 추천
        sipsung_careers = []
        sipsung_majors = []
        if result.ten_gods:
            counts = {}
            for tg in result.ten_gods:
                code = tg.ten_god_code
                counts[code] = counts.get(code, 0) + 1
            group_scores = {
                "비겁": counts.get("bijeon", 0) + counts.get("geopjae", 0),
                "식상": counts.get("siksin", 0) + counts.get("sanggwan", 0),
                "재성": counts.get("pyeonjae", 0) + counts.get("jeongjae", 0),
                "관성": counts.get("pyeongwan", 0) + counts.get("jeonggwan", 0),
                "인성": counts.get("pyeonin", 0) + counts.get("jeongin", 0),
            }
            top_group = max(group_scores.items(), key=lambda x: x[1])[0]
            tg_data = TEN_GOD_GROUP_INTERPRETATION.get(top_group)
            if tg_data:
                sipsung_careers = tg_data["careers"]
                sipsung_majors = tg_data["majors"]

        if not career_data:
            return None

        content = (
            f"오행 분석 결과 {ELEMENT_KR[yongshin_el]} 방향의 활동이 균형을 맞추는 데 도움이 됩니다. "
            f"추천 분야: {career_data['direction']}"
        )

        details = []
        details.append("오행 기반 추천 직업: " + ", ".join(career_data["careers"][:5]))
        details.append("오행 기반 추천 전공: " + ", ".join(career_data["majors"][:5]))

        if sipsung_careers:
            details.append("십성 기반 추천 직업: " + ", ".join(sipsung_careers[:4]))
        if sipsung_majors:
            details.append("십성 기반 추천 전공: " + ", ".join(sipsung_majors[:4]))

        return {
            "section": "career",
            "icon": "🎯",
            "title": "진로 방향 추천",
            "content": content,
            "details": details,
        }
