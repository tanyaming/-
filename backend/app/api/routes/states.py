from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import Vehicle, VehicleLatestState
from app.schemas.common import VehicleStateRead
from app.services.geocode import reverse_geocode
from app.services.state_store import persist_standard_state

router = APIRouter()


@router.get("/latest", response_model=list[VehicleStateRead])
def list_latest_states(db: Session = Depends(get_db)) -> list[dict]:
    states = db.query(VehicleLatestState).order_by(VehicleLatestState.updated_at.desc()).limit(500).all()
    # 批量加载车辆信息
    vehicle_ids = {s.vehicle_id for s in states}
    vehicle_map = {}
    if vehicle_ids:
        vehicles = db.query(Vehicle).filter(Vehicle.id.in_(vehicle_ids)).all()
        vehicle_map = {v.id: v for v in vehicles}
    
    result = []
    for s in states:
        v = vehicle_map.get(s.vehicle_id)
        addr = reverse_geocode(s.latitude, s.longitude) if s.latitude and s.longitude else None
        result.append({
            **s.__dict__,
            "vehicle_name": v.name if v else None,
            "vehicle_plate_no": v.plate_no if v else None,
            "address": addr,
        })
    return result


@router.get("/latest/{vehicle_id}", response_model=VehicleStateRead)
def get_latest_state(vehicle_id: int, db: Session = Depends(get_db)) -> VehicleLatestState:
    item = db.query(VehicleLatestState).filter(VehicleLatestState.vehicle_id == vehicle_id).one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="state not found")
    return item


@router.post("/ingest/{vendor_code}/{vehicle_id}", response_model=VehicleStateRead)
def ingest_state(
    vendor_code: str,
    vehicle_id: int,
    payload: dict[str, Any],
    vendor_id: int | None = None,
    db: Session = Depends(get_db),
) -> VehicleLatestState:
    try:
        return persist_standard_state(
            db,
            vehicle_id=vehicle_id,
            vendor_id=vendor_id,
            vendor_code=vendor_code,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
