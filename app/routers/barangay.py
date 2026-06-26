from fastapi import APIRouter, Query, HTTPException, status
from typing import Annotated, Any

from sqlmodel import select

from app.schemas import BarangayBase, Barangay, BarangayPublic, BarangayCreate, Role, BarangayFloodRisk
from app.services.database import SessionDependency
from app.services import auth

import json

def _load_risk_scores_data() -> list[dict[str, Any]]:
    with open("app/data/barangay_flood_risks.davao_city.json", 'r') as file:
        return json.loads(file.read())

router = APIRouter()

@router.get("/barangays", response_model=list[BarangayPublic])
def get_barangays(session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[BarangayPublic]:
    barangays = session.exec(select(Barangay).offset(offset).limit(limit)).all()
    return barangays

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

@router.get("/barangays/floodrisks", response_model=list[BarangayFloodRisk])
def get_barangay_risk_scores(session: SessionDependency) -> list[BarangayFloodRisk]:
    risk_scores = []
    try:
        risk_scores = _load_risk_scores_data()
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not load barangay flood risks data: {error}")

    results = []
    for item in risk_scores:
        barangay = session.exec(select(Barangay).where(Barangay.name == item["barangay_name"])).first()
        if not barangay:
            continue
        results.append(BarangayFloodRisk(
            barangay_id=barangay.barangay_id,
            barangay_name=item["barangay_name"],
            flood_risk=item["risk_score"],
            normalized_flood_risk=item["normalized_risk_score"]
        ))

    return results

@router.get("/barangays/{barangay_id}", response_model=BarangayPublic)
def get_barangay(barangay_id: int, session: SessionDependency) -> BarangayPublic:
    barangay = session.get(Barangay, barangay_id)
    if not barangay:
        raise HTTPException(status_code=404, detail="Barangay not found")
    return barangay

@router.get("/barangays/floodrisk/{barangay_id}", response_model=BarangayFloodRisk)
def get_barangay_risk_score(barangay_id: int, session: SessionDependency) -> BarangayFloodRisk:
    barangay = session.get(Barangay, barangay_id)
    if not barangay:
        raise HTTPException(status_code=404, detail=f"Barangay with ID {barangay_id} not found")

    risk_scores = []
    try:
        risk_scores = _load_risk_scores_data()
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Could not load flood risks data: {error}")

    data = None
    for item in risk_scores:
        if item["barangay_name"] == barangay.name:
            data = item
            break

    if not data:
        raise HTTPException(status_code=404, detail=f"Could not find barangay with ID {barangay_id} in flood risks data")

    result = BarangayFloodRisk(
        barangay_id=barangay.barangay_id,
        barangay_name=barangay.name,
        flood_risk=data["risk_score"],
        normalized_flood_risk=data["normalized_risk_score"]
    )

    return result