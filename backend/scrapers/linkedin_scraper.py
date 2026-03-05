"""
LinkedIn post metrics scraper — powered by Apify.
Actor: supreme_coder/linkedin-post  (ID: Wpp1BZ6yGWjySadk3)

Rate limit: 1 request per 3 seconds (enforced via asyncio.sleep).
On any Apify error or empty result, logs the issue and returns None
without raising so the caller can handle it gracefully.
"""
import asyncio
import logging
from datetime import datetime, timezone

from apify_client import ApifyClientAsync
from sqlalchemy.orm import Session

from config import settings
from models import Company, LaunchPost

logger = logging.getLogger(__name__)

_ACTOR_ID   = "Wpp1BZ6yGWjySadk3"
_RATE_LIMIT = 3  # seconds between requests


def _extract_metrics(item: dict) -> dict:
    """
    Extract engagement metrics from a Wpp1BZ6yGWjySadk3 actor response item.

    Expected structure:
      item["engagement"]["likes"]    → like count
      item["engagement"]["shares"]   → repost count
      item["engagement"]["comments"] → comment count
      item["postedAt"]["iso"]        → post date (ISO 8601)
    """
    engagement = item.get("engagement") or {}
    posted_at  = item.get("postedAt")   or {}

    likes    = int(engagement.get("likes",    0) or 0)
    reposts  = int(engagement.get("shares",   0) or 0)
    comments = int(engagement.get("comments", 0) or 0)

    # Parse the ISO date string into a date object; fall back to today
    iso_str   = posted_at.get("iso")
    post_date = datetime.now(timezone.utc).date()
    if iso_str:
        try:
            post_date = datetime.fromisoformat(iso_str.replace("Z", "+00:00")).date()
        except ValueError:
            pass

    return {
        "likes":     likes,
        "reposts":   reposts,
        "comments":  comments,
        "post_date": post_date,
    }


def _upsert_launch_post(
    db: Session,
    company_id: int,
    post_url: str,
    likes: int,
    reposts: int,
    post_date,
) -> None:
    """Keep the launch_posts table in sync (dual-write)."""
    post = (
        db.query(LaunchPost)
        .filter(LaunchPost.company_id == company_id, LaunchPost.platform == "linkedin")
        .first()
    )
    if post:
        post.likes    = likes
        post.reposts  = reposts
        post.post_url = post_url
        post.date     = post_date
    else:
        db.add(LaunchPost(
            company_id = company_id,
            platform   = "linkedin",
            post_url   = post_url,
            likes      = likes,
            reposts    = reposts,
            date       = post_date,
        ))
    db.commit()


async def fetch_linkedin_post_metrics(
    company_id: int,
    post_url: str,
    db: Session,
) -> dict | None:
    """
    Fetch likes and reposts for a LinkedIn post URL via Apify.

    Returns a dict with keys: likes, reposts, fetched_at
    Returns None on any error (Apify failure, empty result, missing token).
    """
    if not settings.apify_api_token:
        logger.error("APIFY_API_TOKEN is not set — cannot scrape LinkedIn post.")
        return None

    # Enforce rate limit before hitting the API
    await asyncio.sleep(_RATE_LIMIT)

    try:
        client = ApifyClientAsync(token=settings.apify_api_token)

        run = await client.actor(_ACTOR_ID).call(
            run_input={
                "urls":                        [post_url],
                "limitPerSource":              1,
                "scrapeUntilDate":             None,
                "scrapeAdditionalInformation": True,
                "getRowData":                  False,
            }
        )

        if not run:
            logger.error("Apify actor run returned None for URL: %s", post_url)
            return None

        dataset_items = (
            await client.dataset(run["defaultDatasetId"]).list_items()
        ).items

        if not dataset_items:
            logger.warning("Apify returned 0 items for URL: %s", post_url)
            return None

        metrics    = _extract_metrics(dataset_items[0])
        fetched_at = datetime.now(timezone.utc)

        # ── Dual-write: update Company columns + upsert LaunchPost row ──────
        company = db.query(Company).filter(Company.id == company_id).first()
        if company:
            company.linkedin_post_url   = post_url
            company.linkedin_likes      = metrics["likes"]
            company.linkedin_reposts    = metrics["reposts"]
            company.linkedin_fetched_at = fetched_at
            db.commit()

        _upsert_launch_post(
            db, company_id, post_url,
            metrics["likes"], metrics["reposts"], metrics["post_date"],
        )

        return {
            "likes":      metrics["likes"],
            "reposts":    metrics["reposts"],
            "fetched_at": fetched_at,
        }

    except Exception as exc:
        logger.error("Apify scrape failed for %s: %s", post_url, exc)
        return None
