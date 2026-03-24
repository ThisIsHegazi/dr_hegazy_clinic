import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.db_operations import (
    cancel_appointment,
    create_appointment,
    get_appointment_by_phone,
    get_slots_for_upcoming_days,
)
from app.models import Appointments
from app.services import format_arabic_datetime

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/appointments/slots")
def available_slots(days: int = 14):
    """Return available time slots for the next N calendar days."""
    try:
        return get_slots_for_upcoming_days(days)
    except Exception as exc:
        logger.error("Error fetching slots: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/appointments/check/{phone_number}")
def check_appointment(phone_number: str):
    """Check if a phone number has an appointment and return its details."""
    appointment = get_appointment_by_phone(phone_number)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "لا يوجد موعد مسجل لهذا الرقم"},
        )
    state = "مكتمل" if appointment.completed else "مؤكد"
    return {
        "name": appointment.name,
        "phone_number": appointment.phone_number,
        "scheduled_at": appointment.scheduled_at.isoformat() if appointment.scheduled_at else None,
        "scheduled_at_label": format_arabic_datetime(appointment.scheduled_at) if appointment.scheduled_at else None,
        "completed": appointment.completed,
        "state": state,
    }


@router.post("/appointments")
def get_appointment(ap: Appointments, accept_suggested: bool = False, preferred_slot: str | None = None):
    from app.db_operations import _slot_taken
    forced = None
    if preferred_slot:
        try:
            parsed = datetime.fromisoformat(preferred_slot)
            if not _slot_taken(parsed):
                forced = parsed
        except Exception as exc:
            logger.warning("Invalid preferred_slot %s: %s", preferred_slot, exc)

    appointment, message, suggested_date = create_appointment(
        ap, accept_suggested=accept_suggested, forced_slot=forced
    )
    if not appointment:
        detail: dict = {"message": message}
        if suggested_date:
            detail["message"] = f"{message} {format_arabic_datetime(suggested_date)}"
            detail["suggested_date"] = suggested_date
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    if message == "لديك موعد بالفعل في":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": f"{message} {format_arabic_datetime(appointment.scheduled_at)}"},
        )
    return {"message": f"{message} — {format_arabic_datetime(appointment.scheduled_at)}"}


@router.delete("/appointments/{phone_number}")
def delete_appointment(phone_number: str):
    appointment, message = cancel_appointment(phone_number)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"message": message}
        )
    if appointment.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": f"{message} {format_arabic_datetime(appointment.scheduled_at)}"},
        )
    return {"message": f"{message} — {format_arabic_datetime(appointment.scheduled_at)}"}
