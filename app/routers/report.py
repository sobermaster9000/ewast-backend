import os
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, status
from typing import Annotated

from sqlmodel import select

from app.schemas import ReportType, ReportBase, Report, ReportPublic, ReportCreate, ReportFormFields
from app.services.database import SessionDependency

router = APIRouter()

@router.get("/reports", response_model=list[ReportPublic])
def get_reports(session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[ReportPublic]:
    reports = session.exec(select(Report).offset(offset).limit(limit)).all()
    return reports

@router.get("/reports/pending", response_model=list[ReportPublic])
def get_pending_reports(session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[ReportPublic]:
    reports = session.exec(select(Report).offset(offset).limit(limit).where(Report.is_collected == False)).all()
    return reports

@router.get("/reports/{report_id}", response_model=ReportPublic)
def get_report(report_id: int, session: SessionDependency) -> ReportPublic:
    report = session.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router.get("/reports/user/{user_id}", response_model=list[ReportPublic])
def get_reports_from_user(user_id: int, session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[ReportPublic]:
    reports = session.exec(select(Report).where(Report.reported_by_user_id == user_id).offset(offset).limit(limit)).all()
    return reports

@router.get("/reports/types", response_model=list[str])
def get_report_types() -> list[str]:
    return [x.value for x in ReportType]

@router.post("/reports/create", response_model=ReportPublic, status_code=status.HTTP_201_CREATED)
async def create_report(
    session: SessionDependency,
    form_data: ReportFormFields = Depends(ReportFormFields.as_form),
    image: UploadFile = File(...)
) -> ReportPublic:
        # add authentication guards

        # get current user and assign id to reported_by_user_id
        reported_by_user_id = 0

        # change to storage server in production
        upload_dir = "static/uploads"
        os.makedirs(upload_dir, exist_ok=True)

        file_extension = os.path.splitext(image.filename)[1]
        unique_filename = f"{int(datetime.utcnow().timestamp())}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)

        try:
             contents = await image.read()
             with open(file_path, "wb") as f:
                 f.write(contents)
        except Exception:
             raise HTTPException(status_code=500, detail="Failed to save uplaoded image")
        finally:
             await image.close()

        # update when ai integration service is available
        mock_ai_summary = "Skibidi sigma AI summary"

        report = Report(
            type=form_data.type,
            notes=form_data.notes,
            latitude=form_data.latitude,
            longitude=form_data.longitude,
            reported_by_user_id=reported_by_user_id,
            image_url=f"/static/uploads/{unique_filename}",
            is_collected=False,
            ai_summary=mock_ai_summary,
            date_reported=datetime.utcnow()
        )

        session.add(report)
        session.commit()
        session.refresh(report)

        return report

# the remaining endpoints need the ai integration service to be available first

@router.get("/reports/summary")
def get_reports_summary(session: SessionDependency):
    # add authentication guards
    ...

@router.get("/reports/summary/{barangay_id}")
def get_reports_summary_barangay(barangay_id: int, session: SessionDependency):
    # add authentication guards
    ...