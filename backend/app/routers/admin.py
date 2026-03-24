from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth import verify_credentials, create_access_token, get_current_admin
from app.db_operations import get_all_appointments, delete_appointment_by_id, toggle_appointment_completed

from app.services import format_arabic_datetime

router = APIRouter()

# --- API Endpoints ---

@router.post("/api/admin/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if not verify_credentials(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/api/admin/appointments")
def api_get_all_appointments(admin: str = Depends(get_current_admin)):
    appointments = get_all_appointments()
    result = []
    for ap in appointments:
        result.append({
            "id": ap.id,
            "name": ap.name,
            "phone_number": ap.phone_number,
            "scheduled_at": format_arabic_datetime(ap.scheduled_at) if ap.scheduled_at else "بدون موعد",
            "completed": ap.completed,
        })
    return result


@router.delete("/api/admin/appointments/{ap_id}")
def api_delete_appointment(ap_id: int, admin: str = Depends(get_current_admin)):
    try:
        delete_appointment_by_id(ap_id)
        return {"message": "تم حذف الموعد بنجاح"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/admin/appointments/{ap_id}/toggle")
def api_toggle_appointment(ap_id: int, admin: str = Depends(get_current_admin)):
    try:
        new_status = toggle_appointment_completed(ap_id)
        status_text = "مكتمل" if new_status else "مؤكد"
        return {"message": f"تم تغيير حالة الموعد إلى {status_text}", "completed": new_status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from pydantic import BaseModel
from app.auth import get_password_hash, verify_password
from app.db_operations import get_admin_by_username, update_admin_password

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

@router.put("/api/admin/password")
def api_change_password(req: PasswordChangeRequest, admin: str = Depends(get_current_admin)):
    admin_record = get_admin_by_username(admin)
    if not admin_record:
        raise HTTPException(status_code=404, detail="Admin not found")
        
    hashed = admin_record.get("hashed_password") if isinstance(admin_record, dict) else admin_record.hashed_password
    if not verify_password(req.old_password, hashed):
        raise HTTPException(status_code=400, detail="كلمة المرور القديمة غير صحيحة")
        
    new_hashed = get_password_hash(req.new_password)
    update_admin_password(admin, new_hashed)
    return {"message": "تم تغيير كلمة المرور بنجاح"}
