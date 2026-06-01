import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def uuid_string() -> str:
    return str(uuid.uuid4())


class Role(str, enum.Enum):
    admin = "Admin"
    audit_manager = "Audit Manager"
    auditor = "Auditor"
    department_user = "Department User"
    viewer = "Viewer"


class AuditPlanStatus(str, enum.Enum):
    draft = "Draft"
    pending = "Pending"
    in_progress = "In Progress"
    completed = "Completed"
    closed = "Closed"


class AuditResultType(str, enum.Enum):
    car = "CAR"
    ofi = "OFI"
    obs = "OBS"
    na = "NA"
    pass_ = "PASS"


class CorrectiveActionStatus(str, enum.Enum):
    open = "Open"
    processing = "Processing"
    pending_verify = "Pending Verify"
    closed = "Closed"


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    account: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.viewer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    audit_plans: Mapped[list["AuditPlan"]] = relationship(back_populates="auditor")


class AuditPlan(Base):
    __tablename__ = "audit_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    task_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    cycle_name: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    auditor_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    auditor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[AuditPlanStatus] = mapped_column(
        Enum(AuditPlanStatus), default=AuditPlanStatus.draft, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    auditor: Mapped[User | None] = relationship(back_populates="audit_plans")
    records: Mapped[list["AuditRecord"]] = relationship(back_populates="audit_plan")


class AuditQuestion(Base):
    __tablename__ = "audit_question_bank"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    cycle_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    procedure: Mapped[str] = mapped_column(Text, nullable=False)
    risk_description: Mapped[str] = mapped_column(Text, nullable=False)
    regulation_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    records: Mapped[list["AuditRecord"]] = relationship(back_populates="question")


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    audit_plan_id: Mapped[str] = mapped_column(ForeignKey("audit_plans.id"), nullable=False)
    question_id: Mapped[str] = mapped_column(ForeignKey("audit_question_bank.id"), nullable=False)
    result_type: Mapped[AuditResultType] = mapped_column(Enum(AuditResultType), nullable=False)
    finding: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    audit_plan: Mapped[AuditPlan] = relationship(back_populates="records")
    question: Mapped[AuditQuestion] = relationship(back_populates="records")
    corrective_actions: Mapped[list["CorrectiveAction"]] = relationship(back_populates="audit_record")


class CorrectiveAction(Base):
    __tablename__ = "corrective_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    audit_record_id: Mapped[str] = mapped_column(ForeignKey("audit_records.id"), nullable=False)
    responsible_department: Mapped[str] = mapped_column(String(100), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    action_description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[CorrectiveActionStatus] = mapped_column(
        Enum(CorrectiveActionStatus), default=CorrectiveActionStatus.open, nullable=False
    )
    verified_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    audit_record: Mapped[AuditRecord] = relationship(back_populates="corrective_actions")
