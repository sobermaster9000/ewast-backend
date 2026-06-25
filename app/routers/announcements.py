from fastapi import APIRouter, Query, HTTPException, status, Depends, UploadFile, File
from typing import Annotated

from sqlmodel import select

import datetime as dt
import os

from app.schemas import Announcement, AnnouncementCreate, AnnouncementPublic, Role, Detail, AnnouncementFormFields
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
    current_user: auth.CurrentUser,
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
async def create_announcement(
    session: SessionDependency,
    current_user: auth.CurrentUser,
    form_data: AnnouncementFormFields = Depends(AnnouncementFormFields.as_form),
    image: UploadFile = File(...),
) -> AnnouncementPublic:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")

    announced_by_user_id = current_user.user_id
    if not announced_by_user_id:
        raise HTTPException(status_code=500, detail="An error occured while trying to get user ID")

    barangay_id = current_user.assigned_barangay_id
    if not barangay_id:
        raise HTTPException(status_code=400, detail="User is not assigned to any barangay")

    upload_dir = "static/uploads"
    os.makedirs(upload_dir, exist_ok=True)

    file_extension = os.path.splitext(image.filename)[1]
    unique_filename = f"{int(dt.datetime.now().timestamp())}{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)

    try:
        contents = await image.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save uplaoded image")
    finally:
        await image.close()

    announcement = Announcement(
        title=form_data.title,
        content=form_data.content,
        announced_by_user_id=announced_by_user_id,
        date_published=dt.datetime.now(),
        under_barangay_id=barangay_id,
        image_url=f"static/uploads/{unique_filename}",
    )
    session.add(announcement)
    session.commit()
    session.refresh(announcement)
    return announcement

@router.get("/{announcement_id}/delete", response_model=Detail)
def delete_announcement(
    session: SessionDependency,
    current_user: auth.CurrentUser,
    announcement_id: int
) -> Detail:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")
    announcement = session.get(Announcement, announcement_id)
    if not announcement: raise HTTPException(status_code=404, detail="Announcement not found")
    session.delete(announcement)
    session.commit()
    return Detail(detail="Successfully deleted announcement")