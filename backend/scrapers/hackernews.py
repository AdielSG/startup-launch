"""
Hacker News scraper — fetches 'Launch HN' posts via the HN Algolia API.
No authentication required.
Full implementation in Module 2.
"""


async def search_launch_hn_posts(company_name: str | None = None) -> list[dict]:
    """
    Fetch Launch HN posts and their scores/comment counts.
    If company_name is provided, filter results to that company.
    HN Algolia API: https://hn.algolia.com/api/v1/search
    """
    # TODO Module 2: httpx GET to HN Algolia search API
    raise NotImplementedError("HN scraper not yet implemented")
