from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import RegulatoryPlatform
from app.schemas.common import RegulatoryPlatformCreate, RegulatoryPlatformRead

router = APIRouter()


@router.get("", response_model=list[RegulatoryPlatformRead])
def list_platforms(db: Session = Depends(get_db)) -> list[RegulatoryPlatform]:
    return db.query(RegulatoryPlatform).order_by(RegulatoryPlatform.id.desc()).all()


@router.post("", response_model=RegulatoryPlatformRead)
def create_platform(payload: RegulatoryPlatformCreate, db: Session = Depends(get_db)) -> RegulatoryPlatform:
    item = RegulatoryPlatform(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{platform_id}", response_model=RegulatoryPlatformRead)
def get_platform(platform_id: int, db: Session = Depends(get_db)) -> RegulatoryPlatform:
    item = db.get(RegulatoryPlatform, platform_id)
    if item is None:
        raise HTTPException(status_code=404, detail="platform not found")
    return item


@router.put("/{platform_id}", response_model=RegulatoryPlatformRead)
def update_platform(
    platform_id: int, payload: RegulatoryPlatformCreate, db: Session = Depends(get_db)
) -> RegulatoryPlatform:
    item = db.get(RegulatoryPlatform, platform_id)
    if item is None:
        raise HTTPException(status_code=404, detail="platform not found")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

