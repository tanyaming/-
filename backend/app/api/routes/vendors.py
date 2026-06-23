from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import VendorAccount
from app.schemas.common import VendorAccountCreate, VendorAccountRead
from app.services.vendors.factory import build_vendor_adapter

router = APIRouter()


@router.get("", response_model=list[VendorAccountRead])
def list_vendors(db: Session = Depends(get_db)) -> list[VendorAccount]:
    return db.query(VendorAccount).order_by(VendorAccount.id.desc()).all()


@router.post("", response_model=VendorAccountRead)
def create_vendor(payload: VendorAccountCreate, db: Session = Depends(get_db)) -> VendorAccount:
    item = VendorAccount(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{vendor_id}", response_model=VendorAccountRead)
def get_vendor(vendor_id: int, db: Session = Depends(get_db)) -> VendorAccount:
    item = db.get(VendorAccount, vendor_id)
    if item is None:
        raise HTTPException(status_code=404, detail="vendor not found")
    return item


@router.put("/{vendor_id}", response_model=VendorAccountRead)
def update_vendor(vendor_id: int, payload: VendorAccountCreate, db: Session = Depends(get_db)) -> VendorAccount:
    item = db.get(VendorAccount, vendor_id)
    if item is None:
        raise HTTPException(status_code=404, detail="vendor not found")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{vendor_id}/test-connection")
def test_vendor_connection(vendor_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    item = db.get(VendorAccount, vendor_id)
    if item is None:
        raise HTTPException(status_code=404, detail="vendor not found")
    adapter = build_vendor_adapter(item)
    return adapter.test_connection()


@router.post("/{vendor_id}/sync-vehicles")
def sync_vendor_vehicles(vendor_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    item = db.get(VendorAccount, vendor_id)
    if item is None:
        raise HTTPException(status_code=404, detail="vendor not found")
    adapter = build_vendor_adapter(item)
    vehicles = adapter.fetch_vehicle_list()
    return {"status": "ok", "count": len(vehicles), "vehicles": vehicles}

