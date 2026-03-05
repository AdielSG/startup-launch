# Startup Launch Dashboard

A full-stack dashboard that monitors YC W25 startup launches across X/Twitter and LinkedIn, tracks funding data, and surfaces poor performers for targeted outreach — complete with AI-drafted DMs.

---

## What This Does

The dashboard pulls all 167 YC Winter 2025 companies from the YCombinator directory and automatically enriches each one with launch tweet engagement (X/Twitter), LinkedIn post likes (via Apify), and funding totals (Crunchbase or YC standard deal). Companies that underperform against configurable engagement thresholds are flagged in red. For those, a single click generates a personalised outreach DM via OpenAI — ready to copy and send.

---

## Features

| Feature | Details |
|---|---|
| **YC W25 tracking** | 167 companies scraped from YC Algolia API with founder contacts |
| **X/Twitter engagement** | Launch tweet search using `from:{handle}` for company-scoped precision |
| **LinkedIn metrics** | Paste any LinkedIn post URL → Apify fetches likes + reposts in real time |
| **Funding data** | Real totals from Crunchbase Basic API; falls back to $500K YC standard deal |
| **Founder contacts** | LinkedIn profiles + X handles scraped from YC company pages |
| **Poor performer detection** | Configurable X and LinkedIn thresholds; red rows + status badge |
| **AI outreach DMs** | One-click personalised message generation via OpenAI gpt-4o-mini |
| **Auto-refresh** | APScheduler runs the full scrape pipeline every 6 hours |
| **Manual refresh** | "Refresh Data" button triggers an immediate scrape and shows a result toast |

---

## Tech Stack

| Layer | Tools |
|---|---|
| **Frontend** | React 18, Vite, Tailwind CSS, Recharts, Axios |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy, SQLite, APScheduler |
| **Scraping** | Tweepy (X API v2), Apify client (LinkedIn), httpx (YC/Crunchbase) |
| **AI** | OpenAI SDK — gpt-4o-mini |

---

## Prerequisites

- **Python 3.10+** — [python.org](https://python.org/downloads)
- **Node.js 18+** — [nodejs.org](https://nodejs.org)
- **Git**

---

## API Keys Required

The backend validates all keys at startup and prints a clear error table if any required key is missing. It will not start without them.

Create `backend/.env` (copy from `backend/.env.example`):

```bash
# REQUIRED — server will not start without these
TWITTER_BEARER_TOKEN=     # developer.x.com
APIFY_API_TOKEN=          # console.apify.com/account/integrations
OPENAI_API_KEY=           # platform.openai.com/api-keys

# OPTIONAL — funding shows $500K YC fallback if missing
CRUNCHBASE_API_KEY=       # data.crunchbase.com/docs/getting-started
```

| Key | Required | Where to get it | Free tier |
|---|---|---|---|
| `TWITTER_BEARER_TOKEN` | ✅ Yes | [developer.x.com](https://developer.x.com) → Projects & Apps → Keys and Tokens | 500 reads/month (Pay-Per-Use); dashboard stays under 450 with built-in budget guard |
| `APIFY_API_TOKEN` | ✅ Yes | [console.apify.com/account/integrations](https://console.apify.com/account/integrations) | $5 free monthly credit — sufficient for hundreds of LinkedIn lookups |
| `OPENAI_API_KEY` | ✅ Yes | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Pay-per-use; gpt-4o-mini costs ~$0.001 per DM |
| `CRUNCHBASE_API_KEY` | ⚠️ Optional | [data.crunchbase.com](https://data.crunchbase.com/docs/getting-started) | Basic tier — funding totals only (rounds require Enterprise) |

---

## Setup & Run

### 1. Clone the repo

```bash
git clone <repo-url>
cd startup-launch-dashboard
```

### 2. Backend setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Open .env and fill in your API keys (see table above)
```

Start the backend:

```bash
uvicorn main:app --reload
```

The server starts at **http://localhost:8000**. On first boot it will print either:

```
✅  All required API keys configured.
```

or a table listing exactly which keys are missing and where to get them. It will not start until all required keys are present.

> **API docs:** http://localhost:8000/docs

### 3. Frontend setup

Open a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**

### 4. Open the dashboard

Navigate to **http://localhost:5173** in your browser.

### 5. First run

The database ships with all 167 YC W25 companies already loaded (funding data, founder contacts, and any previously scraped engagement). To pull fresh data:

1. Click **Refresh Data** in the top-right of the sidebar
2. A loading banner appears — the scraper runs synchronously (takes ~2–3 minutes for 167 companies)
3. A toast notification shows the result: `Scraped X companies, found Y tweets`
4. The table updates automatically

---

## How It Works

The scraping pipeline runs in five sequential phases, triggered either manually or by the 6-hour scheduler:

```
Phase 1 — YC Algolia API
  └─ Fetches all W25 companies: name, domain, one-liner, funding stage

Phase 2 — YC Company Pages
  └─ Fetches each company's detail page for founder names,
     LinkedIn URLs, and X handles

Phase 3 — Database upsert
  └─ Writes companies + contacts; inserts $500K YC standard
     deal as a funding row if no Crunchbase data exists

Phase 4 — X/Twitter enrichment
  └─ For companies with a known X handle: searches from:{handle}
     For others: falls back to name + launch keywords
  └─ Saves the most-liked result per company

Phase 5 — Crunchbase enrichment  (requires API key)
  └─ Resolves company name → Crunchbase permalink via autocomplete
  └─ Fetches real funding total; replaces the $500K fallback row
```

LinkedIn metrics are fetched **on-demand** per company via the LinkedIn icon in each table row — not as part of the batch scrape.

---

## Dashboard Guide

| Element | What it means |
|---|---|
| **Red row** | Company is below one or more engagement thresholds |
| **Draft DM button** | Only appears on red rows — generates a personalised AI outreach message |
| **LinkedIn icon** (row) | Click to open a modal, paste the company's LinkedIn post URL, fetch likes via Apify |
| **Contact icons** (row) | LinkedIn logo → founder's LinkedIn profile; X logo → founder's X profile |
| **Stage badge** | `Early` / `Growth` / `Public` — from YC company data |
| **Settings panel** | Gear icon → adjust X likes and LinkedIn likes thresholds |
| **Refresh Data** | Triggers an immediate full scrape; spinner shows while running |

### Performance thresholds

Configured in the Settings panel (gear icon, top-right of sidebar). Defaults:

| Metric | Default | Effect when below |
|---|---|---|
| X likes | 200 | Row turns red, "Draft DM" button appears |
| LinkedIn likes | 50 | Row turns red, "Draft DM" button appears |

A company is a poor performer if **either** metric is below its threshold.

---

## Project Structure

```
startup-launch-dashboard/
├── backend/
│   ├── main.py              # FastAPI app, lifespan, startup key validation
│   ├── config.py            # Pydantic-settings: reads .env
│   ├── database.py          # SQLite engine + session factory
│   ├── models.py            # ORM: Company, FundingRound, LaunchPost, Contact, AppSettings
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── scheduler.py         # APScheduler 6h auto-scrape
│   ├── routers/
│   │   ├── launches.py      # /companies CRUD + LinkedIn + DM endpoints
│   │   ├── scraper.py       # POST /scraper/run
│   │   └── settings.py      # GET/PATCH /settings
│   ├── scrapers/
│   │   ├── yc_scraper.py    # Main pipeline (phases 1–5)
│   │   ├── twitter.py       # Tweepy search + budget guard
│   │   ├── crunchbase.py    # Crunchbase Basic API
│   │   └── linkedin_scraper.py  # Apify actor client
│   └── services/
│       └── dm_drafter.py    # OpenAI gpt-4o-mini DM generation
├── frontend/
│   └── src/
│       ├── App.jsx          # Root: data loading, refresh, toast
│       ├── api/companies.js # Axios API client
│       └── components/
│           ├── LaunchTable.jsx   # Main data table
│           ├── Sidebar.jsx       # Filters, refresh button, stats
│           ├── DmModal.jsx       # AI DM generation modal
│           ├── LinkedInModal.jsx # Apify LinkedIn fetch modal
│           ├── FilterBar.jsx     # Batch / stage filters
│           └── SettingsPanel.jsx # Threshold configuration
├── .env.example
└── README.md
```

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/companies/` | List all companies (supports `?yc_batch=W25`) |
| `GET` | `/companies/{id}` | Get single company with funding + contacts |
| `POST` | `/scraper/run` | Trigger full scrape (synchronous, ~2–3 min) |
| `POST` | `/companies/{id}/linkedin` | Fetch LinkedIn post metrics via Apify |
| `POST` | `/companies/{id}/draft-dm` | Generate outreach DM via OpenAI |
| `GET` | `/settings/` | Get performance thresholds |
| `PATCH` | `/settings/` | Update thresholds |

Interactive docs with request/response schemas: **http://localhost:8000/docs**
