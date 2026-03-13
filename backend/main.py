import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from config import settings
from database import Base, SessionLocal, engine
from models import AppSettings, Company, Contact, FundingRound, LaunchPost  # noqa: F401 — registers ORM tables
from routers import launches, scraper, settings as settings_router
from scheduler import shutdown_scheduler, start_scheduler

# ---------------------------------------------------------------------------
# Validate required API keys at import time so misconfiguration is caught
# immediately.  Calls sys.exit(1) if any required key is missing.
# ---------------------------------------------------------------------------
_REQUIRED_KEYS = [
    ("APIFY_API_TOKEN", settings.apify_api_token, "console.apify.com/account/integrations"),
    ("OPENAI_API_KEY",  settings.openai_api_key,  "platform.openai.com/api-keys"),
]
_missing = [(name, src) for name, val, src in _REQUIRED_KEYS if not val]
if _missing:
    for name, src in _missing:
        print(f"ERROR: Missing required API key {name} — get it from {src}", file=sys.stderr)
    sys.exit(1)
print("API keys OK", flush=True)

# ---------------------------------------------------------------------------
# DB initialisation — run at import time so it works even if Vercel's ASGI
# lifespan protocol is not fully supported.
# ---------------------------------------------------------------------------
try:
    print("Creating DB tables...", flush=True)
    Base.metadata.create_all(bind=engine)
    print("DB tables ready.", flush=True)
except Exception as exc:
    print(f"ERROR — DB create_all failed: {exc}", file=sys.stderr, flush=True)
    raise

try:
    _new_columns = [
        "ALTER TABLE companies ADD COLUMN linkedin_post_url TEXT",
        "ALTER TABLE companies ADD COLUMN linkedin_likes INTEGER DEFAULT 0",
        "ALTER TABLE companies ADD COLUMN linkedin_reposts INTEGER DEFAULT 0",
        "ALTER TABLE companies ADD COLUMN linkedin_fetched_at DATETIME",
        "ALTER TABLE companies ADD COLUMN funding_stage TEXT",
        "ALTER TABLE funding_rounds ADD COLUMN note TEXT",
        "ALTER TABLE launch_posts ADD COLUMN has_video INTEGER DEFAULT 0",
    ]
    with engine.connect() as _conn:
        for _sql in _new_columns:
            try:
                _conn.execute(text(_sql))
                _conn.commit()
            except Exception:
                pass  # column already exists
    print("Migrations done.", flush=True)
except Exception as exc:
    print(f"ERROR — migrations failed: {exc}", file=sys.stderr, flush=True)
    raise

try:
    _db = SessionLocal()
    try:
        if not _db.query(AppSettings).first():
            _db.add(AppSettings())
            _db.commit()
    finally:
        _db.close()
    print("Settings seeded.", flush=True)
except Exception as exc:
    print(f"ERROR — seed settings failed: {exc}", file=sys.stderr, flush=True)
    raise


# ---------------------------------------------------------------------------
# Scheduler — best-effort; not critical in serverless environments.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        start_scheduler()
    except Exception as exc:
        print(f"WARNING — scheduler failed to start (non-fatal): {exc}", flush=True)
    yield
    try:
        shutdown_scheduler()
    except Exception:
        pass


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
app.include_router(settings_router.router, prefix="/settings", tags=["settings"])


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
