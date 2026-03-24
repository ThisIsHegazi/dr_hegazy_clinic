from datetime import datetime
import os
from pytz import timezone

WORK_START_HOUR = 14   # 2:00 PM Cairo
WORK_END_HOUR = 20     # 8:00 PM Cairo

ARABIC_WEEKDAYS = {
    "Sunday": "الأحد",
    "Monday": "الاثنين",
    "Tuesday": "الثلاثاء",
    "Wednesday": "الأربعاء",
    "Thursday": "الخميس",
    "Friday": "الجمعة",
    "Saturday": "السبت",
}


def get_current_cairo_time():
    cairo_tz = timezone("Africa/Cairo")
    cairo_time = datetime.now(cairo_tz)
    return cairo_time


def is_workday(date: datetime):
    workdays = {"Sun", "Mon", "Tue", "Wed", "Thu"}
    if date.date().strftime("%a") in workdays:
        return True
    return False


def format_arabic_datetime(dt: datetime) -> str:
    """Return a human-readable Arabic string for a datetime, e.g.
    'الأحد 2025/03/23 الساعة 2:36 م'"""
    day_name = ARABIC_WEEKDAYS.get(dt.strftime("%A"), dt.strftime("%A"))
    date_str = dt.strftime("%Y/%m/%d")
    hour = dt.hour
    minute = dt.minute
    period = "م" if hour >= 12 else "ص"
    hour_12 = hour % 12 or 12
    return f"{day_name} {date_str} الساعة {hour_12}:{minute:02d} {period}"


def _db_backend() -> str:
    return os.getenv("DB_BACKEND", "supabase").lower()


def _use_supabase() -> bool:
    return _db_backend() == "supabase"


def _supabase_table() -> str:
    return os.getenv("SUPABASE_TABLE", "appointments")


def _parse_datetime(value: object) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    raise ValueError("Unsupported datetime format from Supabase")


def _ensure_supabase_ok(response) -> None:
    error = getattr(response, "error", None)
    if error:
        raise RuntimeError(f"Supabase error: {error}")
