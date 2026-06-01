from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import current_user
from ..models import Announcement, User
from ..schemas import AnnouncementCreate, AnnouncementRead, ApiResponse

router = APIRouter(prefix="/api/announcements", tags=["announcements"])


@router.get("", response_model=ApiResponse)
def list_announcements(db: Session = Depends(get_db), _: User = Depends(current_user)):
    rows = (
        db.query(Announcement)
        .filter(Announcement.is_published.is_(True))
        .order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc())
        .all()
    )
    return ApiResponse(message="Data retrieved successfully", data=[AnnouncementRead.model_validate(row) for row in rows])


@router.post("", response_model=ApiResponse)
def create_announcement(payload: AnnouncementCreate, db: Session = Depends(get_db), _: User = Depends(current_user)):
    row = Announcement(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApiResponse(message="Announcement created", data=AnnouncementRead.model_validate(row))

