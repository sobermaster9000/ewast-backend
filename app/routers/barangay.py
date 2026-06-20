from fastapi import APIRouter, Query, HTTPException, status
from typing import Annotated

from sqlmodel import select

from app.schemas import BarangayBase, Barangay, BarangayPublic, BarangayCreate, Role
from app.services.database import SessionDependency
from app.services import auth

router = APIRouter()

@router.get("/barangays", response_model=list[BarangayPublic])
def get_barangays(session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[BarangayPublic]:
    barangays = session.exec(select(Barangay).offset(offset).limit(limit)).all()
    return barangays

@router.get("/barangays/{barangay_id}", response_model=BarangayPublic)
def get_barangay(barangay_id: int, session: SessionDependency) -> BarangayPublic:
    barangay = session.get(Barangay, barangay_id)
    if not barangay:
        raise HTTPException(status_code=404, detail="Barangay not found")
    return barangay

# @router.post("/barangays/create", response_model=BarangayPublic, status_code=status.HTTP_201_CREATED)
# def create_barangay(barangay_create: BarangayCreate, current_user: auth.CurrentUser, session: SessionDependency) -> BarangayPublic:
#     if current_user.role != Role.ADMIN:
#         raise HTTPException(status_code=403, detail="Admin role required")
#     barangay_create = BarangayCreate.model_validate(barangay_create)
#     barangay = Barangay(
#         name=barangay_create.name,
#         bounds_coords=barangay_create.bounds_coords
#     )
#     session.add(barangay)
#     session.commit()
#     session.refresh(barangay)
#     return barangay