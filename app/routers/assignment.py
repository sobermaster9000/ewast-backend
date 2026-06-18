from datetime import datetime

from fastapi import APIRouter, Query, HTTPException, status
from typing import Annotated

from sqlmodel import select

from app.schemas import AssignmentBase, Assignment, AssignmentPublic, AssignmentCreate, Role
from app.services.database import SessionDependency
from app.services import auth

router = APIRouter()

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
def accept_assignment(assignment_id: int, current_user: auth.CurrentUser, session: SessionDependency) -> AssignmentPublic:
    if current_user.role != Role.COLLECTOR:
        raise HTTPException(status_code=403, detail="Collector role required")
    assignment = session.get(Assignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    assignment_data = assignment.model_dump()
    assignment_data["is_started"] = True
    assignment.sqlmodel_update(assignment_data)
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
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