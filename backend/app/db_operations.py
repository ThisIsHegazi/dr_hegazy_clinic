from datetime import date, datetime, timedelta
import os
from sqlmodel import Session, select
from app.models import Appointments, Admins, engine
from app.services import (
    WORK_START_HOUR,
    WORK_END_HOUR,
    get_current_cairo_time,
    is_workday,
    _ensure_supabase_ok,
    _parse_datetime,
    _supabase_table,
    _use_supabase,
)

# Each appointment slot duration in minutes
_SLOT_MINUTES = 20

# Maximum daily appointments derived from working hours and slot duration
MAX_DAILY_APPOINTMENTS = (WORK_END_HOUR - WORK_START_HOUR) * 60 // _SLOT_MINUTES


def _compute_slot(target_date: datetime) -> datetime:
    """Return the exact slot datetime for the NEXT available slot on target_date's day.

    Instead of using ap_count as a simple index (which breaks when earlier slots
    are deleted, causing collisions with still-existing later slots), we probe
    each slot position starting from WORK_START_HOUR and return the first one
    that has no existing appointment at that exact minute.
    """
    cairo_tz = target_date.tzinfo
    day = target_date.date()
    slot_start = datetime(day.year, day.month, day.day, WORK_START_HOUR, 0, tzinfo=cairo_tz)

    for i in range(MAX_DAILY_APPOINTMENTS):
        candidate = slot_start + timedelta(minutes=i * _SLOT_MINUTES)
        if not _slot_taken(candidate):
            return candidate

    # Fallback (shouldn't be reached if appoints_max_limit is used correctly)
    return slot_start + timedelta(minutes=ap_count(target_date) * _SLOT_MINUTES)


def _slot_taken(slot_dt: datetime) -> bool:
    """Return True if there is already an appointment at exactly this slot datetime."""
    if _use_supabase():
        client = _get_supabase_client()
        response = (
            client.table(_supabase_table())
            .select("id", count="exact")
            .eq("scheduled_at", slot_dt.isoformat())
            .execute()
        )
        _ensure_supabase_ok(response)
        count = response.count if response.count is not None else len(response.data or [])
        return count > 0

    with Session(engine) as session:
        statement = select(Appointments).where(
            Appointments.scheduled_at == slot_dt,
        )
        return session.exec(statement).first() is not None


try:
    from supabase import create_client
except ImportError:  # pragma: no cover - optional unless DB_BACKEND=supabase
    create_client = None

_SUPABASE_CLIENT = None


def _get_supabase_client():
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is not None:
        return _SUPABASE_CLIENT

    if create_client is None:
        raise RuntimeError(
            "supabase package is not installed. Install it or set DB_BACKEND=sql."
        )

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env.")

    _SUPABASE_CLIENT = create_client(url, key)
    return _SUPABASE_CLIENT


def _row_to_appointment(row: dict) -> Appointments:
    scheduled_at = _parse_datetime(row.get("scheduled_at"))
    created_at = _parse_datetime(row.get("created_at"))
    return Appointments(
        id=row.get("id"),
        name=row.get("name"),
        phone_number=row.get("phone_number"),
        scheduled_at=scheduled_at or get_current_cairo_time(),
        completed=row.get("completed", False),
        created_at=created_at or get_current_cairo_time(),
    )


def _appointment_payload(ap: Appointments) -> dict:
    return {
        "name": ap.name,
        "phone_number": ap.phone_number,
        "scheduled_at": ap.scheduled_at.isoformat() if ap.scheduled_at else None,
        "completed": ap.completed,
        "created_at": ap.created_at.isoformat() if ap.created_at else None,
    }


def _resolve_slot(
    current_time: datetime,
    accept_suggested: bool,
    forced_slot: datetime | None,
) -> tuple[datetime | None, datetime | None]:
    if forced_slot is not None:
        return forced_slot, None

    today_available = is_workday(current_time) and not appoints_max_limit(current_time)
    if today_available:
        return _compute_slot(current_time), None

    suggested_date = get_nearest_appointment(current_time)
    suggested_slot = _compute_slot(suggested_date)
    if not accept_suggested:
        return None, suggested_slot
    return _compute_slot(suggested_date), None


def create_appointment(
    ap: Appointments, accept_suggested: bool = False, forced_slot: datetime | None = None
):
    current_time = get_current_cairo_time()
    appointment = appointment_exists(ap.phone_number)
    if appointment:
        message = "لديك موعد بالفعل في"
        return appointment, message, None

    scheduled_at, suggested_slot = _resolve_slot(current_time, accept_suggested, forced_slot)
    if scheduled_at is None and suggested_slot is not None:
        return None, "هل تريد حجز موعد في", suggested_slot

    ap.scheduled_at = scheduled_at

    if _use_supabase():
        client = _get_supabase_client()
        payload = _appointment_payload(ap)
        response = client.table(_supabase_table()).insert(payload).execute()
        _ensure_supabase_ok(response)
        message = "تم حجز موعدك بنجاح"
        return ap, message, None

    with Session(engine) as session:
        session.add(ap)
        session.commit()
        session.refresh(ap)
        message = "تم حجز موعدك بنجاح"
        return ap, message, None


def _get_latest_appointment_by_phone(
    phone_number: str, session: Session | None = None
) -> Appointments | None:
    if _use_supabase():
        client = _get_supabase_client()
        response = (
            client.table(_supabase_table())
            .select("*")
            .eq("phone_number", phone_number)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        _ensure_supabase_ok(response)
        rows = response.data or []
        if not rows:
            return None
        return _row_to_appointment(rows[0])

    if session is None:
        with Session(engine) as new_session:
            statement = (
                select(Appointments)
                .where(Appointments.phone_number == phone_number)
                .order_by(Appointments.created_at.desc())
            )
            return new_session.exec(statement).first()

    statement = (
        select(Appointments)
        .where(Appointments.phone_number == phone_number)
        .order_by(Appointments.created_at.desc())
    )
    return session.exec(statement).first()


def appointment_exists(ph_number: str) -> Appointments | None:
    # checking for existence and not completion of appointment the user requested for
    appointment = _get_latest_appointment_by_phone(ph_number)
    if not appointment or appointment.completed:
        return None
    return appointment


def cancel_appointment(ph_number: str) -> tuple[Appointments | None, str]:
    if _use_supabase():
        appointment = _get_latest_appointment_by_phone(ph_number)
        if not appointment:
            return None, "لا يوجد موعد مسجل لهذا الرقم"
        if appointment.completed:
            return appointment, "الموعد مكتمل بالفعل في"
        client = _get_supabase_client()
        delete_response = (
            client.table(_supabase_table()).delete().eq("id", appointment.id).execute()
        )
        _ensure_supabase_ok(delete_response)
        return appointment, "تم إلغاء موعدك بنجاح ليوم"

    with Session(engine) as session:
        appointment = _get_latest_appointment_by_phone(ph_number, session)
        if not appointment:
            return None, "لا يوجد موعد مسجل لهذا الرقم"
        if appointment.completed:
            return appointment, "الموعد مكتمل بالفعل في"
        session.delete(appointment)
        session.commit()
        return appointment, "تم إلغاء موعدك بنجاح ليوم"


def get_nearest_appointment(current_date: datetime) -> datetime:
    while True:
        # checking for nearest workday if the current is not one
        if not is_workday(current_date):
            current_date += timedelta(days=1)
            continue

        # skip days that reached max appointments
        if appoints_max_limit(current_date):
            current_date += timedelta(days=1)
            continue

        return current_date


def _get_day_bounds(appointment_date: date | datetime) -> tuple[datetime, datetime]:
    try:
        day = appointment_date.date()
        tzinfo = appointment_date.tzinfo
    except AttributeError:
        day = appointment_date
        tzinfo = None
    try:
        day_start = datetime.combine(day, datetime.min.time(), tzinfo=tzinfo)
    except Exception as exc:
        raise ValueError("appointment_date must be a date or datetime") from exc
    day_end = day_start + timedelta(days=1)
    return day_start, day_end


def ap_count(appointment_date: date | datetime) -> int:
    day_start, day_end = _get_day_bounds(appointment_date)
    if _use_supabase():
        client = _get_supabase_client()
        response = (
            client.table(_supabase_table())
            .select("id", count="exact")
            .gte("scheduled_at", day_start.isoformat())
            .lt("scheduled_at", day_end.isoformat())
            .execute()
        )
        _ensure_supabase_ok(response)
        if response.count is not None:
            return response.count
        return len(response.data or [])

    with Session(engine) as session:
        statement = select(Appointments).where(
            Appointments.scheduled_at >= day_start,
            Appointments.scheduled_at < day_end,
        )
        count = len(session.exec(statement).all())
    return count


def appoints_max_limit(
    appointment_date: date | datetime, max_daily: int = MAX_DAILY_APPOINTMENTS
) -> bool:
    return ap_count(appointment_date) >= max_daily


def get_appointment_by_phone(phone_number: str) -> Appointments | None:
    """Return the most recent appointment (completed or not) for a phone number."""
    return _get_latest_appointment_by_phone(phone_number)


def _get_taken_slots_in_range(start_dt: datetime, end_dt: datetime) -> set[datetime]:
    if _use_supabase():
        client = _get_supabase_client()
        response = (
            client.table(_supabase_table())
            .select("scheduled_at")
            .gte("scheduled_at", start_dt.isoformat())
            .lte("scheduled_at", end_dt.isoformat())
            .execute()
        )
        _ensure_supabase_ok(response)
        rows = response.data or []
        taken = set()
        for r in rows:
            dt = _parse_datetime(r.get("scheduled_at"))
            if dt:
                taken.add(dt)
        return taken

    with Session(engine) as session:
        statement = select(Appointments.scheduled_at).where(
            Appointments.scheduled_at >= start_dt,
            Appointments.scheduled_at <= end_dt
        )
        rows = session.exec(statement).all()
        return set(rows)


def get_slots_for_upcoming_days(days: int = 14) -> dict:
    """Return available time slots grouped by date for the next `days` calendar days."""
    now = get_current_cairo_time()
    cairo_tz = now.tzinfo
    
    end_date = now + timedelta(days=days + 1)
    taken_slots = _get_taken_slots_in_range(now, end_date)

    result = []
    current = now
    checked = 0

    while checked < days:
        if is_workday(current):
            day = current.date()
            day_slots = []
            slot_start = datetime(day.year, day.month, day.day, WORK_START_HOUR, 0, tzinfo=cairo_tz)
            for i in range(MAX_DAILY_APPOINTMENTS):
                candidate = slot_start + timedelta(minutes=i * _SLOT_MINUTES)
                if candidate > now and candidate not in taken_slots:
                    day_slots.append(candidate.isoformat())
            if day_slots:
                result.append({"date": day.isoformat(), "slots": day_slots})

        next_day = datetime(current.year, current.month, current.day, tzinfo=cairo_tz) + timedelta(days=1)
        current = next_day
        checked += 1

    return {"days": result}


def mark_past_appointments_completed() -> int:
    """Mark all appointments whose scheduled_at date is before today as completed.
    Returns the number of rows updated."""
    today = get_current_cairo_time().date()

    if _use_supabase():
        client = _get_supabase_client()
        today_start = datetime.combine(today, datetime.min.time()).isoformat()
        response = (
            client.table(_supabase_table())
            .update({"completed": True})
            .lt("scheduled_at", today_start)
            .eq("completed", False)
            .execute()
        )
        _ensure_supabase_ok(response)
        return len(response.data or [])

    with Session(engine) as session:
        today_start = datetime.combine(today, datetime.min.time())
        statement = select(Appointments).where(
            Appointments.scheduled_at < today_start,
            Appointments.completed == False,  # noqa: E712
        )
        rows = session.exec(statement).all()
        for row in rows:
            row.completed = True
            session.add(row)
        session.commit()
        return len(rows)


def get_all_appointments() -> list[Appointments]:
    if _use_supabase():
        client = _get_supabase_client()
        response = (
            client.table(_supabase_table())
            .select("*")
            .order("scheduled_at", desc=True)
            .execute()
        )
        _ensure_supabase_ok(response)
        rows = response.data or []
        return [_row_to_appointment(row) for row in rows]
    
    with Session(engine) as session:
        statement = select(Appointments).order_by(Appointments.scheduled_at.desc())
        return session.exec(statement).all()


def delete_appointment_by_id(ap_id: int) -> None:
    if _use_supabase():
        client = _get_supabase_client()
        response = client.table(_supabase_table()).delete().eq("id", ap_id).execute()
        _ensure_supabase_ok(response)
        return
    with Session(engine) as session:
        statement = select(Appointments).where(Appointments.id == ap_id)
        ap = session.exec(statement).first()
        if ap:
            session.delete(ap)
            session.commit()


def toggle_appointment_completed(ap_id: int) -> bool:
    if _use_supabase():
        client = _get_supabase_client()
        response = client.table(_supabase_table()).select("completed").eq("id", ap_id).execute()
        _ensure_supabase_ok(response)
        rows = response.data
        if not rows:
            return False
        new_val = not rows[0].get("completed", False)
        
        upd = client.table(_supabase_table()).update({"completed": new_val}).eq("id", ap_id).execute()
        _ensure_supabase_ok(upd)
        return new_val
        
    with Session(engine) as session:
        statement = select(Appointments).where(Appointments.id == ap_id)
        ap = session.exec(statement).first()
        if ap:
            ap.completed = not ap.completed
            session.add(ap)
            session.commit()
            return ap.completed
        return False


def get_admin_by_username(username: str):
    if _use_supabase():
        client = _get_supabase_client()
        response = client.table("admins").select("*").eq("username", username).limit(1).execute()
        _ensure_supabase_ok(response)
        rows = response.data or []
        return rows[0] if rows else None
        
    with Session(engine) as session:
        statement = select(Admins).where(Admins.username == username)
        return session.exec(statement).first()


def create_admin(username: str, hashed_password: str):
    if _use_supabase():
        client = _get_supabase_client()
        response = client.table("admins").insert({"username": username, "hashed_password": hashed_password}).execute()
        _ensure_supabase_ok(response)
        rows = response.data or []
        return rows[0] if rows else None

    # SQLModel fallback
    with Session(engine) as session:
        admin = Admins(username=username, hashed_password=hashed_password)
        session.add(admin)
        session.commit()
        session.refresh(admin)
        return admin


def update_admin_password(username: str, new_hashed_password: str) -> None:
    if _use_supabase():
        client = _get_supabase_client()
        response = client.table("admins").update({"hashed_password": new_hashed_password}).eq("username", username).execute()
        _ensure_supabase_ok(response)
        return
        
    with Session(engine) as session:
        statement = select(Admins).where(Admins.username == username)
        admin = session.exec(statement).first()
        if admin:
            admin.hashed_password = new_hashed_password
            session.add(admin)
            session.commit()
