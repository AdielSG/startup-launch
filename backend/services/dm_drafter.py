"""
DM drafting service — generates personalised outreach via OpenAI API.
"""
from openai import AsyncOpenAI, APIError

from config import settings


def _fmt_funding(amount: float) -> str:
    if not amount:
        return "unknown"
    if amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.1f}B"
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    return f"${amount / 1_000:.0f}K"


async def draft_dm(
    company_name: str,
    description: str | None,
    yc_batch: str | None,
    total_funding: float,
    twitter_likes: int | None,
    linkedin_likes: int | None,
    tone: str = "professional",
) -> str:
    """
    Generate a tailored outreach DM for a poorly-performing launch.
    Uses gpt-4o-mini via the OpenAI API.

    Raises:
        ValueError  — if the API key is not configured.
        APIError    — if the OpenAI call fails.
    """
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. "
            "Add it to your .env file to enable DM generation."
        )

    funding_str = _fmt_funding(total_funding)
    x_str       = f"{twitter_likes:,}" if twitter_likes is not None else "unknown"

    user_prompt = (
        f"Company: {company_name}\n"
        f"What they launched: {description or 'N/A'}\n"
        f"Funding raised: {funding_str}\n"
        f"X like count: {x_str}"
    )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=400,
        messages=[
            {
                "role": "system",
                "content": "You are an outreach specialist. Write friendly, concise DMs that offer genuine value. Never sound salesy.",
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )
    return response.choices[0].message.content.strip()
