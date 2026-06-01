from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import AuditPlanStatus, AuditResultType, CorrectiveActionStatus, Role


class ApiResponse(BaseModel):
    success: bool = True
    message: str
    data: object | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserRead"


class UserCreate(BaseModel):
    account: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6)
    name: str
    role: Role = Role.viewer


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=6)
    name: str | None = None
    role: Role | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    account: str
    name: str
    role: Role
    created_at: datetime


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    is_pinned: bool = False
    is_published: bool = True


class AnnouncementRead(AnnouncementCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class AuditPlanCreate(BaseModel):
    task_no: str
    year: int
    cycle_name: str
    department: str
    auditor_name: str | None = None
    auditor_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: AuditPlanStatus = AuditPlanStatus.draft


class AuditPlanUpdate(BaseModel):
    task_no: str | None = None
    year: int | None = None
    cycle_name: str | None = None
    department: str | None = None
    auditor_name: str | None = None
    auditor_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: AuditPlanStatus | None = None


class AuditPlanRead(AuditPlanCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class AuditQuestionCreate(BaseModel):
    cycle_name: str
    question: str
    procedure: str
    risk_description: str
    regulation_reference: str | None = None
    department: str
    enabled: bool = True


class AuditQuestionUpdate(BaseModel):
    cycle_name: str | None = None
    question: str | None = None
    procedure: str | None = None
    risk_description: str | None = None
    regulation_reference: str | None = None
    department: str | None = None
    enabled: bool | None = None


class AuditQuestionRead(AuditQuestionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class AuditRecordCreate(BaseModel):
    audit_plan_id: str
    question_id: str
    result_type: AuditResultType
    finding: str | None = None
    suggestion: str | None = None
    attachment_path: str | None = None


class AuditRecordUpdate(BaseModel):
    audit_plan_id: str | None = None
    question_id: str | None = None
    result_type: AuditResultType | None = None
    finding: str | None = None
    suggestion: str | None = None
    attachment_path: str | None = None


class AuditRecordRead(AuditRecordCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_by: str
    created_at: datetime


class CorrectiveActionCreate(BaseModel):
    audit_record_id: str
    responsible_department: str
    due_date: date
    action_description: str
    evidence_path: str | None = None
    status: CorrectiveActionStatus = CorrectiveActionStatus.open


class CorrectiveActionUpdate(BaseModel):
    responsible_department: str | None = None
    due_date: date | None = None
    action_description: str | None = None
    evidence_path: str | None = None
    status: CorrectiveActionStatus | None = None


class CorrectiveActionRead(CorrectiveActionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    verified_by: str | None
    verified_at: datetime | None
    created_at: datetime


class DashboardStats(BaseModel):
    audit_plan_count: int
    open_plan_count: int
    question_count: int
    audit_record_count: int
    corrective_action_count: int
    open_corrective_action_count: int
    car_count: int
    ofi_count: int
