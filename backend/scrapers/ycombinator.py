"""
ycombinator.py — thin wrapper kept for backward compatibility.
Real implementation lives in yc_scraper.py.
"""
from scrapers.yc_scraper import scrape_yc_batch


async def scrape_yc_companies(batch: str = "W25") -> list[dict]:
    """Scrape YC company directory for a given batch. Delegates to yc_scraper."""
    return await scrape_yc_batch(batch=batch)
