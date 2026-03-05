"""
LinkedIn scraper — intentionally stubbed per project decision.
Returns 'pending' status; manual entry supported via PATCH /launches/{id}.
"""


async def get_linkedin_engagement(company_name: str) -> dict:
    return {
        "likes": None,
        "post_url": None,
        "status": "pending",
        "note": "LinkedIn scraping not implemented — use manual entry via the dashboard",
    }
