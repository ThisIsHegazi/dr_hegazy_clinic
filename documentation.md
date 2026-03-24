**Overview**
Dr Hegazy Clinic is a self-service appointment booking system with a FastAPI backend and a static frontend. Patients can book, check, and cancel appointments. Admins can view all appointments, toggle completion, delete entries, and change the admin password.

**Architecture**
The system has three layers.
- Backend API in `backend/app` (FastAPI + SQLModel)
- Database via Supabase (PostgreSQL) or a direct PostgreSQL connection
- Static frontend in `frontend/` (HTML, CSS, JS)

**Quickstart**
Backend:
```bash
cd backend
uv sync
uv run fastapi dev app/main.py
```
Frontend:
- Serve `frontend/` with any static server
- Set `window.API_BASE_URL` in `frontend/static/js/config.js`

**Configuration**
Create `.env` inside `backend/`.

Environment variables:
| Variable | Default | Description |
|---|---|---|
| `DB_BACKEND` | `supabase` | `supabase` or `sql` |
| `SUPABASE_URL` | none | Supabase project URL |
| `SUPABASE_KEY` | none | Supabase anon or service key |
| `SUPABASE_TABLE` | `appointments` | Table name for appointments in Supabase |
| `SUPABASE_DB_URL` | none | PostgreSQL connection string when `DB_BACKEND=sql` |
| `DATABASE_URL` | none | Alternative to `SUPABASE_DB_URL` |
| `JWT_SECRET_KEY` | default hardcoded | Secret used to sign admin JWT tokens |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `CORS_ORIGIN_REGEX` | none | Regex for allowed origins |

Notes:
- If neither `CORS_ORIGINS` nor `CORS_ORIGIN_REGEX` are set, all origins are allowed.
- `JWT_SECRET_KEY` should be set in production.

**Database**
The backend supports two modes.
- Supabase: set `DB_BACKEND=supabase` and create tables manually.
- SQLModel: set `DB_BACKEND=sql` and the tables are created on startup.

Recommended SQL schema (Supabase or Postgres):
```sql
create table if not exists appointments (
  id bigserial primary key,
  name text not null,
  phone_number text not null,
  scheduled_at timestamptz not null,
  completed boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists admins (
  id bigserial primary key,
  username text unique not null,
  hashed_password text not null,
  created_at timestamptz not null default now()
);
```

**Data Model**
Appointments:
- `id` integer
- `name` string
- `phone_number` string
- `scheduled_at` ISO 8601 datetime
- `completed` boolean
- `created_at` ISO 8601 datetime

Admins:
- `id` integer
- `username` string
- `hashed_password` string
- `created_at` ISO 8601 datetime

**Scheduling**
- Workdays: Sunday through Thursday
- Working hours: 2:00 PM to 8:00 PM Cairo time
- Slot duration: 20 minutes
- Daily capacity: 18 appointments (derived from working hours and slot length)
- If today is not available, the API suggests the next available slot
- Past appointments are marked completed at Cairo midnight and on startup

**Authentication**
Admin endpoints require a bearer token.
- Login with `POST /api/admin/token` using form data (`username`, `password`)
- Tokens are JWTs signed with `JWT_SECRET_KEY`
- Default token expiry is 7 days

If you need to create the first admin user, insert into the `admins` table with a bcrypt hash.
Example hash generation:
```bash
python - <<'PY'
from passlib.context import CryptContext
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
print(pwd.hash("ChangeMe123"))
PY
```

**Patient Endpoints**
`GET /appointments/slots`
Query:
- `days` optional integer, default `14`
Response:
```json
{
  "days": [
    {
      "date": "2026-03-24",
      "slots": ["2026-03-24T14:00:00+02:00", "2026-03-24T14:20:00+02:00"]
    }
  ]
}
```
Notes:
- Only future slots are returned.
- Slots are grouped by date.

`GET /appointments/check/{phone_number}`
Response:
```json
{
  "name": "Ahmed Mohamed",
  "phone_number": "01012345678",
  "scheduled_at": "2026-03-24T14:00:00+02:00",
  "scheduled_at_label": "Arabic formatted label",
  "completed": false,
  "state": "confirmed"
}
```
Notes:
- Message fields and labels are returned in Arabic by default.

`POST /appointments`
Query:
- `accept_suggested` optional boolean, default `false`
- `preferred_slot` optional ISO 8601 datetime (must match an available slot)
Request body:
```json
{
  "name": "Ahmed Mohamed",
  "phone_number": "01012345678"
}
```
Success response:
```json
{
  "message": "Arabic success message"
}
```
Conflict response when next slot is suggested:
```json
{
  "detail": {
    "message": "Arabic suggestion message",
    "suggested_date": "2026-03-25T14:00:00+02:00"
  }
}
```
Conflict response when appointment already exists:
```json
{
  "detail": {
    "message": "Arabic duplicate message"
  }
}
```
Notes:
- The server always sets `scheduled_at` based on availability or suggestion.
- `preferred_slot` is only checked for collisions; it should come from `/appointments/slots`.

`DELETE /appointments/{phone_number}`
Success response:
```json
{
  "message": "Arabic cancel message"
}
```
Error responses:
- `404` if no active appointment exists
- `409` if the appointment is already completed

**Admin Endpoints**
All admin endpoints require `Authorization: Bearer <token>`.

`POST /api/admin/token`
Request content type: `application/x-www-form-urlencoded`
Form fields: `username`, `password`
Response:
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

`GET /api/admin/appointments`
Response:
```json
[
  {
    "id": 1,
    "name": "Ahmed Mohamed",
    "phone_number": "01012345678",
    "scheduled_at": "Arabic formatted label",
    "completed": false
  }
]
```

`PUT /api/admin/appointments/{ap_id}/toggle`
Response:
```json
{
  "message": "Arabic status message",
  "completed": true
}
```

`DELETE /api/admin/appointments/{ap_id}`
Response:
```json
{
  "message": "Arabic delete message"
}
```

`PUT /api/admin/password`
Request body:
```json
{
  "old_password": "OldPassword",
  "new_password": "NewPassword"
}
```
Response:
```json
{
  "message": "Arabic password change message"
}
```

**Error Format**
Errors are returned as JSON with either a string `detail` or an object `detail` containing a `message` field. Some conflicts also include `suggested_date`.

**Frontend Integration**
- Set `window.API_BASE_URL` in `frontend/static/js/config.js`
- `frontend/vercel.json` provides clean URLs for `/book`, `/admin`, and `/admin/login`
- Admin login token is stored in `localStorage` as `adminToken`

**Operational Notes**
- The scheduler runs at Cairo midnight and on startup to mark past appointments as completed.
- All time calculations use the Africa/Cairo timezone.
