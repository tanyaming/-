from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import AlertEvent

router = APIRouter()


@router.get("", response_model=None)
def list_alerts(db: Session = Depends(get_db)) -> list[AlertEvent]:
    return db.query(AlertEvent).order_by(AlertEvent.id.desc()).limit(500).all()


@router.post("/{alert_id}/resolve", response_model=None)
def resolve_alert(alert_id: int, db: Session = Depends(get_db)) -> AlertEvent:
    item = db.get(AlertEvent, alert_id)
    if item is None:
        raise HTTPException(status_code=404, detail="alert not found")
    item.status = "resolved"
    item.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item
