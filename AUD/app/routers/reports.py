from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import (
    AuditPlan,
    AuditPlanStatus,
    AuditQuestion,
    AuditRecord,
    AuditResultType,
    CorrectiveAction,
    CorrectiveActionStatus,
    User,
)
from ..schemas import ApiResponse, DashboardStats

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/dashboard", response_model=ApiResponse)
def dashboard(db: Session = Depends(get_db), _: User = Depends(current_user)):
    stats = DashboardStats(
        audit_plan_count=db.query(AuditPlan).count(),
        open_plan_count=db.query(AuditPlan)
        .filter(AuditPlan.status.in_([AuditPlanStatus.draft, AuditPlanStatus.pending, AuditPlanStatus.in_progress]))
        .count(),
        question_count=db.query(AuditQuestion).filter(AuditQuestion.enabled.is_(True)).count(),
        audit_record_count=db.query(AuditRecord).count(),
        corrective_action_count=db.query(CorrectiveAction).count(),
        open_corrective_action_count=db.query(CorrectiveAction)
        .filter(CorrectiveAction.status != CorrectiveActionStatus.closed)
        .count(),
        car_count=db.query(AuditRecord).filter(AuditRecord.result_type == AuditResultType.car).count(),
        ofi_count=db.query(AuditRecord).filter(AuditRecord.result_type == AuditResultType.ofi).count(),
    )
    return ApiResponse(message="Data retrieved successfully", data=stats)

