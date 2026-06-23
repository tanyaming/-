"""证书管理 API：上传、列表、删除"""

import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import VehicleCertificate
from app.schemas.common import CertificateRead

router = APIRouter()


def _compute_fingerprint(file_path: Path) -> str:
    """计算证书文件 SHA256 指纹"""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha.update(chunk)
    return sha.hexdigest()


@router.get("", response_model=list[CertificateRead])
def list_certificates(db: Session = Depends(get_db)):
    return db.query(VehicleCertificate).order_by(VehicleCertificate.id.desc()).all()


@router.get("/{cert_id}", response_model=CertificateRead)
def get_certificate(cert_id: int, db: Session = Depends(get_db)):
    item = db.get(VehicleCertificate, cert_id)
    if item is None:
        raise HTTPException(status_code=404, detail="certificate not found")
    return item


@router.post("/upload", response_model=CertificateRead)
def upload_certificate(
    name: str = Form(...),
    vehicle_id: int | None = Form(None),
    cert_file: UploadFile = File(..., alias="certificate"),
    key_file: UploadFile | None = File(None, alias="private_key"),
    ca_file: UploadFile | None = File(None, alias="ca_certificate"),
    db: Session = Depends(get_db),
):
    """上传车辆 TLS 证书、私钥、CA 证书"""
    settings = get_settings()

    if not cert_file.filename:
        raise HTTPException(status_code=422, detail="certificate file is required")

    # 存储目录: storage/certificates/{vehicle_id}/
    subdir = str(vehicle_id) if vehicle_id else "unbound"
    target_dir = settings.cert_storage_path / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    # 保存证书文件
    cert_path = target_dir / cert_file.filename
    with open(cert_path, "wb") as f:
        f.write(cert_file.file.read())
    fingerprint = _compute_fingerprint(cert_path)

    # 保存私钥
    key_path = None
    if key_file and key_file.filename:
        key_path = target_dir / key_file.filename
        with open(key_path, "wb") as f:
            f.write(key_file.file.read())

    # 保存 CA 证书
    ca_path = None
    if ca_file and ca_file.filename:
        ca_path = target_dir / ca_file.filename
        with open(ca_path, "wb") as f:
            f.write(ca_file.file.read())

    item = VehicleCertificate(
        name=name,
        vehicle_id=vehicle_id,
        certificate_path=str(cert_path),
        private_key_path=str(key_path) if key_path else None,
        ca_certificate_path=str(ca_path) if ca_path else None,
        fingerprint=fingerprint,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{cert_id}", response_model=CertificateRead)
def update_certificate(
    cert_id: int,
    name: str | None = Form(None),
    vehicle_id: int | None = Form(None),
    is_enabled: bool | None = Form(None),
    db: Session = Depends(get_db),
):
    """更新证书元数据"""
    item = db.get(VehicleCertificate, cert_id)
    if item is None:
        raise HTTPException(status_code=404, detail="certificate not found")
    if name is not None:
        item.name = name
    if vehicle_id is not None:
        item.vehicle_id = vehicle_id
    if is_enabled is not None:
        item.is_enabled = is_enabled
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{cert_id}")
def delete_certificate(cert_id: int, db: Session = Depends(get_db)):
    """删除证书（同时删除文件）"""
    item = db.get(VehicleCertificate, cert_id)
    if item is None:
        raise HTTPException(status_code=404, detail="certificate not found")

    # 删除文件
    for p in [item.certificate_path, item.private_key_path, item.ca_certificate_path]:
        if p:
            path = Path(p)
            if path.exists():
                path.unlink()

    db.delete(item)
    db.commit()
    return {"status": "deleted"}
