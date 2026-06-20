import os
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, status, BackgroundTasks
from typing import Annotated

from sqlmodel import select

from app.schemas import ReportType, ReportBase, Report, ReportPublic, ReportCreate, ReportFormFields, Role, Barangay
from app.services.database import SessionDependency
from app.services import auth
from app.services import report_analysis

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
    current_user: auth.CurrentUser,
    session: SessionDependency,
    background_tasks: BackgroundTasks,
    form_data: ReportFormFields = Depends(ReportFormFields.as_form),
    image: UploadFile = File(...)
) -> ReportPublic:
    if current_user.role != Role.CITIZEN:
        raise HTTPException(status_code=403, detail="Citizen role required")

    reported_by_user_id = current_user.user_id
    if not reported_by_user_id:
        raise HTTPException(status_code=500, detail="An error occured while trying to get user ID")

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

    report = Report(
        type=form_data.type,
        notes=form_data.notes,
        latitude=form_data.latitude,
        longitude=form_data.longitude,
        reported_by_user_id=reported_by_user_id,
        under_barangay_id=report_analysis.get_barangay_id_of_loc(form_data.latitude, form_data.longitude),
        image_url=f"static/uploads/{unique_filename}",
        is_collected=False,
        date_reported=datetime.utcnow()
    )

    session.add(report)
    session.commit()
    session.refresh(report)

    if report.report_id:
        background_tasks.add_task(
            func=report_analysis.process_ai_report_analysis,
            report_id=report.report_id
        )

    return report

@router.get("/reports/general/summary")
def get_reports_summary(current_user: auth.CurrentUser, session: SessionDependency):
    ### uncomment if restricted to admin only ###
    # if current_user.role != Role.ADMIN:
    #     raise HTTPException(status_code=403, detail="Admin role required")
    try:
        general_summary = report_analysis.get_general_report_analysis()
        return {
            "general_summary": general_summary
        }
    except:
        raise HTTPException(status_code=400, detail="An error occured while trying to get the general summary")

@router.get("/reports/summary/barangay/{barangay_id}", response_model=None)
def get_reports_summary_barangay(barangay_id: int, current_user: auth.CurrentUser, session: SessionDependency):
    ### uncomment if restricted to admin only ###
    # if current_user.role != Role.ADMIN:
    #     raise HTTPException(status_code=403, detail="Admin role required")
    try:
        barangay_summary = report_analysis.get_barangay_report_analysis(barangay_id)
        return {
            "barangay_id": barangay_id,
            "barangay_summary": barangay_summary
        }
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"An error occured while trying to get the barangay summary: {error}")

@router.get("/reports/stats", response_model=None)
def get_report_stats(current_user: auth.CurrentUser, session: SessionDependency):
    report_count = report_analysis.get_report_count()
    report_density = report_analysis.get_report_density()
    densest_barangays = report_analysis.get_densest_barangays()
    report_type_freq = report_analysis.get_report_type_freq()
    report_themes = report_analysis.get_report_themes()

    stats = {
        "report_count": report_count,
        "report_density": report_density,
        "densest_barangays": densest_barangays,
        "report_type_freq": report_type_freq,
        "report_themes": report_themes,
        "barangay_stats": []
    }

    barangays = session.exec(select(Barangay)).all()
    for barangay in barangays:
        barangay_stats = report_analysis.get_barangay_report_stats(barangay.barangay_id)
        stats["barangay_stats"].append(barangay_stats)

    return stats

@router.get("/reports/stats/barangay/{barangay_id}", response_model=None)
def get_barangay_report_stats(barangay_id: int, current_user: auth.CurrentUser, session: SessionDependency):
    ...