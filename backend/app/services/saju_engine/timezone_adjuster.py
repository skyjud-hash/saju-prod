"""한국 표준시 변경 이력 + DST 보정."""

from datetime import datetime, timedelta

from app.services.saju_engine.dto import NormalizedBirthData

# 한국 시간대 변경 이력 (인메모리, DB 조회 대신 상수로 관리)
KST_OFFSET_HISTORY = [
    # (start, end, utc_offset_minutes)
    (datetime(1800, 1, 1), datetime(1908, 3, 31, 23, 59, 59), 507),
    (datetime(1908, 4, 1), datetime(1911, 12, 31, 23, 59, 59), 510),
    (datetime(1912, 1, 1), datetime(1954, 3, 20, 23, 59, 59), 540),
    (datetime(1954, 3, 21), datetime(1961, 8, 9, 23, 59, 59), 510),
    (datetime(1961, 8, 10), datetime(2099, 12, 31, 23, 59, 59), 540),
]

# DST 이력 (start, end, dst_minutes)
DST_HISTORY = [
    (datetime(1948, 6, 1), datetime(1948, 9, 12, 23, 59, 59), 60),
    (datetime(1949, 4, 3), datetime(1949, 9, 10, 23, 59, 59), 60),
    (datetime(1950, 4, 1), datetime(1950, 9, 9, 23, 59, 59), 60),
    (datetime(1951, 5, 6), datetime(1951, 9, 8, 23, 59, 59), 60),
    (datetime(1955, 5, 5), datetime(1955, 9, 8, 23, 59, 59), 60),
    (datetime(1956, 5, 20), datetime(1956, 9, 29, 23, 59, 59), 60),
    (datetime(1957, 5, 5), datetime(1957, 9, 21, 23, 59, 59), 60),
    (datetime(1958, 5, 4), datetime(1958, 9, 20, 23, 59, 59), 60),
    (datetime(1959, 5, 3), datetime(1959, 9, 19, 23, 59, 59), 60),
    (datetime(1960, 5, 1), datetime(1960, 9, 17, 23, 59, 59), 60),
    (datetime(1987, 5, 10), datetime(1987, 10, 10, 23, 59, 59), 60),
    (datetime(1988, 5, 8), datetime(1988, 10, 8, 23, 59, 59), 60),
]

CURRENT_KST_OFFSET = 540  # 현행 +09:00


def _find_kst_offset(dt: datetime) -> int:
    for start, end, offset in KST_OFFSET_HISTORY:
        if start <= dt <= end:
            return offset
    return CURRENT_KST_OFFSET


def _find_dst_offset(dt: datetime) -> int:
    for start, end, dst_min in DST_HISTORY:
        if start <= dt <= end:
            return dst_min
    return 0


def apply_timezone_rules(
    data: NormalizedBirthData,
    *,
    use_dst_adjustment: bool,
    use_historical_kst_adjust: bool,
    use_true_solar_time: bool,
) -> NormalizedBirthData:
    dt = data.local_datetime
    total_adjustment_minutes = 0

    if use_historical_kst_adjust:
        historical_offset = _find_kst_offset(dt)
        data.timezone_offset_minutes = historical_offset
        diff = CURRENT_KST_OFFSET - historical_offset
        data.historical_offset_minutes = diff
        total_adjustment_minutes += diff

    if use_dst_adjustment:
        dst_offset = _find_dst_offset(dt)
        if dst_offset > 0:
            data.dst_offset_minutes = -dst_offset
            total_adjustment_minutes -= dst_offset

    if total_adjustment_minutes != 0:
        data.adjusted_datetime = dt + timedelta(minutes=total_adjustment_minutes)
    else:
        data.adjusted_datetime = dt

    return data
