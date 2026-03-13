"""
twitter.py -- Find a company's launch tweet via Apify apidojo/tweet-scraper.

Strategy
--------
Builds a targeted search query combining the company name / X handle with
launch keywords, runs the Apify actor (maxItems=5, sort=Latest), and returns
the tweet with the most likes.

When a company X handle is known the query is scoped to `from:{handle}` for
high precision. Otherwise it falls back to a name + keyword search.

Rate limiting
-------------
One actor call per 2 seconds (asyncio.sleep before each run).  The actor
bills per tweet returned, not per search, so keeping maxItems=5 keeps costs
low.  There is no monthly budget cap needed — Apify charges are metered on
actual results.

Usage (CLI)
-----------
    python -m scrapers.twitter --company "Browser Use" --dry-run
    python -m scrapers.twitter --company "Mentra" --handle mentrahq
"""

import argparse
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from apify_client import ApifyClientAsync

from config import settings

logger = logging.getLogger(__name__)

_ACTOR_ID   = "apidojo/tweet-scraper"
_RATE_LIMIT = 2        # seconds between actor calls

LAUNCH_KEYWORDS = 'launched OR introducing OR "we built" OR "just shipped"'


# ── Query builder ──────────────────────────────────────────────────────────────

def build_query(
    company_name: str,
    domain: Optional[str] = None,
    x_handle: Optional[str] = None,
) -> str:
    """
    Build a Twitter search query string for the Apify actor's searchTerms field.

    When x_handle is known, scope the search to `from:{handle}` so we only
    get tweets posted by the company itself — much more accurate.

    Fallback (no handle): OR the exact company name + domain stem with launch
    keywords, excluding retweets and non-English tweets.

    Examples:
        build_query("Browser Use", x_handle="browser_use")
        -> 'from:browser_use (launched OR introducing OR "we built" OR "just shipped")'

        build_query("Browser Use", "browser-use.com")
        -> '"Browser Use" OR "browser-use" (launched OR …) -is:retweet lang:en'
    """
    if x_handle:
        return f"from:{x_handle} ({LAUNCH_KEYWORDS}) has:videos"

    name_part = f'"{company_name}"'
    if domain:
        stem = domain.split(".")[0]
        if stem.lower() != company_name.lower():
            name_part = f'({name_part} OR "{stem}")'

    return f"{name_part} ({LAUNCH_KEYWORDS}) has:videos -is:retweet lang:en"


# ── Video detection ────────────────────────────────────────────────────────────

def _has_video(tweet: dict) -> bool:
    """Return True if the tweet contains a native video or animated GIF."""
    media = (tweet.get("extendedEntities") or {}).get("media") or []
    return any(m.get("type") in ("video", "animated_gif") for m in media)


# ── Date parser ────────────────────────────────────────────────────────────────

def _parse_date(created_at: Optional[str]):
    """Parse ISO createdAt string into a date object, or return None."""
    if not created_at:
        return None
    try:
        return datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None


# ── Core search ────────────────────────────────────────────────────────────────

async def search_launch_tweet(
    company_name: str,
    domain: Optional[str] = None,
    x_handle: Optional[str] = None,
) -> Optional[dict]:
    """
    Find the most-liked launch tweet for a company via Apify.

    Args:
        company_name: Company display name, e.g. "Browser Use"
        domain:       Company domain, e.g. "browser-use.com" (optional)
        x_handle:     Company's X/Twitter handle (optional; enables from: search)

    Returns:
        Dict with keys: url, likes, reposts, replies, date, author,
                        candidates_checked
        None if the actor returned no results.

    Raises:
        RuntimeError if APIFY_API_TOKEN is not configured.
        Any exception from the Apify client is re-raised to the caller.
    """
    if not settings.apify_api_token:
        raise RuntimeError("APIFY_API_TOKEN is not set in .env")

    await asyncio.sleep(_RATE_LIMIT)

    query = build_query(company_name, domain, x_handle)
    logger.info("[twitter] company=%r  query=%r", company_name, query)

    client = ApifyClientAsync(token=settings.apify_api_token)

    run = await client.actor(_ACTOR_ID).call(
        run_input={
            "searchTerms": [query],
            "maxItems":    5,
            "sort":        "Latest",
        }
    )

    if not run:
        logger.warning("[twitter] %r: actor run returned None", company_name)
        return None

    items = (
        await client.dataset(run["defaultDatasetId"]).list_items()
    ).items

    if not items:
        logger.debug("[twitter] %r: no tweets found", company_name)
        return None

    # Prefer video tweets; within each group, pick the one with the most likes.
    # Sort key: (has_video DESC, likeCount DESC)
    best = max(items, key=lambda t: (_has_video(t), t.get("likeCount") or 0))

    # URL comes directly from the actor output
    tweet_url = best.get("url") or ""
    author    = (best.get("author") or {}).get("userName") or "unknown"

    # Fallback URL construction if the actor omitted the field
    if not tweet_url and author != "unknown":
        tweet_url = f"https://x.com/{author}/status/{best.get('id', '')}"

    return {
        "url":                tweet_url,
        "likes":              best.get("likeCount")    or 0,
        "reposts":            best.get("retweetCount") or 0,
        "replies":            best.get("replyCount")   or 0,
        "date":               _parse_date(best.get("createdAt")),
        "author":             author,
        "has_video":          _has_video(best),
        "candidates_checked": len(items),
    }


# ── Database save ─────────────────────────────────────────────────────────────

def save_to_db(company_id: int, tweet: dict) -> None:
    """
    Upsert the tweet result into launch_posts (platform='twitter').

    If a Twitter post already exists for this company it is updated
    in-place; otherwise a new row is inserted.
    """
    from database import SessionLocal
    from models import LaunchPost

    db = SessionLocal()
    try:
        existing = (
            db.query(LaunchPost)
            .filter(
                LaunchPost.company_id == company_id,
                LaunchPost.platform == "twitter",
            )
            .first()
        )

        if existing:
            existing.post_url  = tweet["url"]
            existing.likes     = tweet["likes"]
            existing.reposts   = tweet["reposts"]
            existing.date      = tweet["date"]
            existing.has_video = tweet.get("has_video", False)
        else:
            db.add(LaunchPost(
                company_id = company_id,
                platform   = "twitter",
                post_url   = tweet["url"],
                likes      = tweet["likes"],
                reposts    = tweet["reposts"],
                date       = tweet["date"],
                has_video  = tweet.get("has_video", False),
            ))

        db.commit()
        logger.info("Saved Twitter post for company_id=%d: %s", company_id, tweet["url"])
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


async def find_and_save(
    company_name: str,
    company_id: int,
    domain: Optional[str] = None,
    x_handle: Optional[str] = None,
) -> Optional[dict]:
    """Convenience wrapper: search + save in one call."""
    tweet = await search_launch_tweet(company_name, domain, x_handle)
    if tweet:
        save_to_db(company_id, tweet)
    return tweet


# ── CLI ───────────────────────────────────────────────────────────────────────

async def _cli_search(company_name: str, x_handle: Optional[str], dry_run: bool) -> None:
    if not settings.apify_api_token:
        print("ERROR: APIFY_API_TOKEN not set in .env")
        return

    query = build_query(company_name, x_handle=x_handle)
    print(f"  Company : {company_name}")
    print(f"  Query   : {query}")
    print()

    try:
        result = await search_launch_tweet(company_name, x_handle=x_handle)
    except Exception as exc:
        print(f"  ERROR: {exc}")
        return

    if result is None:
        print("  Result  : No matching tweets found.")
        return

    print(f"  Result  : Found (best of {result['candidates_checked']} candidates)")
    print(f"  Author  : @{result['author']}")
    print(f"  URL     : {result['url']}")
    print(f"  Likes   : {result['likes']:,}")
    print(f"  Reposts : {result['reposts']:,}")
    print(f"  Date    : {result['date']}")
    print()

    if dry_run:
        print("  Dry run — not saved to DB.")
        return

    from database import SessionLocal
    from models import Company

    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.name == company_name).first()
        if company:
            save_to_db(company.id, result)
            print(f"  Saved to DB (company_id={company.id})")
        else:
            print(f"  Company '{company_name}' not found in DB — skipping save.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Twitter launch tweet scraper (via Apify)")
    parser.add_argument("--company",  default="Browser Use", help="Company name to search for")
    parser.add_argument("--handle",   default=None,          help="X/Twitter handle (optional)")
    parser.add_argument("--dry-run",  action="store_true",   help="Print result without saving to DB")
    args = parser.parse_args()

    asyncio.run(_cli_search(args.company, args.handle, args.dry_run))


if __name__ == "__main__":
    main()
