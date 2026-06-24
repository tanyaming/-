from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.entities import Vehicle, VehicleRegulatoryBinding, VehicleVendorBinding
from app.schemas.common import VehicleCreate, VehicleDetailRead, VehicleRead, VehicleRegulatoryBindingCreate, VehicleRegulatoryBindingRead, VehicleVendorBindingCreate, VehicleVendorBindingRead

router = APIRouter()


@router.get("", response_model=list[VehicleDetailRead])
def list_vehicles(db: Session = Depends(get_db)) -> list[Vehicle]:
    return (
        db.query(Vehicle)
        .options(
            selectinload(Vehicle.vendor_bindings),
            selectinload(Vehicle.regulatory_bindings),
        )
        .order_by(Vehicle.id.desc())
        .all()
    )


@router.post("", response_model=VehicleRead)
def create_vehicle(payload: VehicleCreate, db: Session = Depends(get_db)) -> Vehicle:
    item = Vehicle(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{vehicle_id}", response_model=VehicleDetailRead)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)) -> Vehicle:
    item = (
        db.query(Vehicle)
        .options(
            selectinload(Vehicle.vendor_bindings),
            selectinload(Vehicle.regulatory_bindings),
            selectinload(Vehicle.latest_state),
        )
        .filter(Vehicle.id == vehicle_id)
        .one_or_none()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="vehicle not found")
    return item


@router.put("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(vehicle_id: int, payload: VehicleCreate, db: Session = Depends(get_db)) -> Vehicle:
    item = db.get(Vehicle, vehicle_id)
    if item is None:
        raise HTTPException(status_code=404, detail="vehicle not found")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{vehicle_id}/vendor-bindings", response_model=None)
def bind_vendor(
    vehicle_id: int, payload: VehicleVendorBindingCreate, db: Session = Depends(get_db)
) -> VehicleVendorBinding:
    if db.get(Vehicle, vehicle_id) is None:
        raise HTTPException(status_code=404, detail="vehicle not found")
    item = VehicleVendorBinding(vehicle_id=vehicle_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{vehicle_id}/regulatory-bindings", response_model=None)
def bind_regulatory(
    vehicle_id: int, payload: VehicleRegulatoryBindingCreate, db: Session = Depends(get_db)
) -> VehicleRegulatoryBinding:
    encoded = payload.regulatory_vehicle_no.encode("utf-8")
    if len(encoded) != 8:
        raise HTTPException(
            status_code=422,
            detail=f"监管车辆编号必须恰好8字节（UTF-8编码），格式 AABCDDDD，仅限数字和英文字母。当前输入 {len(payload.regulatory_vehicle_no)} 个字符，编码后 {len(encoded)} 字节"
        )
    if db.get(Vehicle, vehicle_id) is None:
        raise HTTPException(status_code=404, detail="vehicle not found")
    # 同一辆车+同一平台只能有一个绑定
    existing = (
        db.query(VehicleRegulatoryBinding)
        .filter(
            VehicleRegulatoryBinding.vehicle_id == vehicle_id,
            VehicleRegulatoryBinding.platform_id == payload.platform_id,
        )
        .one_or_none()
    )
    if existing:
        # 更新现有绑定
        for key, value in payload.model_dump().items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    item = VehicleRegulatoryBinding(vehicle_id=vehicle_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
