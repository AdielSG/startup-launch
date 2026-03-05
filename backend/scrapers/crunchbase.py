"""
Crunchbase Basic API scraper.

Public async functions:
  get_permalink(company_name, domain) → str | None
  get_funding(permalink)              → dict | None

Rate limit: 1 request per 0.3 s (stays well under 200 req/min).
On any API or network error, logs and returns None without raising.
"""
import asyncio
import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

_BASE      = "https://api.crunchbase.com"
_RATE_WAIT = 0.3   # seconds between every request


async def get_permalink(
    company_name: str,
    domain: Optional[str] = None,
) -> Optional[str]:
    """
    Use the Crunchbase autocomplete endpoint to resolve a company name
    (and optional domain) to a Crunchbase permalink.

    Matching priority:
      1. Exact name match (case-insensitive)
      2. Domain stem contained in candidate name  (e.g. "resend.com" → "resend")
      3. First autocomplete result as a fallback

    Returns the permalink string (e.g. "mentra") or None.
    """
    if not settings.crunchbase_api_key:
        logger.error("CRUNCHBASE_API_KEY not set — cannot call autocomplete")
        return None

    await asyncio.sleep(_RATE_WAIT)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{_BASE}/v4/data/autocompletes",
                params={
                    "user_key":       settings.crunchbase_api_key,
                    "query":          company_name,
                    "collection_ids": "organization.companies",
                    "limit":          5,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("Crunchbase autocomplete failed for %r: %s", company_name, exc)
        return None

    entities = data.get("entities", [])
    if not entities:
        logger.debug("No autocomplete results for %r", company_name)
        return None

    name_lower  = company_name.lower()
    domain_stem = domain.split(".")[0].lower() if domain else None

    for entity in entities:
        ident     = entity.get("identifier", {})
        candidate = (ident.get("value") or "").lower()
        permalink = ident.get("permalink")
        if not permalink:
            continue
        if candidate == name_lower:
            return permalink
        if domain_stem and domain_stem in candidate:
            return permalink

    # No exact match — use the first result (Crunchbase ranks by relevance)
    first = entities[0].get("identifier", {}).get("permalink")
    logger.debug("No exact match for %r — using first result: %s", company_name, first)
    return first


async def get_funding(permalink: str) -> Optional[dict]:
    """
    Fetch funding data for a Crunchbase organization by permalink.

    Returns a dict with:
      funding_total      (float, USD)
      num_funding_rounds (int)
      last_funding_type  (str | None)  e.g. "seed", "series_a"
      short_description  (str | None)

    Returns None on any API or parsing error.
    """
    if not settings.crunchbase_api_key:
        return None

    await asyncio.sleep(_RATE_WAIT)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{_BASE}/api/v4/entities/organizations/{permalink}",
                params={
                    "user_key":  settings.crunchbase_api_key,
                    "field_ids": (
                        "funding_total,num_funding_rounds,"
                        "last_funding_type,short_description"
                    ),
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.error("Crunchbase entity fetch failed for %r: %s", permalink, exc)
        return None

    props = data.get("properties", {})

    # funding_total is a Money object: {"value": 123, "currency": "USD", "value_usd": 123}
    ft_obj        = props.get("funding_total") or {}
    funding_total = float(ft_obj.get("value_usd") or ft_obj.get("value") or 0)

    return {
        "funding_total":      funding_total,
        "num_funding_rounds": int(props.get("num_funding_rounds") or 0),
        "last_funding_type":  props.get("last_funding_type"),
        "short_description":  props.get("short_description"),
    }
