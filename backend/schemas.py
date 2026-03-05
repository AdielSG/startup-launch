from datetime import date as Date, datetime
from typing import List, Optional

from pydantic import BaseModel, computed_field


# ── Funding Round ─────────────────────────────────────────────────────────────

class FundingRoundBase(BaseModel):
    amount:     Optional[float] = None
    round_type: Optional[str]   = None  # pre-seed | seed | series_a …
    date:       Optional[Date]  = None
    source:     Optional[str]   = None  # yc | crunchbase | manual …
    note:       Optional[str]   = None


class FundingRoundCreate(FundingRoundBase):
    company_id: int


class FundingRoundRead(FundingRoundBase):
    id: int
    company_id: int

    model_config = {"from_attributes": True}


# ── Launch Post ───────────────────────────────────────────────────────────────

class LaunchPostBase(BaseModel):
    platform: str                     # twitter | linkedin | hackernews
    post_url: Optional[str] = None
    likes: Optional[int] = None
    reposts: Optional[int] = None
    date: Optional[Date] = None


class LaunchPostCreate(LaunchPostBase):
    company_id: int


class LaunchPostRead(LaunchPostBase):
    id: int
    company_id: int

    model_config = {"from_attributes": True}


class LaunchPostUpdate(BaseModel):
    post_url: Optional[str] = None
    likes: Optional[int] = None
    reposts: Optional[int] = None
    date: Optional[Date] = None


# ── Contact ───────────────────────────────────────────────────────────────────

class ContactBase(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    x_handle: Optional[str] = None


class ContactCreate(ContactBase):
    company_id: int


class ContactRead(ContactBase):
    id: int
    company_id: int

    model_config = {"from_attributes": True}


# ── Company ───────────────────────────────────────────────────────────────────

class CompanyBase(BaseModel):
    name:          str
    domain:        Optional[str] = None
    description:   Optional[str] = None
    founded_year:  Optional[int] = None
    yc_batch:      Optional[str] = None
    funding_stage: Optional[str] = None  # "Early" | "Growth" | "Public"


class CompanyCreate(CompanyBase):
    pass


class CompanyRead(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    linkedin_post_url:   Optional[str]      = None
    linkedin_likes:      Optional[int]      = None
    linkedin_reposts:    Optional[int]      = None
    linkedin_fetched_at: Optional[datetime] = None
    funding_rounds: List[FundingRoundRead] = []
    launch_posts:   List[LaunchPostRead]   = []
    contacts:       List[ContactRead]      = []

    @computed_field
    @property
    def total_funding(self) -> float:
        return sum(r.amount or 0 for r in self.funding_rounds)

    model_config = {"from_attributes": True}


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    founded_year: Optional[int] = None
    yc_batch: Optional[str] = None


# ── App Settings ──────────────────────────────────────────────────────────────

class AppSettingsRead(BaseModel):
    id: int
    twitter_likes_threshold: int
    linkedin_likes_threshold: int

    model_config = {"from_attributes": True}


class AppSettingsUpdate(BaseModel):
    twitter_likes_threshold: Optional[int] = None
    linkedin_likes_threshold: Optional[int] = None


# ── DM Drafting ───────────────────────────────────────────────────────────────

class DmDraftRequest(BaseModel):
    company_id: int
    tone: Optional[str] = "professional"


# Body for POST /companies/{id}/draft-dm  (company_id comes from the path)
class DmToneRequest(BaseModel):
    tone: Optional[str] = "professional"


class DmDraftResponse(BaseModel):
    company_id: int
    company_name: str
    dm_text: str


# ── LinkedIn Scraping ──────────────────────────────────────────────────────────

class LinkedInUrlRequest(BaseModel):
    linkedin_post_url: str


class LinkedInMetricsResponse(BaseModel):
    company_id:          int
    linkedin_post_url:   str
    linkedin_likes:      int
    linkedin_reposts:    int
    linkedin_fetched_at: datetime
