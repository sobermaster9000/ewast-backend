from fastapi import APIRouter, Query, HTTPException, status
from typing import Annotated

from sqlmodel import select

import datetime as dt

from app.schemas import Announcement, AnnouncementCreate, AnnouncementPublic, Role, Detail
from app.services import auth
from app.services.database import SessionDependency

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)

# return all announcements
@router.get("/", response_model=list[AnnouncementPublic])
def get_announcements(
    session: SessionDependency,
    current_user: auth.CurrentActiveUser,
    offset: int = 0,
    limit: Annotated[int, Query(le=25)] = 25
) -> list[AnnouncementPublic]:
    announcements = session.exec(select(Announcement).offset(offset).limit(limit)).all()
    return announcements

@router.get("/barangay/{barangay_id}", response_model=list[AnnouncementPublic])
def get_announcements_for_barangay(
    session: SessionDependency,
    barangay_id: int
) -> list[AnnouncementPublic]:
    announcements = session.exec(select(Announcement).where(Announcement.under_barangay_id == barangay_id)).all()
    return announcements

@router.get("/{announcement_id}", response_model=AnnouncementPublic)
def get_announcement(
    session: SessionDependency,
    announcement_id: int
) -> AnnouncementPublic:
    announcement = session.get(Announcement, announcement_id)
    if not announcement: raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement

@router.post("/create", response_model=AnnouncementPublic, status_code=status.HTTP_201_CREATED)
def create_announcement(
    session: SessionDependency,
    current_user: auth.CurrentActiveUser,
    announcement_create: AnnouncementCreate
) -> AnnouncementPublic:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")
    announcement = Announcement(
        title=announcement_create.title,
        content=announcement_create.content,
        announced_by_user_id=current_user.user_id,
        date_published=dt.date.today(),
        under_barangay_id=current_user.assigned_barangay_id,
        image_url=announcement_create.image_url
    )
    session.add(announcement)
    session.commit()
    session.refresh(announcement)
    return announcement

@router.get("/{announcement_id}/delete", response_model=Detail)
def delete_announcement(
    session: SessionDependency,
    current_user: auth.CurrentActiveUser,
    announcement_id: int
) -> Detail:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")
    announcement = session.get(Announcement, announcement_id)
    if not announcement: raise HTTPException(status_code=404, detail="Announcement not found")
    session.delete(announcement)
    session.commit()
    return Detail(detail="Successfully deleted announcement")