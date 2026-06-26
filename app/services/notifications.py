from datetime import datetime
from email.message import EmailMessage
import math
import smtplib
from sqlmodel import select
from app.schemas import Notification, Report, Route, User
from app.services.database import SessionDependency
from app.config import settings

from app.services.geocoding import reverse_geocode


def send_email(to_email: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise RuntimeError("SMTP settings are not configured")

    port = settings.SMTP_PORT or (465 if settings.SMTP_USE_SSL else 587)
    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    if settings.SMTP_USE_SSL:
        smtp_class = smtplib.SMTP_SSL
    else:
        smtp_class = smtplib.SMTP

    with smtp_class(host=settings.SMTP_HOST, port=port, timeout=settings.SMTP_TIMEOUT_SECONDS) as smtp:
        if not settings.SMTP_USE_SSL and settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    '''
    SYNOPSIS: Returns the distance in meters.

    The Haversine distance is used to calculate the shortest distance 
    of two waypoints given their latitude and longitude.

    '''
    radius = 6371000.0 # radius of earth in meters
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def _closest_route_waypoint_distance(route_waypoints: list[tuple[float, float]], report_lat: float, report_lon: float) -> tuple[float, int]:
    best_distance = float("inf")
    best_index = -1
    for index, (lat, lon) in enumerate(route_waypoints):
        distance = _haversine_distance(report_lat, report_lon, lat, lon)
        if distance < best_distance:
            best_distance = distance
            best_index = index
    return best_distance, best_index


def create_notification(session: SessionDependency, assignment_id: int, user_id: int, title: str, message: str) -> Notification:
    notification = Notification(
        assignment_id=assignment_id,
        user_id=user_id,
        title=title,
        message=message,
        is_read=False,
        created_at=datetime.utcnow()
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification


def get_user_notifications(session: SessionDependency, user_id: int) -> list[Notification]:
    return session.exec(select(Notification).where(Notification.user_id == user_id)).all()


def notify_user_by_email(session: SessionDependency, user_id: int, title: str, message: str) -> None:
    user = session.get(User, user_id)
    if not user or not user.email:
        raise RuntimeError("Cannot send email: user email not found")
    send_email(user.email, title, message)


def notify_citizens_route_approved(session: SessionDependency, route_id: int, max_distance_meters: float = 200.0) -> None:
    route = session.get(Route, route_id)
    if not route or not route.waypoints:
        return

    uncollected_reports = session.exec(select(Report).where(Report.is_collected == False)).all()
    collected_reports = session.exec(select(Report).where(Report.is_collected == True)).all()
    if route.for_barangay_id is not None:
        uncollected_reports = [report for report in uncollected_reports if report.under_barangay_id == route.for_barangay_id]
        collected_reports = [report for report in collected_reports if report.under_barangay_id == route.for_barangay_id]

    if not uncollected_reports:
        return

    route_waypoints = route.waypoints
    collected_report_indices = []
    for report in collected_reports:
        _, idx = _closest_route_waypoint_distance(route_waypoints, report.latitude, report.longitude)
        if idx >= 0:
            collected_report_indices.append(idx)

    for report in uncollected_reports:
        distance, index = _closest_route_waypoint_distance(route_waypoints, report.latitude, report.longitude)
        if distance > max_distance_meters:
            continue

        heading_from_prior = any(prior_index < index for prior_index in collected_report_indices)
        title = "Route approved near your reported trash"
        message = (
            f"A collector route has been approved near your reported trash at "
            f"({report.latitude}, {report.longitude}). "
        )
        if heading_from_prior:
            message += "The collector is expected to approach your location from a prior collection point."
        else:
            message += "The team is scheduled to pass through the area soon."

        create_notification(
            session=session,
            assignment_id=0,
            user_id=report.reported_by_user_id,
            title=title,
            message=message,
        )

        try:
            notify_user_by_email(
                session=session,
                user_id=report.reported_by_user_id,
                title=title,
                message=message,
            )
        except Exception:
            pass
