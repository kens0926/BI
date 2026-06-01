from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .models import Announcement, AuditPlan, AuditPlanStatus, AuditQuestion, Role, User
from .routers import announcements, audit_plans, audit_records, auth, corrective_actions, questions, reports
from .security import hash_password


APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"

app = FastAPI(
    title="Internal Audit Management System",
    description="FastAPI MVP built from AUD/ICP.MD",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def seed_initial_data(db: Session) -> None:
    if not db.query(User).filter(User.account == "admin").first():
        db.add(
            User(
                account="admin",
                password_hash=hash_password("admin123"),
                name="System Admin",
                role=Role.admin,
            )
        )

    if not db.query(Announcement).first():
        db.add(
            Announcement(
                title="內控稽核管理系統已啟用",
                content="請使用年度稽核計畫、題庫管理與查核記錄功能開始建立稽核作業。",
                is_pinned=True,
            )
        )

    if not db.query(AuditQuestion).first():
        db.add_all(
            [
                AuditQuestion(
                    cycle_name="採購循環",
                    question="採購申請是否經授權主管核准？",
                    procedure="抽查採購申請單與核准紀錄，確認授權層級符合規範。",
                    risk_description="未經授權採購可能造成舞弊或不當支出。",
                    regulation_reference="採購管理辦法",
                    department="採購部",
                ),
                AuditQuestion(
                    cycle_name="銷售循環",
                    question="客戶授信額度是否定期檢討？",
                    procedure="檢視授信清單、逾期帳款與最近一次檢討紀錄。",
                    risk_description="授信控管不足可能提高呆帳風險。",
                    regulation_reference="應收帳款管理辦法",
                    department="業務部",
                ),
            ]
        )

    if not db.query(AuditPlan).first():
        admin = db.query(User).filter(User.account == "admin").first()
        db.add(
            AuditPlan(
                task_no="AUD-2026-001",
                year=2026,
                cycle_name="採購循環",
                department="採購部",
                auditor_name="System Admin",
                auditor_id=admin.id if admin else None,
                status=AuditPlanStatus.pending,
            )
        )

    db.commit()


def migrate_schema() -> None:
    inspector = inspect(engine)
    if "audit_plans" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("audit_plans")}
    if "auditor_name" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE audit_plans ADD COLUMN auditor_name VARCHAR(100)"))


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.include_router(auth.router)
app.include_router(announcements.router)
app.include_router(audit_plans.router)
app.include_router(questions.router)
app.include_router(audit_records.router)
app.include_router(corrective_actions.router)
app.include_router(reports.router)
