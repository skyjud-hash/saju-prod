from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NormalizedBirthData:
    local_datetime: datetime
    utc_datetime: datetime | None = None
    timezone_offset_minutes: int | None = None
    dst_offset_minutes: int = 0
    historical_offset_minutes: int = 0
    true_solar_offset_minutes: int = 0
    adjusted_datetime: datetime | None = None
    hour_unknown: bool = False


@dataclass
class PillarResult:
    pillar_type: str
    stem_code: str
    branch_code: str
    stem_kr: str
    branch_kr: str
    stem_hanja: str
    branch_hanja: str
    stem_yinyang: str
    branch_yinyang: str
    stem_element: str
    branch_element: str
    pillar_order: int


@dataclass
class TenGodResult:
    source_pillar_type: str
    source_position_type: str  # "stem" or "branch_hidden"
    source_code: str
    day_master_stem_code: str
    ten_god_code: str
    ten_god_kr: str
    ten_god_hanja: str
    relation_element_type: str
    relation_yinyang_type: str


@dataclass
class TwelveStageResult:
    target_pillar_type: str
    day_master_stem_code: str
    target_branch_code: str
    stage_code: str
    stage_kr: str
    stage_hanja: str


@dataclass
class RelationResult:
    relation_category: str
    relation_subtype: str | None
    left_position: str
    right_position: str | None
    left_code: str
    right_code: str | None
    is_activated: bool
    note: str | None


@dataclass
class HiddenStemResult:
    pillar_type: str
    branch_code: str
    hidden_stem_order: int
    hidden_stem_code: str
    hidden_stem_kr: str
    hidden_stem_hanja: str
    relative_weight: float | None


@dataclass
class DaewoonResult:
    cycle_index: int
    start_age: int
    end_age: int
    start_year: int | None
    end_year: int | None
    stem_code: str
    branch_code: str
    stem_kr: str
    branch_kr: str
    stem_hanja: str = ""
    branch_hanja: str = ""
    direction: str = ""
    # 십성 (일간 기준)
    stem_ten_god_kr: str = ""
    stem_ten_god_code: str = ""
    branch_ten_god_kr: str = ""    # 지지 본기 기준
    branch_ten_god_code: str = ""
    # 십이운성 (일간 기준)
    twelve_stage_kr: str = ""
    twelve_stage_code: str = ""


@dataclass
class SewoonResult:
    """세운(歲運) — 매년 간지 + 십성 + 십이운성."""
    year: int
    stem_code: str
    branch_code: str
    stem_kr: str
    branch_kr: str
    stem_hanja: str = ""
    branch_hanja: str = ""
    # 십성 (일간 기준)
    stem_ten_god_kr: str = ""
    stem_ten_god_code: str = ""
    branch_ten_god_kr: str = ""    # 지지 본기 기준
    branch_ten_god_code: str = ""
    # 십이운성 (일간 기준)
    twelve_stage_kr: str = ""
    twelve_stage_code: str = ""


@dataclass
class GyeokgukInfo:
    """격국/용신 정보 (해석 엔진에서 사용)."""
    gyeokguk_name: str = ""
    gyeokguk_type: str = ""
    strength: str = ""
    strength_score: float = 50.0
    yongshin_element: str = ""
    yongshin_reason: str = ""
    gishin_element: str = ""
    details: list[str] = field(default_factory=list)


@dataclass
class FullSajuResult:
    pillars: list[PillarResult] = field(default_factory=list)
    hidden_stems: list[HiddenStemResult] = field(default_factory=list)
    ten_gods: list[TenGodResult] = field(default_factory=list)
    twelve_stages: list[TwelveStageResult] = field(default_factory=list)
    relations: list[RelationResult] = field(default_factory=list)
    five_elements: dict[str, float] = field(default_factory=dict)
    daewoon: list[DaewoonResult] = field(default_factory=list)
    gyeokguk: GyeokgukInfo | None = None
