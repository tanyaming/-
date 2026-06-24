from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import Vehicle, VehicleVendorBinding, VendorAccount
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


@router.delete("/{vendor_id}")
def delete_vendor(vendor_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    item = db.get(VendorAccount, vendor_id)
    if item is None:
        raise HTTPException(status_code=404, detail="vendor not found")
    # 删除关联的厂商绑定
    db.query(VehicleVendorBinding).filter(VehicleVendorBinding.vendor_id == vendor_id).delete()
    db.delete(item)
    db.commit()
    return {"status": "ok", "message": f"vendor {vendor_id} deleted"}


@router.post("/{vendor_id}/test-connection")
def test_vendor_connection(vendor_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    item = db.get(VendorAccount, vendor_id)
    if item is None:
        raise HTTPException(status_code=404, detail="vendor not found")
    adapter = build_vendor_adapter(item)
    return adapter.test_connection()


@router.post("/{vendor_id}/sync-vehicles")
def sync_vendor_vehicles(vendor_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    """从厂商拉取车辆列表，同步到中台车辆档案并建立绑定关系。"""
    item = db.get(VendorAccount, vendor_id)
    if item is None:
        raise HTTPException(status_code=404, detail="vendor not found")
    adapter = build_vendor_adapter(item)
    raw_vehicles = adapter.fetch_vehicle_list()

    created = 0
    updated = 0

    for v in raw_vehicles:
        # 兼容新石器 (vinId/vehicleId/vin) 和九识 (id/name/number/vin)
        vendor_vehicle_id = str(v.get("vinId") or v.get("vehicleId") or v.get("id") or v.get("vin") or "")
        if not vendor_vehicle_id:
            continue
        vin = v.get("vin")
        vehicle_name = v.get("vehicleName") or v.get("name") or ""
        plate_no = v.get("plateNumber") or v.get("plateNo") or v.get("number") or ""
        model = v.get("model") or ""
        brand = v.get("brand") or ("九识" if item.vendor_type == "jiushi" else "新石器")

        # 查找或创建车辆
        vehicle = None
        if vin:
            vehicle = db.query(Vehicle).filter(Vehicle.vin == vin).first()

        if vehicle is None:
            vehicle = Vehicle(
                name=vehicle_name or plate_no or vendor_vehicle_id,
                vin=vin,
                plate_no=plate_no or None,
                model=model or None,
                brand=brand,
                vehicle_category=v.get("vehicleCategory") or v.get("vehicleType") or None,
                power_type=v.get("powerType") or None,
                status="active",
            )
            db.add(vehicle)
            db.flush()
            created += 1
        else:
            updated += 1

        # 查找或创建厂商绑定
        existing_binding = (
            db.query(VehicleVendorBinding)
            .filter(
                VehicleVendorBinding.vehicle_id == vehicle.id,
                VehicleVendorBinding.vendor_id == vendor_id,
            )
            .first()
        )
        if existing_binding is None:
            binding = VehicleVendorBinding(
                vehicle_id=vehicle.id,
                vendor_id=vendor_id,
                vendor_vehicle_id=vendor_vehicle_id,
                vendor_vehicle_name=vehicle_name or None,
                vendor_vin=vin,
                is_primary=True,
            )
            db.add(binding)

    db.commit()
    return {"status": "ok", "count": len(raw_vehicles), "created": created, "updated": updated}

