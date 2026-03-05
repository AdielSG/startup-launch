"""
Scheduler — APScheduler background job that fires every 6 hours.
Runs the full scraping pipeline: YC company scrape → Twitter enrichment.
"""
import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger(__name__)
_scheduler = BackgroundScheduler()


def _scrape_job():
    """
    Sync wrapper for the async scrape pipeline.
    APScheduler's BackgroundScheduler runs jobs in threads, so we create
    a new event loop for each run.
    """
    from scrapers.yc_scraper import scrape_yc_batch

    log.info("[scheduler] Scrape job started")
    try:
        companies, tweets = asyncio.run(scrape_yc_batch(batch="W25", fetch_founders=True))
        log.info(
            "[scheduler] Scrape job complete — %d companies, %d tweets",
            len(companies), tweets,
        )
    except Exception as exc:
        log.error("[scheduler] Scrape job error: %s", exc, exc_info=True)


def start_scheduler():
    _scheduler.add_job(_scrape_job, "interval", hours=6, id="scrape_all")
    _scheduler.start()
    log.info("[scheduler] Started — scrape job runs every 6 hours")


def shutdown_scheduler():
    _scheduler.shutdown(wait=False)
    log.info("[scheduler] Stopped")
