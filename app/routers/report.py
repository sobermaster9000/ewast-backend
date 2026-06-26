import os
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, status, BackgroundTasks
from typing import Annotated

from sqlmodel import select

from app.schemas import ReportType, ReportBase, Report, ReportPublic, ReportCreate, ReportFormFields, Role, Barangay, BarangayStatistics, Statistics, GeneralSummary, BarangaySummary, Theme, ReportTypeFreq, ReportCount, ReportDensity
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

@router.get("/reports/types", response_model=list[str])
def get_report_types() -> list[str]:
    return [x.value for x in ReportType]

@router.get("/reports/type/{report_type}", response_model=list[ReportPublic])
def get_reports_by_type(
    session: SessionDependency,
    report_type: str,
    offset: int = 0,
    limit: Annotated[int, Query(le=50)] = 50
) -> list[ReportPublic]:
    if report_type not in [x.value for x in ReportType]:
        raise HTTPException(status_code=404, detail="Report type not found")
    reports = session.exec(select(Report).where(Report.type == report_type).offset(offset).limit(limit)).all()
    return reports

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

    barangay_id = report_analysis.get_barangay_id_of_loc(form_data.latitude, form_data.longitude)

    from app.services.geocoding import reverse_geocode
    address = reverse_geocode(form_data.latitude, form_data.longitude)
    if not address:
        if barangay_id:
            barangay = session.get(Barangay, barangay_id)
            if barangay:
                address = f"Barangay {barangay.name}, Philippines"
        if not address:
            address = "Unknown Address"

    report = Report(
        type=form_data.type,
        notes=form_data.notes,
        latitude=form_data.latitude,
        longitude=form_data.longitude,
        address=address,
        report_themes=[],
        reported_by_user_id=reported_by_user_id,
        under_barangay_id=barangay_id,
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

@router.get("/reports/general/summary", response_model=GeneralSummary)
def get_reports_summary(current_user: auth.CurrentUser, session: SessionDependency) -> GeneralSummary:
    ### uncomment if restricted to admin only ###
    # if current_user.role != Role.ADMIN:
    #     raise HTTPException(status_code=403, detail="Admin role required")
    try:
        general_summary = report_analysis.get_general_report_analysis()
        return GeneralSummary(general_summary=general_summary)
    except:
        raise HTTPException(status_code=400, detail="An error occured while trying to get the general summary")

@router.get("/reports/stats", response_model=Statistics)
def get_report_stats(current_user: auth.CurrentUser, session: SessionDependency) -> Statistics:
    report_count = report_analysis.get_report_count()
    report_density = report_analysis.get_report_density()
    barangays_with_most_reports = report_analysis.get_barangays_with_most_reports()
    report_type_freq = report_analysis.get_report_type_freq()
    report_themes = report_analysis.get_report_themes()

    stats = Statistics(
        report_count=report_count,
        report_density_sq_m=report_density,
        barangays_with_most_reports=barangays_with_most_reports,
        report_type_freq=report_type_freq,
        report_themes=report_themes,
        barangay_stats=[]
    )

    barangays = session.exec(select(Barangay)).all()
    for barangay in barangays:
        barangay_report_count = report_analysis.get_report_count(barangay.barangay_id)
        barangay_report_density = report_analysis.get_report_density(barangay.barangay_id)
        barangay_report_type_freq = report_analysis.get_report_type_freq(barangay.barangay_id)
        barangay_report_themes = report_analysis.get_report_themes(barangay.barangay_id)
        barangay_stats = BarangayStatistics(
            barangay_name=barangay.name,
            report_count=barangay_report_count,
            report_density_sq_m=barangay_report_density,
            report_type_freq=barangay_report_type_freq,
            report_themes=barangay_report_themes
        )
        stats.barangay_stats.append(barangay_stats)

    return stats

@router.get("/reports/stats/count", response_model=int)
def get_count_report_stat() -> int:
    return report_analysis.get_report_count()

@router.get("/reports/stats/density-rankings", response_model=list[ReportDensity])
def get_density_rankings_stat(session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[ReportDensity]:
    barangays = session.exec(select(Barangay)).all()
    results = []
    for barangay in barangays:
        results.append(ReportDensity(
            barangay_id=barangay.barangay_id,
            barangay_name=barangay.name,
            report_density_sq_m=report_analysis.get_report_density(barangay.barangay_id)
        ))
    return sorted(results, key=lambda x:x.report_density_sq_m, reverse=True)[offset:offset+limit]

@router.get("/reports/stats/most-reports", response_model=list[ReportCount])
def get_barangays_with_most_reports_stat() -> list[ReportCount]:
    return sorted(report_analysis.get_barangays_with_most_reports(), key=lambda x:x.count, reverse=True)

@router.get("/reports/stats/type-freq", response_model=list[ReportTypeFreq])
def get_report_type_freq_stat() -> list[ReportTypeFreq]:
    return report_analysis.get_report_type_freq()

@router.get("/reports/stats/report-themes", response_model=list[Theme])
def get_report_themes_stat() -> list[Theme]:
    return report_analysis.get_report_themes()

@router.get("/reports/geocode/reverse", response_model=dict[str, str])
def get_address_from_coordinates(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180)
) -> dict[str, str]:
    from app.services.geocoding import reverse_geocode
    address = reverse_geocode(latitude, longitude)
    if not address:
        raise HTTPException(status_code=400, detail="Failed to reverse geocode coordinates")
    return {"address": address}

@router.get("/reports/{report_id}", response_model=ReportPublic)
def get_report(report_id: int, session: SessionDependency) -> ReportPublic:
    report = session.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router.get("/reports/{report_id}/address", response_model=dict[str, str])
def get_report_address(report_id: int, session: SessionDependency) -> dict[str, str]:
    report = session.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # If address is already saved, return it
    if report.address:
        return {"address": report.address}

    # Otherwise, resolve it now, save it, and return it
    from app.services.geocoding import reverse_geocode
    address = reverse_geocode(report.latitude, report.longitude)
    if not address:
        if report.under_barangay_id:
            barangay = session.get(Barangay, report.under_barangay_id)
            if barangay:
                address = f"Barangay {barangay.name}, Philippines"
        if not address:
            address = "Unknown Address"

    report.address = address
    session.add(report)
    session.commit()
    session.refresh(report)

    return {"address": address}

@router.get("/reports/user/{user_id}", response_model=list[ReportPublic])
def get_reports_from_user(user_id: int, session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[ReportPublic]:
    reports = session.exec(select(Report).where(Report.reported_by_user_id == user_id).offset(offset).limit(limit)).all()
    return reports

@router.get("/reports/summary/barangay/{barangay_id}", response_model=BarangaySummary)
def get_reports_summary_barangay(barangay_id: int, current_user: auth.CurrentUser, session: SessionDependency) -> BarangaySummary:
    ### uncomment if restricted to admin only ###
    # if current_user.role != Role.ADMIN:
    #     raise HTTPException(status_code=403, detail="Admin role required")
    try:
        barangay_summary = report_analysis.get_barangay_report_analysis(barangay_id)
        return BarangaySummary(barangay_id=barangay_id, barangay_summary=barangay_summary)
    except Exception as error:
        raise HTTPException(status_code=400, detail=f"An error occured while trying to get the barangay summary: {error}")

@router.get("/reports/stats/barangay/{barangay_id}", response_model=BarangayStatistics)
def get_barangay_report_stats(barangay_id: int, current_user: auth.CurrentUser, session: SessionDependency) -> BarangayStatistics:
    barangay = session.get(Barangay, barangay_id)
    if not barangay:
        raise HTTPException(status_code=404, detail=f"Could not find barangay with ID {barangay_id}")
    report_count = report_analysis.get_report_count(barangay_id)
    report_density = report_analysis.get_report_density(barangay_id)
    report_type_freq = report_analysis.get_report_type_freq(barangay_id)
    report_themes = report_analysis.get_report_themes(barangay_id)
    stats = BarangayStatistics(
        barangay_name=barangay.name,
        report_count=report_count,
        report_density_sq_m=report_density,
        report_type_freq=report_type_freq,
        report_themes=report_themes
    )
    return stats