"""
Base scraper utilities — rate-limited queue with exponential backoff.
Full implementation in Module 2.
"""
import asyncio
import random
from typing import Any, Callable


async def with_backoff(
    fn: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Any:
    """
    Execute fn() with exponential backoff on failure.
    Delay formula: base_delay * (2 ** attempt) + uniform jitter [0, 1s]
    """
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except Exception as exc:
            if attempt == max_retries:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"[backoff] Attempt {attempt + 1} failed: {exc}. Retrying in {delay:.2f}s")
            await asyncio.sleep(delay)
