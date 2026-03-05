from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import AppSettings
from schemas import AppSettingsRead, AppSettingsUpdate

router = APIRouter()


@router.get("/", response_model=AppSettingsRead)
def get_settings(db: Session = Depends(get_db)):
    row = db.query(AppSettings).first()
    if not row:
        raise HTTPException(status_code=404, detail="Settings not initialized")
    return row


@router.put("/", response_model=AppSettingsRead)
def update_settings(payload: AppSettingsUpdate, db: Session = Depends(get_db)):
    row = db.query(AppSettings).first()
    if not row:
        raise HTTPException(status_code=404, detail="Settings not initialized")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row
