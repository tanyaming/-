from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import ConnectionStatus, RegulatoryReportLog

router = APIRouter()


@router.get("/logs", response_model=None)
def list_report_logs(db: Session = Depends(get_db)) -> list[RegulatoryReportLog]:
    return db.query(RegulatoryReportLog).order_by(RegulatoryReportLog.id.desc()).limit(500).all()


@router.get("/connections", response_model=None)
def list_connection_status(db: Session = Depends(get_db)) -> list[ConnectionStatus]:
    return db.query(ConnectionStatus).order_by(ConnectionStatus.updated_at.desc()).limit(500).all()
