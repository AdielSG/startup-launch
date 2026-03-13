"""
import_launch_tweets.py — Bulk-import launch tweets from a curated URL list.

Fetches tweet metrics via Apify (apidojo/tweet-scraper), then for each tweet:
  · Matches the author @handle to an existing company via contacts.x_handle
  · Upserts launch_posts with real engagement numbers
  · Creates a new Company (yc_batch="assessment") for unmatched authors

Notes
-----
* Two URLs in the source list share the same status ID (1932469194978922555):
    https://x.com/abhshkdz/status/1932469194978922555
    https://x.com/antonosika/status/1932469194978922555
  Only one author can own a tweet — the script deduplicates by URL and reports
  the discrepancy so you can fix the list manually.

* When the same author appears more than once, the tweet with the most likes
  is used (others are ignored).

Usage (run from the backend/ directory):
    python -m scripts.import_launch_tweets
    python -m scripts.import_launch_tweets --dry-run
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Allow running as a module from backend/ or directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from apify_client import ApifyClientAsync

from config import settings
from database import SessionLocal
from models import Company, Contact, FundingRound, LaunchPost

# ── Tweet URL list ─────────────────────────────────────────────────────────────

TWEET_URLS: list[str] = [
    "https://x.com/getcaptionsapp/status/1929554635544461727",
    "https://x.com/abhshkdz/status/1932469194978922555",
    "https://x.com/itsalfredw/status/1915065644875411730",
    "https://x.com/antonosika/status/1932469194978922555",
    "https://x.com/ycombinator/status/1953186461848879188",
    "https://x.com/weberwongwong/status/1894794612398792974",
    "https://x.com/willahmed/status/1920486427176898599",
    "https://x.com/thejamescad/status/1955339868659388418",
    "https://x.com/dylanottt/status/1942324855954890983",
    "https://x.com/Lauramaywendel/status/1952727329932706210",
    "https://x.com/antonosika/status/1948017850809270314",
    "https://x.com/Aiswarya_Sankar/status/1955284660822606013",
    "https://x.com/devvmandal/status/1952737863189078492",
    "https://x.com/TarunAmasa/status/1953130965355905140",
    "https://x.com/dom_lucre/status/1930377511009194271",
    "https://x.com/kuseHQ/status/1956362632849686979",
    "https://x.com/merit_systems/status/194044112973817876",
    "https://x.com/annarmonaco/status/1957474116640133252",
    "https://x.com/aquavoice_/status/1958577295528272331",
    "https://x.com/adilbuilds/status/1960730479503741432",
    "https://x.com/devv_ai/status/1960353809798238539",
    "https://x.com/nichochar/status/1958563340588081162",
    "https://x.com/samuelbeek/status/1962543194937180371",
    "https://x.com/exaailabs/status/1963262700123000947",
    "https://x.com/ccharliewu/status/1963333351622001047",
    "https://x.com/Creatify_AI/status/1963285168535613554",
    "https://x.com/audrlo/status/1963540707576336452",
    "https://x.com/amasad/status/1965800350071590966",
    "https://x.com/reve/status/1967640858372751540",
    "https://x.com/varunvummadi/status/1986088112544428100",
    "https://x.com/calumworthy/status/1988283207138324487",
    "https://x.com/karim_rc/status/1995538458836959487",
]

_ACTOR_ID = "apidojo/twitter-scraper-lite"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_date(created_at: Optional[str]):
    if not created_at:
        return None
    try:
        return datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None


def _handle_from_url(url: str) -> Optional[str]:
    """Extract lowercase username from https://x.com/{user}/status/{id}."""
    try:
        parts = url.rstrip("/").split("/")
        idx = parts.index("status")
        return parts[idx - 1].lower()
    except (ValueError, IndexError):
        return None


def _status_id_from_url(url: str) -> Optional[str]:
    """Extract the status ID from a tweet URL."""
    try:
        return url.rstrip("/").split("/status/")[1]
    except IndexError:
        return None


def _has_video(tweet: dict) -> bool:
    """Return True if the tweet contains a native video or animated GIF."""
    media = (tweet.get("extendedEntities") or {}).get("media") or []
    return any(m.get("type") in ("video", "animated_gif") for m in media)


# ── Duplicate URL detection ────────────────────────────────────────────────────

def _report_duplicate_urls(urls: list[str]) -> None:
    """Warn about URLs that share the same status ID (impossible in practice)."""
    seen: dict[str, str] = {}  # status_id → first URL
    for url in urls:
        sid = _status_id_from_url(url)
        if not sid:
            continue
        if sid in seen:
            print(
                f"\n  WARNING: DUPLICATE STATUS ID detected:\n"
                f"       {seen[sid]}\n"
                f"       {url}\n"
                f"     A tweet has only one author - one of these URLs is wrong.\n"
                f"     Both will be fetched; the actor will return the real author.\n"
            )
        else:
            seen[sid] = url


# ── Apify fetch ───────────────────────────────────────────────────────────────

async def fetch_tweet_metrics(urls: list[str]) -> list[dict]:
    """
    Fetch tweet metrics for all URLs in a single Apify run.

    Uses startUrls (standard Apify convention for URL-based input).
    Returns however many tweet items the actor manages to retrieve.
    """
    # Deduplicate URLs before sending to Apify
    unique_urls = list(dict.fromkeys(urls))

    client = ApifyClientAsync(token=settings.apify_api_token)
    print(f"  Starting Apify run ({len(unique_urls)} unique URLs) ...")

    run = await client.actor(_ACTOR_ID).call(
        run_input={
            "startUrls": [{"url": u} for u in unique_urls],
            "maxItems":  len(unique_urls) + 5,
        }
    )

    if not run:
        print("  ERROR: Apify actor run returned None.")
        return []

    items = (await client.dataset(run["defaultDatasetId"]).list_items()).items
    return items or []


# ── DB import ─────────────────────────────────────────────────────────────────

def _upsert_launch_post(db, company_id: int, tweet: dict) -> None:
    existing = (
        db.query(LaunchPost)
        .filter(
            LaunchPost.company_id == company_id,
            LaunchPost.platform == "twitter",
        )
        .first()
    )
    fields = dict(
        post_url  = tweet.get("url") or "",
        likes     = tweet.get("likeCount")    or 0,
        reposts   = tweet.get("retweetCount") or 0,
        date      = _parse_date(tweet.get("createdAt")),
        has_video = _has_video(tweet),
    )
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
    else:
        db.add(LaunchPost(company_id=company_id, platform="twitter", **fields))


def import_tweets(tweets: list[dict], dry_run: bool) -> tuple[int, int, int]:
    """
    Write tweet data to the DB.

    Deduplicates by author username — when the same author appears in multiple
    tweets, the one with the most likes is used.

    Returns (matched, created, skipped) counts.
    """
    # ── Deduplicate by author, keep highest-liked tweet ────────────────────────
    by_author: dict[str, dict] = {}
    for t in tweets:
        raw_author = (t.get("author") or {}).get("userName") or _handle_from_url(
            t.get("url") or ""
        )
        if not raw_author:
            continue
        author = raw_author.lower()
        prev = by_author.get(author)
        if prev is None or (t.get("likeCount") or 0) > (prev.get("likeCount") or 0):
            by_author[author] = t

    matched = created = skipped = 0
    db = SessionLocal()

    try:
        for author, tweet in by_author.items():
            url   = tweet.get("url") or "?"
            likes = tweet.get("likeCount")    or 0
            rt    = tweet.get("retweetCount") or 0
            date  = _parse_date(tweet.get("createdAt"))

            # ── Try to find existing company via contacts.x_handle ─────────────
            contact = (
                db.query(Contact)
                .filter(Contact.x_handle.ilike(author))
                .first()
            )

            if contact:
                company_id = contact.company_id
                company    = db.query(Company).filter(Company.id == company_id).first()
                cname      = company.name if company else f"id={company_id}"
                print(
                    f"  [matched]  @{author:<22} {likes:>7,} L  {rt:>6,} RT"
                    f"  -> {cname}"
                )
                matched += 1
                if not dry_run:
                    _upsert_launch_post(db, company_id, tweet)

            else:
                print(
                    f"  [new]      @{author:<22} {likes:>7,} L  {rt:>6,} RT"
                    f"  -> creating company"
                )
                created += 1
                if not dry_run:
                    company = Company(name=f"@{author}", yc_batch="assessment")
                    db.add(company)
                    db.flush()  # assigns company.id

                    db.add(Contact(company_id=company.id, x_handle=author))
                    db.add(FundingRound(
                        company_id = company.id,
                        amount     = 500_000,
                        round_type = "pre-seed",
                        source     = "yc",
                        note       = "YC standard deal (assessment import)",
                    ))
                    _upsert_launch_post(db, company.id, tweet)

        if not dry_run:
            db.commit()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return matched, created, skipped


# ── CLI ───────────────────────────────────────────────────────────────────────

async def main(dry_run: bool = False) -> None:
    if not settings.apify_api_token:
        print("ERROR: APIFY_API_TOKEN is not set in .env")
        sys.exit(1)

    print(f"{'[DRY RUN] ' if dry_run else ''}Importing {len(TWEET_URLS)} tweet URLs\n")

    _report_duplicate_urls(TWEET_URLS)

    tweets = await fetch_tweet_metrics(TWEET_URLS)
    total_fetched = len(tweets)
    print(f"  Apify returned {total_fetched} tweet(s)\n")

    if not tweets:
        print(
            "No tweets returned.\n"
            "If startUrls is not supported by this actor version, the script\n"
            "needs to switch to a search-term approach. Check the Apify run log."
        )
        return

    print(f"  {'Author':<24} {'Likes':>8}  {'RT':>6}  URL")
    print(f"  {'-'*24} {'-'*8}  {'-'*6}  {'-'*40}")
    for t in tweets:
        author = (t.get("author") or {}).get("userName", "?")
        print(
            f"  @{author:<23} {(t.get('likeCount') or 0):>8,}"
            f"  {(t.get('retweetCount') or 0):>6,}  {(t.get('url') or '')}"
        )
    print()

    print(f"  -- Matching & {'planning' if dry_run else 'writing'} -------------------------------------")
    matched, created, skipped = import_tweets(tweets, dry_run)

    mode = "[DRY RUN] " if dry_run else ""
    print(
        f"\n{mode}Done: {total_fetched} tweets fetched, "
        f"{matched} matched to existing companies, "
        f"{created} created as new entries"
        + (f", {skipped} skipped" if skipped else "")
    )


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Import launch tweets from assessment list into the dashboard DB"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch and match but do not write to the database",
    )
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))


if __name__ == "__main__":
    _cli()
