from datetime import datetime, timedelta

from fastapi import APIRouter, Query, HTTPException, status, BackgroundTasks
from typing import Annotated

from sqlmodel import select, Session

from app.schemas import AssignmentBase, Assignment, AssignmentPublic, AssignmentCreate, Role
from app.services.database import SessionDependency, db_engine
from app.services import auth, notifications

import asyncio
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

async def schedule_deadline_notification(assignment_id: int, notification_time: datetime):
    wait_time = (notification_time - datetime.utcnow()).total_seconds()
    if wait_time > 0:
        await asyncio.sleep(wait_time)

    with Session(db_engine) as session:
        assignment = session.get(Assignment, assignment_id)
        if not assignment or assignment.is_completed:
            return

        if not assignment.assigned_to_user_id or not assignment.deadline:
            return

        title = "Trash collection deadline approaching"
        message = (
            f"Your assignment is due at {assignment.deadline.isoformat()} UTC. "
            "Please finish trash collection within the next 30 minutes."
        )
        notifications.create_notification(
            session=session,
            assignment_id=assignment.assignment_id,
            user_id=assignment.assigned_to_user_id,
            title=title,
            message=message,
        )

        try:
            notifications.notify_user_by_email(
                session=session,
                user_id=assignment.assigned_to_user_id,
                title=title,
                message=message,
            )
        except Exception as error:
            logger.error(f"Failed to send deadline email for assignment {assignment_id}: {error}")

    

@router.get("/assignments", response_model=list[AssignmentPublic])
def get_assignments(session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[AssignmentPublic]:
    assignments = session.exec(select(Assignment).offset(offset).limit(limit)).all()
    return assignments

@router.get("/assignments/{assignment_id}", response_model=AssignmentPublic)
def get_assignment(assignment_id: int, session: SessionDependency) -> AssignmentPublic:
    assignment = session.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment

@router.get("/assignments/collector/{collector_id}", response_model=list[AssignmentPublic])
def get_assignments_collector(collector_id: int, session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[AssignmentPublic]:
    reports = session.exec(select(Assignment).where(Assignment.assigned_to_user_id == collector_id).offset(offset).limit(limit)).all()
    return reports

@router.post("/assignments/create", response_model=AssignmentPublic, status_code=status.HTTP_201_CREATED)
def create_assignment(assignment_create: AssignmentCreate, current_user: auth.CurrentUser, session: SessionDependency) -> AssignmentPublic:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")
    assignment_create = AssignmentCreate.model_validate(assignment_create)
    assignment = Assignment(
        assigned_to_user_id=assignment_create.assigned_to_user_id,
        route_id=assignment_create.route_id,
        date_assigned=datetime.utcnow()
    )
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    return assignment

@router.get("/assignments/accept/{assignment_id}", response_model=AssignmentPublic)
def accept_assignment(assignment_id: int, current_user: auth.CurrentUser, session: SessionDependency, background_tasks: BackgroundTasks) -> AssignmentPublic:
    if current_user.role != Role.COLLECTOR:
        raise HTTPException(status_code=403, detail="Collector role required")
    assignment = session.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    assignment_data = assignment.model_dump()
    assignment_data["is_started"] = True
    assignment_data["deadline"] = datetime.utcnow() + timedelta(hours=4)
    assignment_data["is_tracked_by_admin"] = True
    assignment.sqlmodel_update(assignment_data)
    session.add(assignment)
    session.commit()
    session.refresh(assignment)

    if hasattr(assignment, "deadline") and assignment.deadline:
        now = datetime.utcnow()
        notification_time = assignment.deadline - timedelta(minutes=30)
        if notification_time < now:
            notification_time = now

        background_tasks.add_task(schedule_deadline_notification, assignment_id, notification_time)
    return assignment

@router.get("/assignments/complete/{assignment_id}", response_model=AssignmentPublic)
def complete_assignment(assignment_id: int, current_user: auth.CurrentUser, session: SessionDependency) -> AssignmentPublic:
    if current_user.role != Role.COLLECTOR:
        raise HTTPException(status_code=403, detail="Collector role required")
    assignment = session.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    assignment_data = assignment.model_dump()
    assignment_data["is_completed"] = True
    assignment_data["date_completed"] = datetime.utcnow()
    assignment.sqlmodel_update(assignment_data)
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    return assignment