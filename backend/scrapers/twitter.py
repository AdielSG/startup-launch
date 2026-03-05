"""
twitter.py -- Find a company's launch tweet via Twitter API v2.

Strategy
--------
Builds a targeted search query combining the company name with launch
keywords, fetches up to 10 recent tweets (the API minimum, cheapest
option on Pay-Per-Use), and returns the one with the most likes.

Budget guard
------------
Twitter Pay-Per-Use charges per tweet read. A JSON file
(twitter_usage.json, next to this file) tracks the monthly request
count and halts at BUDGET_GUARD (default 450) to leave a safety buffer
below the 500-request target. The counter resets automatically on the
first call of each new calendar month.

Rate limiting
-------------
1 request per call -- no pagination, no background polling.
The scheduler in scheduler.py spaces out calls across companies.

Retry policy
------------
Transient server errors (5xx): up to 3 retries with exponential backoff.
Rate-limit errors (429): treated as budget exhaustion -- no retry.
Auth/permission errors (401, 403): raised immediately.

Usage (CLI)
-----------
    # verify token and test connectivity
    python -m scrapers.twitter --verify

    # search for a specific company (dry run, no DB write)
    python -m scrapers.twitter --company "Browser Use" --dry-run

    # search and save to DB (company must exist in companies table)
    python -m scrapers.twitter --company "Mentra"
"""

import argparse
import asyncio
import json
import logging
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import tweepy

from config import settings

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

# Launch signal keywords used in the query.
# Each multi-word phrase is pre-quoted for the Twitter query syntax.
LAUNCH_KEYWORDS: list[str] = [
    "launched",
    "introducing",
    '"we built"',
]

# Request budget management
MONTHLY_LIMIT = 500          # target the user specified
BUDGET_GUARD  = 450          # halt at 90% to leave a safety buffer

# Persistent usage counter (resets on new calendar month)
_USAGE_FILE = Path(__file__).parent / "twitter_usage.json"


# ── Budget tracking ────────────────────────────────────────────────────────────

class TwitterBudgetError(Exception):
    """Raised when the monthly API request budget is near exhausted."""


def _load_usage() -> dict:
    """Load usage dict from disk, or return a fresh default."""
    if _USAGE_FILE.exists():
        try:
            return json.loads(_USAGE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"month": "", "count": 0}


def _save_usage(usage: dict) -> None:
    _USAGE_FILE.write_text(json.dumps(usage, indent=2), encoding="utf-8")


def _check_and_increment() -> int:
    """
    Increment the monthly counter. Reset it when the calendar month changes.
    Returns the new count.
    Raises TwitterBudgetError if the guard threshold is already reached.
    """
    usage = _load_usage()
    current_month = datetime.utcnow().strftime("%Y-%m")

    if usage.get("month") != current_month:
        usage = {"month": current_month, "count": 0}

    if usage["count"] >= BUDGET_GUARD:
        raise TwitterBudgetError(
            f"Monthly Twitter budget guard reached "
            f"({usage['count']}/{MONTHLY_LIMIT} requests in {current_month}). "
            f"Halting to avoid overspend. Resets on {current_month[:4]}-"
            f"{int(current_month[5:]) % 12 + 1:02d}-01."
        )

    usage["count"] += 1
    _save_usage(usage)
    return usage["count"]


def get_usage() -> dict:
    """Return current usage stats (safe to call without incrementing)."""
    return _load_usage()


# ── Query builder ──────────────────────────────────────────────────────────────

def build_query(
    company_name: str,
    domain: Optional[str] = None,
    x_handle: Optional[str] = None,
) -> str:
    """
    Construct a Twitter search query for a company's launch tweet.

    When x_handle is known, use a `from:` scoped query so we only get
    tweets the company itself posted — much more accurate than a name search.

    Fallback (no x_handle): OR the exact company name + domain stem with
    launch keywords, excluding retweets and non-English tweets.

    Examples:
        build_query("Browser Use", x_handle="browser_use")
        -> 'from:browser_use (launched OR introducing OR "we built" OR "just shipped")'

        build_query("Browser Use", "browser-use.com")
        -> '"Browser Use" OR "browser-use" (launched OR introducing OR "we built") -is:retweet lang:en'
    """
    kw_part = 'launched OR introducing OR "we built" OR "just shipped"'

    if x_handle:
        return f"from:{x_handle} ({kw_part})"

    name_part = f'"{company_name}"'
    if domain:
        stem = domain.split(".")[0]          # "browser-use.com" -> "browser-use"
        if stem.lower() != company_name.lower():
            name_part = f'({name_part} OR "{stem}")'

    fallback_kw = " OR ".join(LAUNCH_KEYWORDS)  # original keyword set
    return f"{name_part} ({fallback_kw}) -is:retweet lang:en"


# ── Core search (synchronous tweepy call) ─────────────────────────────────────

def _sync_search(query: str) -> Optional[dict]:
    """
    Execute one search_recent_tweets call.
    Returns the tweet dict with the most likes, or None if no results.

    This is a synchronous function; call it via asyncio.to_thread() from
    async contexts.
    """
    client = tweepy.Client(
        bearer_token=settings.twitter_bearer_token,
        wait_on_rate_limit=False,   # we manage rate limits ourselves
    )

    for attempt in range(3):
        try:
            response = client.search_recent_tweets(
                query=query,
                max_results=10,     # API minimum; cheapest option
                tweet_fields=["public_metrics", "created_at"],
                expansions=["author_id"],
                user_fields=["username"],
            )
            break  # success

        except tweepy.errors.TooManyRequests:
            # 429 on Pay-Per-Use means we've hit the per-15-min cap.
            # Do NOT retry -- that burns budget. Surface it immediately.
            raise TwitterBudgetError(
                "Twitter API rate limit hit (429). "
                "Waited calls are disabled on Pay-Per-Use to avoid charges."
            )

        except tweepy.errors.Unauthorized as exc:
            raise RuntimeError(
                f"Twitter bearer token rejected (401). "
                f"Check TWITTER_BEARER_TOKEN in .env. Detail: {exc}"
            ) from exc

        except tweepy.errors.Forbidden as exc:
            raise RuntimeError(
                f"Twitter API access forbidden (403). "
                f"Verify your app has 'Read' permissions and search access. "
                f"Detail: {exc}"
            ) from exc

        except tweepy.errors.BadRequest as exc:
            raise ValueError(
                f"Malformed Twitter query: {query!r}. Detail: {exc}"
            ) from exc

        except tweepy.errors.TwitterServerError:
            if attempt == 2:
                raise
            wait = 2 ** attempt + 1
            logger.warning("Twitter server error (5xx), retry %d/3 in %ds", attempt + 1, wait)
            time.sleep(wait)

    # No results
    if not response.data:
        return None

    # Build username lookup from expansions
    users: dict[int, str] = {}
    if response.includes and "users" in response.includes:
        users = {u.id: u.username for u in response.includes["users"]}

    # Pick the tweet with the most likes
    best = max(response.data, key=lambda t: t.public_metrics.get("like_count", 0))

    username = users.get(best.author_id, "unknown")
    tweet_url = f"https://twitter.com/{username}/status/{best.id}"

    return {
        "tweet_id": str(best.id),
        "text": best.text,
        "url": tweet_url,
        "likes": best.public_metrics.get("like_count", 0),
        "reposts": best.public_metrics.get("retweet_count", 0),
        "replies": best.public_metrics.get("reply_count", 0),
        "date": best.created_at.date() if best.created_at else None,
        "author": username,
        "candidates_checked": len(response.data),
    }


# ── Public async API ──────────────────────────────────────────────────────────

async def search_launch_tweet(
    company_name: str,
    domain: Optional[str] = None,
    x_handle: Optional[str] = None,
) -> Optional[dict]:
    """
    Find the most-liked launch tweet for a company.

    Checks and increments the monthly request budget before calling the
    API. Returns a tweet dict on success, None if no results were found.
    Raises TwitterBudgetError when the monthly guard is reached.

    Args:
        company_name: Company display name, e.g. "Browser Use"
        domain:       Company domain, e.g. "browser-use.com" (optional)
        x_handle:     Company's own X/Twitter handle (optional; when set,
                      scopes the search to `from:{handle}` for much higher
                      precision than a keyword search)

    Returns:
        Dict with keys: tweet_id, text, url, likes, reposts, replies,
                        date, author, candidates_checked
        None if the query returned no results.
    """
    if not settings.twitter_bearer_token:
        raise RuntimeError("TWITTER_BEARER_TOKEN is not set in .env")

    query = build_query(company_name, domain, x_handle)
    count = _check_and_increment()
    logger.info(
        "Twitter search #%d/%d | company=%r | query=%r",
        count, BUDGET_GUARD, company_name, query,
    )

    try:
        result = await asyncio.to_thread(_sync_search, query)
    except Exception:
        # Roll back the increment on error so we don't waste the budget slot
        usage = _load_usage()
        usage["count"] = max(0, usage["count"] - 1)
        _save_usage(usage)
        raise

    return result


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
            existing.post_url = tweet["url"]
            existing.likes    = tweet["likes"]
            existing.reposts  = tweet["reposts"]
            existing.date     = tweet["date"]
        else:
            db.add(LaunchPost(
                company_id = company_id,
                platform   = "twitter",
                post_url   = tweet["url"],
                likes      = tweet["likes"],
                reposts    = tweet["reposts"],
                date       = tweet["date"],
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
    """
    Convenience wrapper: search + save in one call.
    Returns the tweet dict, or None if nothing was found.
    """
    tweet = await search_launch_tweet(company_name, domain, x_handle)
    if tweet:
        save_to_db(company_id, tweet)
    return tweet


# ── CLI ───────────────────────────────────────────────────────────────────────

def _print_result(company_name: str, query: str, result: Optional[dict]) -> None:
    print()
    print(f"  Company : {company_name}")
    print(f"  Query   : {query}")
    print()
    if result is None:
        print("  Result  : No matching tweets found.")
        print()
        print("  Note: search_recent_tweets only covers the last 7 days.")
        print("  Launch tweets older than 7 days require the Full Archive")
        print("  endpoint (Academic/Enterprise tier).")
    else:
        print(f"  Result  : Found (best of {result['candidates_checked']} candidates)")
        print(f"  Author  : @{result['author']}")
        print(f"  URL     : {result['url']}")
        print(f"  Likes   : {result['likes']:,}")
        print(f"  Reposts : {result['reposts']:,}")
        print(f"  Replies : {result['replies']:,}")
        print(f"  Date    : {result['date']}")
        print(f"  Text    : {result['text'][:120]}{'...' if len(result['text']) > 120 else ''}")
    print()


async def _cli_verify() -> None:
    """Send a minimal query to confirm the bearer token is valid."""
    print("Verifying Twitter API connectivity...")
    if not settings.twitter_bearer_token:
        print("  ERROR: TWITTER_BEARER_TOKEN not set in .env")
        return
    try:
        count = _check_and_increment()
        result = await asyncio.to_thread(
            _sync_search, "YCombinator -is:retweet lang:en"
        )
        print(f"  OK -- bearer token accepted.")
        print(f"  Budget: {count}/{BUDGET_GUARD} requests used this month.")
        if result:
            print(f"  Test tweet: {result['url']}")
    except TwitterBudgetError as e:
        print(f"  BUDGET: {e}")
    except Exception as e:
        print(f"  ERROR: {e}")


async def _cli_search(company_name: str, dry_run: bool) -> None:
    usage = get_usage()
    print(f"Budget: {usage.get('count', 0)}/{BUDGET_GUARD} requests used "
          f"({usage.get('month', 'n/a')})")

    query = build_query(company_name)
    try:
        result = await search_launch_tweet(company_name)
    except TwitterBudgetError as e:
        print(f"BUDGET GUARD: {e}")
        return
    except Exception as e:
        print(f"ERROR: {e}")
        return

    _print_result(company_name, query, result)

    if result and not dry_run:
        # Look up company_id from DB
        from database import SessionLocal
        from models import Company
        db = SessionLocal()
        try:
            company = db.query(Company).filter(Company.name == company_name).first()
            if company:
                save_to_db(company.id, result)
                print(f"  Saved to DB (company_id={company.id})")
            else:
                print(f"  Company '{company_name}' not found in DB -- skipping save.")
                print("  Run seed.py or the YC scraper first to add it.")
        finally:
            db.close()
    elif result and dry_run:
        print("  Dry run -- not saved to DB.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Twitter launch tweet scraper")
    parser.add_argument("--company", default="Browser Use",
                        help="Company name to search for (default: 'Browser Use')")
    parser.add_argument("--verify", action="store_true",
                        help="Verify bearer token connectivity and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print result without saving to DB")
    parser.add_argument("--budget", action="store_true",
                        help="Show current monthly request usage and exit")
    args = parser.parse_args()

    if args.budget:
        u = get_usage()
        print(f"Twitter API usage: {u.get('count', 0)}/{BUDGET_GUARD} "
              f"(month={u.get('month', 'n/a')}, limit={MONTHLY_LIMIT})")
        return

    if args.verify:
        asyncio.run(_cli_verify())
        return

    asyncio.run(_cli_search(args.company, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
