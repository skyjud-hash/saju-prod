"""합충형해파(合沖刑害破) 관계 계산기."""

from itertools import combinations

from app.services.saju_engine.dto import PillarResult, RelationResult

# 천간합 (left, right, result_note)
CHEONGAN_HAP = [
    ("gap", "gi", "갑기합토"),
    ("eul", "gyeong", "을경합금"),
    ("byeong", "sin", "병신합수"),
    ("jeong", "im", "정임합목"),
    ("mu", "gye", "무계합화"),
]

# 천간충
CHEONGAN_CHUNG = [
    ("gap", "gyeong"), ("eul", "sin"), ("byeong", "im"), ("jeong", "gye"),
]

# 지지육합
JIJI_YUKHAP = [
    ("ja", "chuk", "자축합토"), ("in", "hae", "인해합목"),
    ("myo", "sul", "묘술합화"), ("jin", "yu", "진유합금"),
    ("sa", "sin_branch", "사신합수"), ("o", "mi", "오미합화"),
]

# 지지충
JIJI_CHUNG = [
    ("ja", "o"), ("chuk", "mi"), ("in", "sin_branch"),
    ("myo", "yu"), ("jin", "sul"), ("sa", "hae"),
]

# 지지삼합 (3개 지지가 모여야 성립)
JIJI_SAMHAP = [
    ({"in", "o", "sul"}, "화국", "인오술 삼합화국"),
    ({"sa", "yu", "chuk"}, "금국", "사유축 삼합금국"),
    ({"sin_branch", "ja", "jin"}, "수국", "신자진 삼합수국"),
    ({"hae", "myo", "mi"}, "목국", "해묘미 삼합목국"),
]

# 지지방합
JIJI_BANGHAP = [
    ({"in", "myo", "jin"}, "목방", "인묘진 방합목"),
    ({"sa", "o", "mi"}, "화방", "사오미 방합화"),
    ({"sin_branch", "yu", "sul"}, "금방", "신유술 방합금"),
    ({"hae", "ja", "chuk"}, "수방", "해자축 방합수"),
]

# 지지형
JIJI_HYEONG = [
    ("in", "sa", "무은지형"), ("sa", "sin_branch", "무은지형"),
    ("sin_branch", "in", "무은지형"),
    ("chuk", "sul", "지세지형"), ("sul", "mi", "지세지형"),
    ("mi", "chuk", "지세지형"),
    ("ja", "myo", "무례지형"),
    ("jin", "jin", "자형"), ("o", "o", "자형"),
    ("yu", "yu", "자형"), ("hae", "hae", "자형"),
]

# 지지해
JIJI_HAE = [
    ("ja", "mi"), ("chuk", "o"), ("in", "sa"),
    ("myo", "jin"), ("sin_branch", "hae"), ("yu", "sul"),
]

# 지지파
JIJI_PA = [
    ("ja", "yu"), ("chuk", "jin"), ("in", "hae"),
    ("myo", "o"), ("sa", "sin_branch"), ("mi", "sul"),
]


def _match_pair(code1: str, code2: str, pair: tuple[str, str]) -> bool:
    return (code1 == pair[0] and code2 == pair[1]) or (code1 == pair[1] and code2 == pair[0])


class RelationCalculator:
    def calculate(self, pillars: list[PillarResult]) -> list[RelationResult]:
        results: list[RelationResult] = []
        stems = [(p.pillar_type, p.stem_code) for p in pillars]
        branches = [(p.pillar_type, p.branch_code) for p in pillars]

        # 천간합
        for (pos1, s1), (pos2, s2) in combinations(stems, 2):
            for left, right, note in CHEONGAN_HAP:
                if _match_pair(s1, s2, (left, right)):
                    results.append(RelationResult(
                        relation_category="천간합", relation_subtype=None,
                        left_position=pos1, right_position=pos2,
                        left_code=s1, right_code=s2,
                        is_activated=True, note=note,
                    ))

        # 천간충
        for (pos1, s1), (pos2, s2) in combinations(stems, 2):
            for left, right in CHEONGAN_CHUNG:
                if _match_pair(s1, s2, (left, right)):
                    results.append(RelationResult(
                        relation_category="천간충", relation_subtype=None,
                        left_position=pos1, right_position=pos2,
                        left_code=s1, right_code=s2,
                        is_activated=True, note=f"{s1}{s2}충",
                    ))

        # 지지육합
        for (pos1, b1), (pos2, b2) in combinations(branches, 2):
            for left, right, note in JIJI_YUKHAP:
                if _match_pair(b1, b2, (left, right)):
                    results.append(RelationResult(
                        relation_category="지지육합", relation_subtype=None,
                        left_position=pos1, right_position=pos2,
                        left_code=b1, right_code=b2,
                        is_activated=True, note=note,
                    ))

        # 지지충
        for (pos1, b1), (pos2, b2) in combinations(branches, 2):
            for left, right in JIJI_CHUNG:
                if _match_pair(b1, b2, (left, right)):
                    results.append(RelationResult(
                        relation_category="지지충", relation_subtype=None,
                        left_position=pos1, right_position=pos2,
                        left_code=b1, right_code=b2,
                        is_activated=True, note=f"{b1}{b2}충",
                    ))

        # 지지삼합
        branch_codes = {b for _, b in branches}
        branch_positions = {b: pos for pos, b in branches}
        for required_set, subtype, note in JIJI_SAMHAP:
            if required_set.issubset(branch_codes):
                codes_list = sorted(required_set)
                results.append(RelationResult(
                    relation_category="지지삼합", relation_subtype=subtype,
                    left_position=branch_positions.get(codes_list[0], ""),
                    right_position=branch_positions.get(codes_list[1], ""),
                    left_code=codes_list[0], right_code=codes_list[1],
                    is_activated=True, note=note,
                ))

        # 지지방합
        for required_set, subtype, note in JIJI_BANGHAP:
            if required_set.issubset(branch_codes):
                codes_list = sorted(required_set)
                results.append(RelationResult(
                    relation_category="지지방합", relation_subtype=subtype,
                    left_position=branch_positions.get(codes_list[0], ""),
                    right_position=branch_positions.get(codes_list[1], ""),
                    left_code=codes_list[0], right_code=codes_list[1],
                    is_activated=True, note=note,
                ))

        # 지지형
        for (pos1, b1), (pos2, b2) in combinations(branches, 2):
            for left, right, subtype in JIJI_HYEONG:
                if b1 == left and b2 == right:
                    results.append(RelationResult(
                        relation_category="지지형", relation_subtype=subtype,
                        left_position=pos1, right_position=pos2,
                        left_code=b1, right_code=b2,
                        is_activated=True, note=f"{b1}{b2}형",
                    ))
        # 자형 (같은 지지)
        for (pos1, b1), (pos2, b2) in combinations(branches, 2):
            if b1 == b2 and b1 in ("jin", "o", "yu", "hae"):
                results.append(RelationResult(
                    relation_category="지지형", relation_subtype="자형",
                    left_position=pos1, right_position=pos2,
                    left_code=b1, right_code=b2,
                    is_activated=True, note=f"{b1}{b2}자형",
                ))

        # 지지해
        for (pos1, b1), (pos2, b2) in combinations(branches, 2):
            for left, right in JIJI_HAE:
                if _match_pair(b1, b2, (left, right)):
                    results.append(RelationResult(
                        relation_category="지지해", relation_subtype=None,
                        left_position=pos1, right_position=pos2,
                        left_code=b1, right_code=b2,
                        is_activated=True, note=f"{b1}{b2}해",
                    ))

        # 지지파
        for (pos1, b1), (pos2, b2) in combinations(branches, 2):
            for left, right in JIJI_PA:
                if _match_pair(b1, b2, (left, right)):
                    results.append(RelationResult(
                        relation_category="지지파", relation_subtype=None,
                        left_position=pos1, right_position=pos2,
                        left_code=b1, right_code=b2,
                        is_activated=True, note=f"{b1}{b2}파",
                    ))

        return results
