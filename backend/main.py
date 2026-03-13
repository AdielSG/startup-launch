import io
import sys
from contextlib import asynccontextmanager

# Force UTF-8 on Windows consoles that default to cp1252, so box-drawing
# characters and emoji in startup messages render correctly.
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import Base, SessionLocal, engine
from models import AppSettings, Company, Contact, FundingRound, LaunchPost  # noqa: F401 — registers ORM tables
from routers import launches, scraper, settings
from scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    _check_api_keys()          # exits with code 1 if required keys are missing

    try:
        print("Creating DB tables...", flush=True)
        Base.metadata.create_all(bind=engine)
        print("DB tables ready.", flush=True)
    except Exception as exc:
        print(f"ERROR — Base.metadata.create_all failed: {exc}", flush=True)
        raise

    try:
        _run_migrations()
    except Exception as exc:
        print(f"ERROR — _run_migrations failed: {exc}", flush=True)
        raise

    try:
        _seed_default_settings()
    except Exception as exc:
        print(f"ERROR — _seed_default_settings failed: {exc}", flush=True)
        raise

    try:
        start_scheduler()
    except Exception as exc:
        # Scheduler is non-critical in serverless; log and continue.
        print(f"WARNING — scheduler failed to start (non-fatal): {exc}", flush=True)

    yield

    try:
        shutdown_scheduler()
    except Exception:
        pass


def _check_api_keys() -> None:
    """
    Validate required and optional API keys before the server accepts traffic.
    Prints a clear diagnostic table and calls sys.exit(1) if any required key
    is missing or empty.
    """
    from config import settings

    REQUIRED = [
        ("APIFY_API_TOKEN", settings.apify_api_token, "console.apify.com/account/integrations"),
        ("OPENAI_API_KEY",  settings.openai_api_key,  "platform.openai.com/api-keys"),
    ]
    OPTIONAL = []

    missing = [(name, source) for name, val, source in REQUIRED if not val]

    if missing:
        c1 = max(len(n) for n, _ in missing) + 2
        c2 = max(len(s) for _, s in missing) + 2
        top = f"┌{'─' * c1}┬{'─' * c2}┐"
        hdr = f"│ {'Key':<{c1 - 2}} │ {'Where to get it':<{c2 - 2}} │"
        div = f"├{'─' * c1}┼{'─' * c2}┤"
        bot = f"└{'─' * c1}┴{'─' * c2}┘"
        rows = "\n".join(f"│ {n:<{c1 - 2}} │ {s:<{c2 - 2}} │" for n, s in missing)
        print(
            f"\n❌  STARTUP FAILED — Missing required API keys:\n\n"
            f"{top}\n{hdr}\n{div}\n{rows}\n{bot}\n\n"
            f"Add these keys to your .env file and restart.\n",
            flush=True,
        )
        sys.exit(1)

    print("✅  All required API keys configured.", flush=True)

    for name, val, note in OPTIONAL:
        if not val:
            print(f"⚠️   {name} not set — {note}", flush=True)


def _run_migrations():
    """
    Add new columns to existing tables without Alembic.
    SQLite's ALTER TABLE ADD COLUMN is safe to re-run — we swallow
    the 'duplicate column' error so startup is always idempotent.
    """
    new_columns = [
        "ALTER TABLE companies ADD COLUMN linkedin_post_url TEXT",
        "ALTER TABLE companies ADD COLUMN linkedin_likes INTEGER DEFAULT 0",
        "ALTER TABLE companies ADD COLUMN linkedin_reposts INTEGER DEFAULT 0",
        "ALTER TABLE companies ADD COLUMN linkedin_fetched_at DATETIME",
        "ALTER TABLE companies ADD COLUMN funding_stage TEXT",
        "ALTER TABLE funding_rounds ADD COLUMN note TEXT",
        "ALTER TABLE launch_posts ADD COLUMN has_video INTEGER DEFAULT 0",
    ]
    with engine.connect() as conn:
        for sql in new_columns:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # column already exists — nothing to do


def _seed_default_settings():
    """Insert the default settings row if the table is empty."""
    db = SessionLocal()
    try:
        if not db.query(AppSettings).first():
            db.add(AppSettings())
            db.commit()
    finally:
        db.close()


app = FastAPI(
    title="Startup Launch Dashboard",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://frontend-five-sable-52.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(launches.router, prefix="/companies", tags=["companies"])
app.include_router(scraper.router, prefix="/scraper",   tags=["scraper"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
