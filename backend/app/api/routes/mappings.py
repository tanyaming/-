from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import EnumMappingRule, FieldMappingRule
from app.schemas.common import EnumMappingRuleCreate, MappingRuleCreate

router = APIRouter()


@router.get("/fields", response_model=None)
def list_field_mappings(db: Session = Depends(get_db)) -> list[FieldMappingRule]:
    return db.query(FieldMappingRule).order_by(FieldMappingRule.id.desc()).all()


@router.post("/fields", response_model=None)
def create_field_mapping(payload: MappingRuleCreate, db: Session = Depends(get_db)) -> FieldMappingRule:
    item = FieldMappingRule(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/enums", response_model=None)
def list_enum_mappings(db: Session = Depends(get_db)) -> list[EnumMappingRule]:
    return db.query(EnumMappingRule).order_by(EnumMappingRule.id.desc()).all()


@router.post("/enums", response_model=None)
def create_enum_mapping(payload: EnumMappingRuleCreate, db: Session = Depends(get_db)) -> EnumMappingRule:
    item = EnumMappingRule(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
