from datetime import datetime, time


DAYS_MAP = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}


def get_today_day_name() -> str:
    return DAYS_MAP[datetime.now().weekday()]


def is_quiet_time(quiet_start: time, quiet_end: time) -> bool:
    now = datetime.now().time()
    if quiet_start <= quiet_end:
        return quiet_start <= now <= quiet_end
    else:
        return now >= quiet_start or now <= quiet_end


def parse_time(text: str) -> time | None:
    try:
        parts = text.strip().split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return None