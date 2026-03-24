from datetime import datetime
import os
from sqlmodel import SQLModel, Field, create_engine
from app.services import get_current_cairo_time

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency for local dev
    load_dotenv = None

if load_dotenv:
    load_dotenv()


class Appointments(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    phone_number: str
    scheduled_at: datetime = Field(default_factory=get_current_cairo_time)
    completed: bool = False
    created_at: datetime = Field(default_factory=get_current_cairo_time)


class Admins(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=get_current_cairo_time)


def _build_db_url() -> str:
    if os.getenv("DB_BACKEND", "supabase").lower() == "supabase":
        return ""

    db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError(
            "Missing SUPABASE_DB_URL in .env (or DATABASE_URL). "
            "Add the Supabase Postgres connection string."
        )

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

    # Only add sslmode=require for remote (Supabase/cloud) connections,
    # not for local/Replit internal PostgreSQL (which uses localhost/127.0.0.1)
    if db_url.startswith("postgresql+psycopg://") and "sslmode=" not in db_url:
        is_local = any(
            host in db_url
            for host in ["localhost", "127.0.0.1", "@/", "host.docker.internal"]
        )
        if not is_local:
            separator = "&" if "?" in db_url else "?"
            db_url = f"{db_url}{separator}sslmode=require"

    return db_url


db_url = _build_db_url()
engine = create_engine(db_url) if db_url else None


def create_all_db_and_tables():
    if engine is None:
        raise RuntimeError(
            "DB_BACKEND is set to 'supabase'. Use the Supabase SQL editor or "
            "migrations to create tables."
        )
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    create_all_db_and_tables()
