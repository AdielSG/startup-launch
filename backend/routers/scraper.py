"""
Scraper router — manual trigger endpoint.

POST /scraper/run runs the full pipeline synchronously and only returns
once the scrape is complete. The frontend waits on this response (up to
300 s) before reloading the company list.
"""
import logging

from fastapi import APIRouter

router = APIRouter()
log = logging.getLogger(__name__)


@router.post("/run")
async def trigger_scrape():
    """
    Run the full scraping pipeline (YC + Twitter) and block until done.
    Returns the number of companies processed and tweets saved.
    """
    from scrapers.yc_scraper import scrape_yc_batch

    log.info("[scraper] Pipeline started")
    try:
        companies, tweets = await scrape_yc_batch(batch="W25", fetch_founders=True)
        log.info(
            "[scraper] Pipeline complete — %d companies, %d tweets",
            len(companies), tweets,
        )
        return {
            "status":    "ok",
            "companies": len(companies),
            "tweets":    tweets,
        }
    except Exception as exc:
        log.error("[scraper] Pipeline error: %s", exc, exc_info=True)
        return {"status": "error", "detail": str(exc), "companies": 0, "tweets": 0}
