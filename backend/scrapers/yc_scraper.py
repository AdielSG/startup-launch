"""
yc_scraper.py — Scrape YC company directory.

Data sources
────────────
1. Algolia (45BWZJ1SGC / YCCompany_production)
   Public, read-only key embedded in ycombinator.com. Used for batch-filtered
   company listings with full pagination.

2. ycombinator.com/companies/{slug}
   Company detail page. Founders + year_founded are embedded in the
   Inertia.js `data-page` JSON attribute — no JavaScript engine needed,
   plain httpx fetch is enough.

Rate limiting
─────────────
Default: 1 request / second (configurable via `rps` param).
A single RateLimiter is shared across all request types so Algolia calls
and HTML fetches are both counted.

Retries
───────
Each HTTP call is wrapped in the project-wide `with_backoff` helper
(base.py): 3 retries, exponential delay + jitter.

Database
────────
Upsert on `companies.name`: safe to re-run. Founders are stored in
`contacts` (linkedin_url + x_handle). Founded year written to company row.

CLI usage
─────────
    python yc_scraper.py                 # W25, all pages, save to DB
    python yc_scraper.py --batch S24     # different batch
    python yc_scraper.py --pages 1       # first page only (20 companies)
    python yc_scraper.py --no-founders   # skip founder fetch (faster)
    python yc_scraper.py --dry-run       # no DB writes
"""

import argparse
import asyncio
import json
import re
import sys
import time
from html import unescape
from typing import Optional
from urllib.parse import urlparse

import httpx

# ── Algolia config ────────────────────────────────────────────────────────────
# Public read-only key, restricted to YCCompany indices. Embedded in
# ycombinator.com/companies page source — not a secret.
_ALGOLIA_APP_ID = "45BWZJ1SGC"
_ALGOLIA_API_KEY = (
    "ZjA3NWMwMmNhMzEwZmMxOThkZDlkMjFmNDAwNTNjNjdkZjdhNWJkOWRjMThiODQwMjUyZTVkYj"
    "A4YjFlMmU2YnJlc3RyaWN0SW5kaWNlcz0lNUIlMjJZQ0NvbXBhbnlfcHJvZHVjdGlvbiUyMiUy"
    "QyUyMllDQ29tcGFueV9CeV9MYXVuY2hfRGF0ZV9wcm9kdWN0aW9uJTIyJTVEJnRhZ0ZpbHRlcn"
    "M9JTVCJTIyeWNkY19wdWJsaWMlMjIlNUQmYW5hbHl0aWNzVGFncz0lNUIlMjJ5Y2RjJTIyJTVE"
)
_ALGOLIA_ENDPOINT = (
    f"https://{_ALGOLIA_APP_ID.lower()}-dsn.algolia.net"
    "/1/indexes/YCCompany_production/query"
)
_ALGOLIA_HEADERS = {
    "x-algolia-application-id": _ALGOLIA_APP_ID,
    "x-algolia-api-key": _ALGOLIA_API_KEY,
    "Content-Type": "application/json",
}
_ALGOLIA_ATTRIBUTES = [
    "name", "slug", "website", "one_liner", "long_description",
    "batch", "team_size", "tags", "status", "stage",
]

_YC_COMPANY_URL = "https://www.ycombinator.com/companies/{slug}"
_HITS_PER_PAGE = 20
DEFAULT_BATCH = "W25"


# ── Batch format helpers ───────────────────────────────────────────────────────

def _to_algolia_batch(batch: str) -> str:
    """'W25' → 'Winter 2025', 'S24' → 'Summer 2024'. Passes through full names."""
    m = re.match(r"^([WS])(\d{2})$", batch.strip(), re.IGNORECASE)
    if not m:
        return batch
    season = "Winter" if m.group(1).upper() == "W" else "Summer"
    return f"{season} {2000 + int(m.group(2))}"


def _to_short_batch(batch_full: str) -> str:
    """'Winter 2025' → 'W25'."""
    m = re.match(r"^(Winter|Summer)\s+(\d{4})$", batch_full, re.IGNORECASE)
    if not m:
        return batch_full
    prefix = "W" if m.group(1).lower() == "winter" else "S"
    return f"{prefix}{m.group(2)[2:]}"


# ── Field extractors ──────────────────────────────────────────────────────────

def _extract_domain(website: Optional[str]) -> Optional[str]:
    if not website:
        return None
    try:
        host = urlparse(website).netloc or urlparse(website).path
        return host.removeprefix("www.") or None
    except Exception:
        return None


def _extract_x_handle(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    m = re.match(r"https?://(?:twitter\.com|x\.com)/([^/?#]+)", url)
    return m.group(1) if m else None


# ── Rate limiter ──────────────────────────────────────────────────────────────

class RateLimiter:
    """Ensures at most `rps` HTTP requests per second across all callers."""

    def __init__(self, rps: float = 1.0):
        self._interval = 1.0 / rps
        self._last = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            gap = self._interval - (now - self._last)
            if gap > 0:
                await asyncio.sleep(gap)
            self._last = time.monotonic()


# ── HTTP helpers ──────────────────────────────────────────────────────────────

async def _fetch_algolia_page(
    batch_full: str,
    page: int,
    client: httpx.AsyncClient,
    limiter: RateLimiter,
) -> dict:
    """Fetch one paginated result page from the Algolia index."""
    await limiter.acquire()
    payload = {
        "query": "",
        "facetFilters": [[f"batch:{batch_full}"]],
        "page": page,
        "hitsPerPage": _HITS_PER_PAGE,
        "attributesToRetrieve": _ALGOLIA_ATTRIBUTES,
    }
    for attempt in range(4):
        try:
            resp = await client.post(
                _ALGOLIA_ENDPOINT, json=payload, headers=_ALGOLIA_HEADERS
            )
            resp.raise_for_status()
            return resp.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            if attempt == 3:
                raise
            wait = (2 ** attempt) + 0.5
            print(f"\n    [retry] algolia page {page}, attempt {attempt + 2} in {wait:.1f}s ({exc})")
            await asyncio.sleep(wait)
    return {}  # unreachable


async def _fetch_founders(
    slug: str,
    client: httpx.AsyncClient,
    limiter: RateLimiter,
) -> tuple[list[dict], Optional[int]]:
    """
    Fetch the YC company detail page and extract:
      - founders list (full_name, title, bio, linkedin_url, x_handle)
      - year_founded

    Data lives in the Inertia.js `data-page` attribute as HTML-entity-encoded JSON.
    No JavaScript rendering needed.
    """
    await limiter.acquire()
    url = _YC_COMPANY_URL.format(slug=slug)

    for attempt in range(4):
        try:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; startup-dashboard/1.0)",
                    "Accept": "text/html",
                },
            )
            resp.raise_for_status()
            break
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return [], None          # company has no public page
            if attempt == 3:
                print(f"\n    [warn] {slug}: HTTP {exc.response.status_code} after 4 attempts")
                return [], None
            wait = (2 ** attempt) + 0.5
            await asyncio.sleep(wait)
        except httpx.RequestError as exc:
            if attempt == 3:
                print(f"\n    [warn] {slug}: request error {exc}")
                return [], None
            await asyncio.sleep((2 ** attempt) + 0.5)

    m = re.search(r'data-page="({.*?})"', resp.text, re.DOTALL)
    if not m:
        return [], None

    try:
        data = json.loads(unescape(m.group(1)))
    except json.JSONDecodeError:
        return [], None

    company_props = data.get("props", {}).get("company", {})
    year_founded: Optional[int] = company_props.get("year_founded")

    founders: list[dict] = []
    for f in company_props.get("founders", []):
        founders.append({
            "full_name": f.get("full_name"),
            "title": f.get("title"),
            "bio": f.get("founder_bio"),
            "linkedin_url": f.get("linkedin_url"),
            "twitter_url": f.get("twitter_url"),
            "x_handle": _extract_x_handle(f.get("twitter_url")),
        })

    return founders, year_founded


# ── Database helpers ──────────────────────────────────────────────────────────

def _upsert_to_db(companies: list[dict]) -> int:
    """
    Upsert a list of company dicts into SQLite.
    Each dict may contain a '_founders' key with a list of founder dicts.
    Returns the number of rows upserted.
    """
    from database import Base, SessionLocal, engine
    from models import AppSettings, Company, Contact, FundingRound

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    upserted = 0

    try:
        # Ensure settings row exists
        if not db.query(AppSettings).first():
            db.add(AppSettings())

        for row in companies:
            founders = row.pop("_founders", [])
            slug = row.pop("slug", None)  # not stored in Company model

            existing = db.query(Company).filter(Company.name == row["name"]).first()
            if existing:
                for field, val in row.items():
                    if val is not None:
                        setattr(existing, field, val)
                company = existing
            else:
                company = Company(**{k: v for k, v in row.items() if v is not None})
                db.add(company)

            db.flush()

            # Upsert founders → contacts table
            for founder in founders:
                li_url = founder.get("linkedin_url")
                existing_contact = (
                    db.query(Contact)
                    .filter(
                        Contact.company_id == company.id,
                        Contact.linkedin_url == li_url,
                    )
                    .first()
                    if li_url
                    else None
                )
                if existing_contact:
                    existing_contact.x_handle = (
                        founder.get("x_handle") or existing_contact.x_handle
                    )
                else:
                    db.add(
                        Contact(
                            company_id=company.id,
                            linkedin_url=li_url,
                            x_handle=founder.get("x_handle"),
                        )
                    )

            # Insert YC standard deal funding round (once per company)
            yc_deal_exists = (
                db.query(FundingRound)
                .filter(
                    FundingRound.company_id == company.id,
                    FundingRound.source == "yc",
                )
                .first()
            )
            if not yc_deal_exists:
                batch = row.get("yc_batch") or company.yc_batch or "YC"
                db.add(FundingRound(
                    company_id = company.id,
                    amount     = 500_000,
                    round_type = "pre-seed",
                    source     = "yc",
                    note       = f"YC {batch} standard deal",
                ))

            upserted += 1

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return upserted


# ── Twitter enrichment ────────────────────────────────────────────────────────

async def _enrich_with_twitter(companies: list[dict]) -> int:
    """
    For each company in the list, search for its best launch tweet and upsert
    the result into launch_posts (platform='twitter').

    Skips gracefully when:
      - TWITTER_BEARER_TOKEN is not configured
      - The monthly budget guard is reached
      - Any other per-company error occurs

    Returns the number of tweets saved.
    """
    from config import settings
    if not settings.twitter_bearer_token:
        print("  [twitter] TWITTER_BEARER_TOKEN not set — skipping enrichment")
        return 0

    try:
        from scrapers.twitter import find_and_save, TwitterBudgetError
    except ImportError:
        from twitter import find_and_save, TwitterBudgetError  # CLI fallback

    from database import SessionLocal
    from models import Company as _Company

    db = SessionLocal()
    saved = 0
    try:
        print(f"  [twitter] enriching {len(companies)} companies ...")
        for company_data in companies:
            name   = company_data.get("name")
            domain = company_data.get("domain")
            if not name:
                continue
            row = db.query(_Company).filter(_Company.name == name).first()
            if not row:
                continue
            try:
                # Prefer the company's own X handle for a precise from: search
                x_handle = next(
                    (c.x_handle for c in row.contacts if c.x_handle), None
                )
                tweet = await find_and_save(name, row.id, domain, x_handle=x_handle)
                if tweet:
                    print(f"  [twitter] {name}: {tweet['likes']:,} likes — {tweet['url']}")
                    saved += 1
                else:
                    print(f"  [twitter] {name}: no tweet found")
            except TwitterBudgetError as exc:
                print(f"  [twitter] Budget guard reached: {exc}")
                break
            except Exception as exc:
                print(f"  [twitter] {name}: error — {exc}")
    finally:
        db.close()

    print(f"  [twitter] {saved} tweet(s) saved")
    return saved


# ── Crunchbase enrichment ─────────────────────────────────────────────────────

async def _enrich_with_crunchbase(companies: list[dict]) -> int:
    """
    For each company, resolve a Crunchbase permalink then fetch funding totals.

    If funding_total > 0:
      - Delete the $500 K YC placeholder row (source='yc')
      - Insert a new FundingRound row with the real total (source='crunchbase')
    Otherwise the YC placeholder is kept as fallback.

    Returns the number of companies enriched with real funding data.
    """
    from config import settings
    if not settings.crunchbase_api_key:
        print("  [crunchbase] CRUNCHBASE_API_KEY not set — skipping enrichment")
        return 0

    try:
        from scrapers.crunchbase import get_permalink, get_funding
    except ImportError:
        from crunchbase import get_permalink, get_funding  # CLI fallback

    from database import SessionLocal
    from models import Company as _Company, FundingRound

    db = SessionLocal()
    enriched = 0
    try:
        print(f"  [crunchbase] enriching {len(companies)} companies ...")
        for company_data in companies:
            name   = company_data.get("name")
            domain = company_data.get("domain")
            if not name:
                continue
            row = db.query(_Company).filter(_Company.name == name).first()
            if not row:
                continue

            try:
                permalink = await get_permalink(name, domain)
                if not permalink:
                    print(f"  [crunchbase] {name}: no permalink")
                    continue

                funding = await get_funding(permalink)
                total = (funding or {}).get("funding_total") or 0
                if total <= 0:
                    print(f"  [crunchbase] {name}: no funding data, keeping YC fallback")
                    continue

                # Replace YC placeholder with real Crunchbase total
                db.query(FundingRound).filter(
                    FundingRound.company_id == row.id,
                    FundingRound.source     == "yc",
                ).delete()

                num_rounds = funding.get("num_funding_rounds") or "?"
                db.add(FundingRound(
                    company_id = row.id,
                    amount     = total,
                    round_type = funding.get("last_funding_type"),
                    source     = "crunchbase",
                    note       = f"Total raised per Crunchbase ({num_rounds} round(s))",
                ))

                # Backfill description if company has none
                if funding.get("short_description") and not row.description:
                    row.description = funding["short_description"]

                db.commit()
                print(
                    f"  [crunchbase] {name}: ${total:,.0f}"
                    f"  ({funding.get('last_funding_type') or 'unknown'},"
                    f" {num_rounds} round(s))"
                )
                enriched += 1

            except Exception as exc:
                db.rollback()
                print(f"  [crunchbase] {name}: error — {exc}")

    finally:
        db.close()

    kept = len(companies) - enriched
    print(f"  [crunchbase] {enriched} enriched with real data, {kept} kept YC fallback")
    return enriched


# ── Main scraper ──────────────────────────────────────────────────────────────

async def scrape_yc_batch(
    batch: str = DEFAULT_BATCH,
    max_pages: Optional[int] = None,
    fetch_founders: bool = True,
    save_to_db: bool = True,
    rps: float = 1.0,
) -> list[dict]:
    """
    Scrape all YC companies for a given batch.

    Args:
        batch:          'W25', 'S24', 'W24' … or full name 'Winter 2025'
        max_pages:      Cap page count (None = all pages)
        fetch_founders: Fetch per-company detail page for founders
        save_to_db:     Upsert results into SQLite when True
        rps:            Max requests per second (default 1.0)

    Returns:
        List of company dicts (includes '_founders' key).
    """
    batch_full = _to_algolia_batch(batch)
    batch_short = _to_short_batch(batch_full)
    limiter = RateLimiter(rps=rps)
    results: list[dict] = []

    print(f"[yc_scraper] batch={batch_full} ({batch_short})  rps={rps}")

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:

        # ── Phase 1: company listing via Algolia ──────────────────────────────
        page = 0
        nb_pages: Optional[int] = None

        while True:
            if max_pages is not None and page >= max_pages:
                break

            label = f"{page + 1}/{nb_pages}" if nb_pages else f"{page + 1}/??"
            print(f"  [algolia] page {label}", end="  ", flush=True)

            data = await _fetch_algolia_page(batch_full, page, client, limiter)
            hits = data.get("hits", [])
            nb_pages = data.get("nbPages", 1)

            print(f"{len(hits)} companies  (total={data.get('nbHits', '?')})")

            for hit in hits:
                results.append({
                    "name":          hit.get("name"),
                    "slug":          hit.get("slug"),   # used for founder fetch, not stored
                    "domain":        _extract_domain(hit.get("website")),
                    "description":   hit.get("one_liner") or hit.get("long_description"),
                    "yc_batch":      batch_short,
                    "funding_stage": hit.get("stage"),  # "Early" | "Growth" | "Public"
                    "founded_year":  None,              # filled in phase 2
                    "_founders":     [],                # filled in phase 2
                })

            page += 1
            if page >= nb_pages:
                break

        print(f"  [algolia] fetched {len(results)} companies across {page} page(s)")

        # ── Phase 2: per-company founder fetch ────────────────────────────────
        if fetch_founders and results:
            print(f"  [founders] fetching {len(results)} company pages @ {rps} req/s ...")
            for i, company in enumerate(results, start=1):
                slug = company.get("slug") or ""
                name = company.get("name", "?")
                print(f"    [{i:>3}/{len(results)}] {name:<35}", end="  ", flush=True)

                founders, year_founded = await _fetch_founders(slug, client, limiter)
                company["_founders"] = founders
                company["founded_year"] = year_founded

                f_names = ", ".join(
                    f["full_name"] for f in founders if f.get("full_name")
                ) or "—"
                print(f"{len(founders)} founder(s): {f_names}")

    # ── Phase 3: persist ──────────────────────────────────────────────────────
    tweets_saved = 0
    if save_to_db:
        # Pass a copy so we don't mutate the caller's list
        import copy
        upserted = _upsert_to_db(copy.deepcopy(results))
        print(f"  [db] upserted {upserted} companies")

        # ── Phase 4: Twitter enrichment ───────────────────────────────────────
        tweets_saved = await _enrich_with_twitter(results)

        # ── Phase 5: Crunchbase enrichment ────────────────────────────────────
        await _enrich_with_crunchbase(results)

    return results, tweets_saved


# ── CLI test runner ───────────────────────────────────────────────────────────

def _print_summary(companies: list[dict]) -> None:
    sep = "-" * 80
    header = f"{'#':>3}  {'Company':<30}  {'Domain':<25}  {'Yr':>4}  Founders"
    print()
    print("=" * 80)
    print(f" YC Scrape Results -- {len(companies)} companies")
    print("=" * 80)
    print(header)
    print(sep)
    for i, c in enumerate(companies, start=1):
        founders = c.get("_founders", [])
        f_str = ", ".join(f["full_name"] for f in founders if f.get("full_name")) or "-"
        yr = str(c.get("founded_year") or "-")
        name = (c.get("name") or "")[:29]
        domain = (c.get("domain") or "")[:24]
        print(f"{i:>3}  {name:<30}  {domain:<25}  {yr:>4}  {f_str}")
    print(sep)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape YC company directory")
    parser.add_argument("--batch", default=DEFAULT_BATCH, help="Batch, e.g. W25, S24")
    parser.add_argument("--pages", type=int, default=None, help="Max pages (default: all)")
    parser.add_argument("--no-founders", dest="founders", action="store_false",
                        help="Skip per-company founder fetch")
    parser.add_argument("--dry-run", dest="save_db", action="store_false",
                        help="Do not write to database")
    parser.add_argument("--rps", type=float, default=1.0,
                        help="Requests per second (default 1.0)")
    args = parser.parse_args()

    companies, tweets_saved = asyncio.run(
        scrape_yc_batch(
            batch=args.batch,
            max_pages=args.pages,
            fetch_founders=args.founders,
            save_to_db=args.save_db,
            rps=args.rps,
        )
    )
    _print_summary(companies)
    print(f"Done. {len(companies)} companies scraped, {tweets_saved} tweets saved.")


if __name__ == "__main__":
    main()
