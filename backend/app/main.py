import asyncio
import logging
import os
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db_operations import mark_past_appointments_completed
from app.models import create_all_db_and_tables, engine
from app.services import get_current_cairo_time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.routers.admin import router as admin_router
from app.routers.appointments import router as appointments_router

app = FastAPI()

app.include_router(admin_router)
app.include_router(appointments_router)

def _normalize_origin(origin: str) -> str:
    origin = origin.strip()
    if not origin or origin == "*":
        return origin

    if "://" not in origin:
        return origin.rstrip("/")

    try:
        parts = urlsplit(origin)
    except ValueError:
        return origin.rstrip("/")

    if parts.scheme and parts.netloc:
        return f"{parts.scheme}://{parts.netloc}"

    return origin.rstrip("/")


def _get_cors_config() -> tuple[list[str], str | None]:
    raw_origins = os.getenv("CORS_ORIGINS", "").strip()
    raw_regex = os.getenv("CORS_ORIGIN_REGEX", "").strip()

    origins = []
    if raw_origins:
        for origin in raw_origins.split(","):
            normalized = _normalize_origin(origin)
            if normalized:
                origins.append(normalized)

    # De-duplicate while preserving order
    seen = set()
    origins = [o for o in origins if not (o in seen or seen.add(o))]
    origin_regex = raw_regex or None

    if not origins and not origin_regex:
        return ["*"], None

    return origins, origin_regex

cors_origins, cors_origin_regex = _get_cors_config()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _seconds_until_next_cairo_midnight() -> float:
    """Return the number of seconds from now until the next midnight in Cairo time."""
    now = get_current_cairo_time()
    tomorrow_midnight = datetime(
        now.year, now.month, now.day, tzinfo=now.tzinfo
    ) + timedelta(days=1)
    return (tomorrow_midnight - now).total_seconds()


async def _daily_completion_scheduler():
    """Background task: at each Cairo midnight, mark past appointments as completed."""
    while True:
        wait_seconds = _seconds_until_next_cairo_midnight()
        logger.info("Daily scheduler: next run in %.0f seconds (at Cairo midnight).", wait_seconds)
        await asyncio.sleep(wait_seconds)
        try:
            updated = mark_past_appointments_completed()
            logger.info("Daily scheduler: marked %d appointment(s) as completed.", updated)
        except Exception as exc:
            logger.error("Daily scheduler error: %s", exc)


@app.on_event("startup")
async def on_startup():
    if engine is not None:
        create_all_db_and_tables()

    # Run once on startup to catch any appointments missed during downtime
    try:
        updated = mark_past_appointments_completed()
        logger.info("Startup: marked %d past appointment(s) as completed.", updated)
    except Exception as exc:
        logger.error("Startup completion check error: %s", exc)

    # Launch the daily midnight scheduler as a background task
    asyncio.create_task(_daily_completion_scheduler())
