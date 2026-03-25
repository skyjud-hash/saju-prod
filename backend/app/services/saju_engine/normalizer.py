"""생년월일시 정규화."""

from datetime import datetime

from app.services.saju_engine.dto import NormalizedBirthData


def normalize_birth_datetime(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int | None,
    birth_minute: int | None,
) -> NormalizedBirthData:
    hour = 12 if birth_hour is None else birth_hour
    minute = 0 if birth_minute is None else birth_minute

    local_dt = datetime(birth_year, birth_month, birth_day, hour, minute)

    return NormalizedBirthData(
        local_datetime=local_dt,
        adjusted_datetime=local_dt,
    )
