from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import AuditRecord, CorrectiveAction, CorrectiveActionStatus, User
from ..schemas import ApiResponse, CorrectiveActionCreate, CorrectiveActionRead, CorrectiveActionUpdate

router = APIRouter(prefix="/api/corrective-actions", tags=["corrective-actions"])


@router.get("", response_model=ApiResponse)
def list_corrective_actions(
    status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    query = db.query(CorrectiveAction)
    if status:
        query = query.filter(CorrectiveAction.status == status)
    rows = query.order_by(CorrectiveAction.due_date.asc()).all()
    return ApiResponse(
        message="Data retrieved successfully",
        data=[CorrectiveActionRead.model_validate(row) for row in rows],
    )


@router.post("", response_model=ApiResponse)
def create_corrective_action(
    payload: CorrectiveActionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    if not db.get(AuditRecord, payload.audit_record_id):
        raise HTTPException(status_code=404, detail="Audit record not found")
    row = CorrectiveAction(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApiResponse(message="Corrective action created", data=CorrectiveActionRead.model_validate(row))


@router.put("/{action_id}", response_model=ApiResponse)
def update_corrective_action(
    action_id: str,
    payload: CorrectiveActionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    row = db.get(CorrectiveAction, action_id)
    if not row:
        raise HTTPException(status_code=404, detail="Corrective action not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    if payload.status == CorrectiveActionStatus.closed:
        row.verified_by = user.id
        row.verified_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return ApiResponse(message="Corrective action updated", data=CorrectiveActionRead.model_validate(row))

