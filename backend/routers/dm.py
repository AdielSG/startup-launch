"""
DM drafting router — superseded by POST /companies/{id}/draft-dm in launches.py.
Kept as a stub; not registered in main.py.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Company
from schemas import DmDraftRequest, DmDraftResponse

router = APIRouter()


@router.post("/draft", response_model=DmDraftResponse)
def draft_dm(payload: DmDraftRequest, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == payload.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Stub — real implementation is in services/dm_drafter.py
    dm_text = (
        f"Hi {company.name} team, I noticed your recent launch "
        f"and wanted to reach out. [DM drafter not yet implemented — Module 3]"
    )
    return DmDraftResponse(
        company_id=company.id,
        company_name=company.name,
        dm_text=dm_text,
    )
