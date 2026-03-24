# Dr Hegazy Clinic

Self-service clinic appointment booking for Dr Hegazy Clinic. Patients can book, check, and cancel appointments, while admins manage the schedule through a secure dashboard. The backend is FastAPI + SQLModel, and the frontend is a static HTML/CSS/JS site.

---

## Features

- Self-service booking with name and phone number
- 20-minute slots from 2:00 PM to 8:00 PM Cairo time (18 slots per workday)
- Smart scheduling with next available suggestions
- Workday enforcement (Sunday through Thursday)
- Duplicate prevention for active appointments
- Appointment cancellation by phone number
- Auto-completion of past appointments at Cairo midnight and on startup
- Admin dashboard to view, toggle, delete, and change passwords
- Supabase or PostgreSQL support
- Timezone-aware (Africa/Cairo)

---

## Tech Stack

| Layer       | Technology                               |
|-------------|------------------------------------------|
| Backend     | FastAPI                                  |
| ORM         | SQLModel (SQLAlchemy + Pydantic)         |
| DB (cloud)  | Supabase (PostgreSQL)                    |
| DB (local)  | PostgreSQL via psycopg (v3)              |
| Timezone    | pytz (Africa/Cairo)                      |
| Runtime     | Python 3.12+, managed with uv            |
| Frontend    | Static HTML, CSS, and JavaScript         |

---

## Project Structure

```
dr_hegazy_clinic/
├── backend/
│   ├── app/
│   │   ├── __init__.py        # Package marker
│   │   ├── main.py            # FastAPI app, startup, scheduler
│   │   ├── auth.py            # Admin auth and JWT helpers
│   │   ├── models.py          # SQLModel definitions and DB engine
│   │   ├── db_operations.py   # DB access for appointments/admins
│   │   ├── services.py        # Time, slots, and workday helpers
│   │   └── routers/
│   │       ├── appointments.py
│   │       └── admin.py
│   ├── pyproject.toml         # Backend dependencies
│   └── uv.lock                # Backend lockfile
├── frontend/
│   ├── index.html             # Landing page (/)
│   ├── book/                  # Booking page (/book)
│   ├── admin/                 # Admin dashboard (/admin)
│   ├── static/                # CSS/JS/assets
│   └── vercel.json            # Optional SPA routing rewrites
└── documentation.md           # Full app and API documentation
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- uv (package manager)
- A Supabase project or a PostgreSQL database

### Installation

```bash
# Clone the repository
git clone https://github.com/ThisIsHegazi/dr_hegazy_clinic.git
cd dr_hegazy_clinic

# Install backend dependencies
cd backend
uv sync
```

### Configuration

Create a `.env` file in `backend/`.

**Supabase (default):**
```env
DB_BACKEND=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
SUPABASE_TABLE=appointments
JWT_SECRET_KEY=replace-with-a-strong-secret
```

**PostgreSQL (SQLModel backend):**
```env
DB_BACKEND=sql
SUPABASE_DB_URL=postgresql://user:password@host:5432/dbname
JWT_SECRET_KEY=replace-with-a-strong-secret
```

**CORS (optional):**
```env
CORS_ORIGINS=https://your-frontend-domain.com
# or
CORS_ORIGIN_REGEX=https://.*\.yourdomain\.com
```

### Running the Backend

```bash
cd backend
uv run fastapi dev app/main.py
```

The API will be available at `http://localhost:8000`.

### Running the Frontend

Serve the `frontend/` folder as a static site. Set the API base URL in `frontend/static/js/config.js`:

```js
window.API_BASE_URL = "https://api.example.com";
```

---

## API Summary

### Patient Endpoints

| Method   | Endpoint                               | Description                                        |
|----------|----------------------------------------|----------------------------------------------------|
| GET      | `/appointments/slots`                  | Available slots for upcoming days                  |
| GET      | `/appointments/check/{phone_number}`   | Check a phone number appointment status            |
| POST     | `/appointments`                        | Book a new appointment                             |
| DELETE   | `/appointments/{phone_number}`         | Cancel an existing appointment by phone number     |

### Admin Endpoints

| Method   | Endpoint                                 | Description                            |
|----------|------------------------------------------|----------------------------------------|
| POST     | `/api/admin/token`                       | Admin login for access token           |
| GET      | `/api/admin/appointments`                | Get all appointments                   |
| DELETE   | `/api/admin/appointments/{ap_id}`        | Delete appointment by ID               |
| PUT      | `/api/admin/appointments/{ap_id}/toggle` | Toggle appointment completion status   |
| PUT      | `/api/admin/password`                    | Change admin password                  |

---

## Documentation

See `documentation.md` for full setup, database schema, and detailed API documentation.

---

## Business Rules

| Rule                    | Detail                                                                 |
|-------------------------|------------------------------------------------------------------------|
| Working days            | Sunday, Monday, Tuesday, Wednesday, Thursday                           |
| Working hours           | 2:00 PM to 8:00 PM (Cairo time)                                         |
| Slot duration           | 20 minutes                                                             |
| Daily appointment limit | 18 per day (derived from work hours and slot duration)                  |
| Duplicate booking       | Not allowed while a non-completed appointment exists                   |
| Auto-completion         | Past appointments are marked complete at Cairo midnight                 |
| Timezone                | All logic uses Africa/Cairo                                             |
