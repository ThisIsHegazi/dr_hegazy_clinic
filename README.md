# Clinic Appointment Manager

A self-service web application that allows patients to book and cancel clinic appointments, with automatic scheduling, workday enforcement, and daily appointment limits.

---

## Features

- **Self-service booking** — Patients provide their name and phone number to book an appointment
- **Smart scheduling** — If today is unavailable (non-workday or fully booked), the system suggests the next open date
- **Daily cap enforcement** — Maximum 10 appointments per day; overflow is redirected to the next available slot
- **Working-day awareness** — Clinic operates Sunday–Thursday; Friday and Saturday are off
- **Duplicate prevention** — A patient cannot book while they have an active (non-completed) appointment
- **Appointment cancellation** — Patients can cancel using their phone number
- **Auto-completion** — Appointments with past dates are automatically marked as completed at Cairo midnight and on every startup
- **Admin Dashboard** — Secure dashboard to view, toggle, and delete appointments
- **Dual database backend** — Works with Supabase (default) or any PostgreSQL database via SQLModel / SQLAlchemy
- **Timezone-aware** — All scheduling logic runs on the **Africa/Cairo** timezone (UTC+2)

---

## Tech Stack

| Layer       | Technology                               |
|-------------|------------------------------------------|
| Backend     | [FastAPI](https://fastapi.tiangolo.com/) |
| ORM         | [SQLModel](https://sqlmodel.tiangolo.com/) (SQLAlchemy + Pydantic) |
| DB (cloud)  | [Supabase](https://supabase.com/) (PostgreSQL) |
| DB (local)  | PostgreSQL via `psycopg` (v3)            |
| Timezone    | `pytz` (Africa/Cairo)                    |
| Runtime     | Python 3.12+, managed with `uv`          |

---

## Project Structure

```
clinic_appointment_app/
├── backend/
│   ├── app/
│   │   ├── __init__.py        # Package marker
│   │   ├── main.py            # FastAPI app, API routes, startup & scheduler
│   │   ├── models.py          # Appointments SQLModel, DB engine setup
│   │   ├── db_operations.py   # All DB read/write logic (Supabase & SQL backends)
│   │   └── services.py        # Utility helpers: Cairo time, workday detection
│   ├── pyproject.toml         # Backend dependencies
│   └── uv.lock                # Backend lockfile
├── frontend/
│   ├── index.html         # Landing page (/)
│   ├── book/              # Booking page (/book)
│   ├── admin/             # Admin dashboard page (/admin)
│   └── admin/login/       # Admin login page (/admin/login)
│   └── static/            # Frontend static assets (CSS, JS)
└── documentation.md       # Full technical documentation
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- [`uv`](https://github.com/astral-sh/uv) (package manager)
- A Supabase project **or** a PostgreSQL database

### Installation

```bash
# Clone the repository
git clone https://github.com/ThisIsHegazi/clinic_app_appointments.git
cd clinic_app_appointments

# Install dependencies
cd backend
uv sync
```

### Configuration

Create a `.env` file in `backend/`:

**Using Supabase (default):**
```env
DB_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
SUPABASE_TABLE=appointments   # optional, defaults to "appointments"
```

**Using a direct PostgreSQL connection:**
```env
DB_BACKEND=sql
SUPABASE_DB_URL=postgresql://user:password@host:5432/dbname
```

**Frontend/Backend split (recommended):**
```env
# Backend only: allow your frontend origin(s)
CORS_ORIGINS=https://your-frontend-domain.com
```

### Running the Backend (API)

```bash
cd backend
uv run fastapi dev app/main.py
```

The API will be available at `http://localhost:8000`.

### Running the Frontend (Static)

Open `frontend/index.html` in a static server (or deploy `frontend/` as a static site).
Set `window.API_BASE_URL` in `frontend/static/js/config.js` to your backend URL.
Example:
```js
window.API_BASE_URL = "https://api.example.com";
```

---

## API Reference

### Patient Endpoints

| Method   | Endpoint                               | Description                                           |
|----------|----------------------------------------|-------------------------------------------------------|
| `GET`    | `/appointments/slots`                  | Returns available time slots for the upcoming days    |
| `GET`    | `/appointments/check/{phone_number}`   | Check if a phone number has an appointment            |
| `POST`   | `/appointments`                        | Book a new appointment                                |
| `DELETE` | `/appointments/{phone_number}`         | Cancel an existing appointment by phone number        |

### Admin Endpoints

| Method   | Endpoint                               | Description                                           |
|----------|----------------------------------------|-------------------------------------------------------|
| `POST`   | `/api/admin/token`                     | Admin login for access token                          |
| `GET`    | `/api/admin/appointments`              | Get all appointments                                  |
| `DELETE` | `/api/admin/appointments/{ap_id}`      | Delete appointment by ID                              |
| `PUT`    | `/api/admin/appointments/{ap_id}/toggle` | Toggle appointment completion status                  |
| `PUT`    | `/api/admin/password`                  | Change admin password                                 |

### Book an Appointment — `POST /appointments`

**Request body:**
```json
{
  "name": "Ahmed Mohamed",
  "phone_number": "01012345678"
}
```

**Responses:**
- `200 OK` — Appointment booked successfully
- `409 Conflict` — Duplicate active appointment, or no slot today (returns the next suggested date)

### Cancel an Appointment — `DELETE /appointments/{phone_number}`

**Responses:**
- `200 OK` — Appointment cancelled successfully
- `404 Not Found` — No active appointment for that number
- `409 Conflict` — Appointment is already marked as completed

---

## Business Rules

| Rule                    | Detail                                                              |
|-------------------------|---------------------------------------------------------------------|
| Working days            | Sunday, Monday, Tuesday, Wednesday, Thursday                       |
| Daily appointment limit | 10 per day                                                          |
| Duplicate booking       | Not allowed while a non-completed appointment exists               |
| Auto-completion         | Past appointments are marked complete at Cairo midnight & startup  |
| Timezone                | All logic uses **Africa/Cairo** (UTC+2)                            |

---
