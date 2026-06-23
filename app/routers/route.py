from fastapi import APIRouter, Query, HTTPException, status
from typing import Annotated

from sqlmodel import select

import datetime as dt

from app.schemas import RouteBase, Route, RoutePublic, RouteCreate, RouteTripRequest, Role
from app.schemas.route import RouteTripRequestBarangay
from app.services.database import SessionDependency
from app.services import auth, routing

router = APIRouter()

@router.get("/routes", response_model=list[RoutePublic])
def get_routes(session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[RoutePublic]:
    routes = session.exec(select(Route).offset(offset).limit(limit)).all()
    return routes

@router.get("/routes/{route_id}", response_model=RoutePublic)
def get_route(session: SessionDependency, route_id: int) -> RoutePublic:
    route = session.get(Route, route_id)
    if not route: raise HTTPException(status_code=404, detail="Route not found")
    return route

@router.post("/routes/create", response_model=RoutePublic, status_code=status.HTTP_201_CREATED)
def create_route(current_user: auth.CurrentUser, session: SessionDependency, route_create: RouteCreate) -> RoutePublic:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")

    route_create = RouteCreate.model_validate(route_create)
    route = Route(
        waypoints = route_create.waypoints
    )
    session.add(route)
    session.commit()
    session.refresh(route)
    return route

@router.post("/routes/trip", response_model=RoutePublic, status_code=status.HTTP_201_CREATED)
def create_route_trip(current_user: auth.CurrentUser, session: SessionDependency, trip_request: RouteTripRequest) -> RoutePublic:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")

    trip_request = RouteTripRequest.model_validate(trip_request)
    try:
        route_waypoints = routing.generate_unapproved_route_waypoints(
            start=trip_request.start,
            end=trip_request.end,
            report_locations=trip_request.report_locations,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    route = Route(waypoints=route_waypoints)
    session.add(route)
    session.commit()
    session.refresh(route)
    return route

@router.post("/routes/trip/barangay/{barangay_id}", response_model=RoutePublic, status_code=status.HTTP_201_CREATED)
def create_route_trip_for_barangay(current_user: auth.CurrentUser, session: SessionDependency, trip_request_barangay: RouteTripRequestBarangay) -> RoutePublic:
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")

    trip_request_barangay = RouteTripRequestBarangay.model_validate(trip_request_barangay)
    try:
        route_waypoints = routing.generate_unapproved_route_waypoints_for_barangay(
            start=trip_request_barangay.start,
            end=trip_request_barangay.end,
            barangay_id=trip_request_barangay.barangay_id
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"An error occured trying to generate the route trip: {error}")

    route = Route(waypoints=route_waypoints, for_barangay_id=trip_request_barangay.barangay_id)
    session.add(route)
    session.commit()
    session.refresh(route)
    return route

@router.get("/routes/suggest", response_model=list[RoutePublic])
def suggest_routes(current_user: auth.CurrentUser, session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[RoutePublic]:
    if current_user.role != Role.ADMIN:
            raise HTTPException(status_code=403, detail="Admin role required")
    routes = session.exec(select(Route).offset(offset).limit(limit).where(Route.is_approved == False))
    return routes

@router.get("/routes/approve/{route_id}", response_model=RoutePublic)
def approve_route(current_user: auth.CurrentUser, session: SessionDependency, route_id: int) -> RoutePublic:
    if current_user.role != Role.ADMIN:
            raise HTTPException(status_code=403, detail="Admin role required")
    route = session.get(Route, route_id)
    if not route: raise HTTPException(status_code=404, detail="Route not found")
    route_data = route.model_dump()
    route_data['is_approved'] = True
    route_data['date_approved'] = dt.date.today()
    route.sqlmodel_update(route_data)
    session.add(route)
    session.commit()
    session.refresh(route)
    return route

@router.get("/routes/delete/{route_id}", response_model=RoutePublic)
def delete_route(current_user: auth.CurrentUser, session: SessionDependency, route_id: int) -> RoutePublic:
    if current_user.role != Role.ADMIN:
            raise HTTPException(status_code=403, detail="Admin role required")
    route = session.get(Route, route_id)
    if not route: raise HTTPException(status_code=404, detail="Route not found")
    session.delete(route)
    session.commit()
    return {
        "status_code": 204
    }
