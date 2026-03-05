from typing import List, Optional

from openai import APIError
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Company
from schemas import (
    CompanyCreate,
    CompanyRead,
    CompanyUpdate,
    ContactRead,
    DmDraftResponse,
    DmToneRequest,
    LinkedInUrlRequest,
    LinkedInMetricsResponse,
)
from scrapers import linkedin_scraper
from services import dm_drafter

router = APIRouter()


# ── Company CRUD ──────────────────────────────────────────────────────────────

@router.get("/", response_model=List[CompanyRead])
def list_companies(
    yc_batch: Optional[str] = Query(None, description="Filter by YC batch, e.g. W25"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Company)
    if yc_batch:
        query = query.filter(Company.yc_batch == yc_batch)
    return query.offset(skip).limit(limit).all()


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.post("/", response_model=CompanyRead, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    company = Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.patch("/{company_id}", response_model=CompanyRead)
def update_company(company_id: int, payload: CompanyUpdate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}", status_code=204)
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()


# ── Enrichment ────────────────────────────────────────────────────────────────

@router.get("/{company_id}/contact", response_model=ContactRead)
def get_company_contact(company_id: int, db: Session = Depends(get_db)):
    """Return the primary contact for a company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    if not company.contacts:
        raise HTTPException(status_code=404, detail="No contact info on file")
    return company.contacts[0]


# ── LinkedIn Scraping ─────────────────────────────────────────────────────────

@router.post("/{company_id}/linkedin", response_model=LinkedInMetricsResponse)
async def fetch_linkedin_metrics(
    company_id: int,
    payload: LinkedInUrlRequest,
    db: Session = Depends(get_db),
):
    """
    Save a LinkedIn post URL for a company and trigger the Apify scraper.
    The Apify actor typically takes 20–60 seconds to respond.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not payload.linkedin_post_url.startswith("https://www.linkedin.com/"):
        raise HTTPException(status_code=422, detail="URL must be a linkedin.com post URL")

    # Persist the URL immediately so it's not lost if Apify is slow
    company.linkedin_post_url = payload.linkedin_post_url
    db.commit()

    result = await linkedin_scraper.fetch_linkedin_post_metrics(
        company_id = company_id,
        post_url   = payload.linkedin_post_url,
        db         = db,
    )

    if result is None:
        raise HTTPException(
            status_code=502,
            detail="Apify returned no data for this URL. Check that the URL is a valid public LinkedIn post.",
        )

    return LinkedInMetricsResponse(
        company_id          = company_id,
        linkedin_post_url   = payload.linkedin_post_url,
        linkedin_likes      = result["likes"],
        linkedin_reposts    = result["reposts"],
        linkedin_fetched_at = result["fetched_at"],
    )


# ── DM Drafting ───────────────────────────────────────────────────────────────

@router.post("/{company_id}/draft-dm", response_model=DmDraftResponse)
async def draft_dm_for_company(
    company_id: int,
    payload: DmToneRequest,
    db: Session = Depends(get_db),
):
    """Call OpenAI API and return a personalised outreach DM."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    total_funding  = sum(r.amount or 0 for r in company.funding_rounds)
    twitter_post   = next((p for p in company.launch_posts if p.platform == "twitter"),  None)
    linkedin_post  = next((p for p in company.launch_posts if p.platform == "linkedin"), None)

    try:
        dm_text = await dm_drafter.draft_dm(
            company_name   = company.name,
            description    = company.description,
            yc_batch       = company.yc_batch,
            total_funding  = total_funding,
            twitter_likes  = twitter_post.likes  if twitter_post  else None,
            linkedin_likes = linkedin_post.likes if linkedin_post else None,
            tone           = payload.tone or "professional",
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except APIError as exc:
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {exc.message}")

    return DmDraftResponse(
        company_id   = company.id,
        company_name = company.name,
        dm_text      = dm_text,
    )
