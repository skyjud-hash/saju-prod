"""간지 수학 유틸리티: 천간/지지 메타데이터 조회 및 산술 연산."""

from app.services.saju_engine.constants import BRANCHES, BRANCH_INDEX, STEMS, STEM_INDEX


def get_stem_meta(stem_code: str) -> dict:
    for code, kr, hanja, yinyang, element in STEMS:
        if code == stem_code:
            return {
                "stem_code": code,
                "stem_kr": kr,
                "stem_hanja": hanja,
                "stem_yinyang": yinyang,
                "stem_element": element,
            }
    raise ValueError(f"Unknown stem_code: {stem_code}")


def get_branch_meta(branch_code: str) -> dict:
    for entry in BRANCHES:
        code, kr, hanja, yinyang, element = entry[0], entry[1], entry[2], entry[3], entry[4]
        if code == branch_code:
            return {
                "branch_code": code,
                "branch_kr": kr,
                "branch_hanja": hanja,
                "branch_yinyang": yinyang,
                "branch_element": element,
            }
    raise ValueError(f"Unknown branch_code: {branch_code}")


def add_stem(stem_code: str, step: int) -> str:
    idx = STEM_INDEX[stem_code]
    return STEMS[(idx + step) % 10][0]


def add_branch(branch_code: str, step: int) -> str:
    idx = BRANCH_INDEX[branch_code]
    return BRANCHES[(idx + step) % 12][0]


def stem_group(stem_code: str) -> str:
    if stem_code in ("gap", "gi"):
        return "gap_gi"
    if stem_code in ("eul", "gyeong"):
        return "eul_gyeong"
    if stem_code in ("byeong", "sin"):
        return "byeong_sin"
    if stem_code in ("jeong", "im"):
        return "jeong_im"
    return "mu_gye"


def get_element_relation(my_element: str, target_element: str) -> str:
    from app.services.saju_engine.constants import ELEMENT_CONTROL, ELEMENT_PRODUCTION

    if my_element == target_element:
        return "same"
    if ELEMENT_PRODUCTION.get(my_element) == target_element:
        return "produce"
    if ELEMENT_CONTROL.get(my_element) == target_element:
        return "control"
    if ELEMENT_PRODUCTION.get(target_element) == my_element:
        return "produced"
    if ELEMENT_CONTROL.get(target_element) == my_element:
        return "controlled"
    raise ValueError(f"Cannot determine relation: {my_element} -> {target_element}")
