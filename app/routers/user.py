from datetime import datetime
import re

from fastapi import APIRouter, Query, HTTPException, status
from typing import Annotated

from sqlmodel import select

from app.schemas import Role, UserBase, User, UserPublic, UserCreate, UserLogin
from app.services.database import SessionDependency

router = APIRouter()

@router.get("/users/citizens", response_model=list[UserPublic])
def get_citizens(session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[UserPublic]:
    citizens = session.exec(select(User).where(User.role == Role.CITIZEN).offset(offset).limit(limit)).all()
    return citizens

@router.get("/users/admins", response_model=list[UserPublic])
def get_admins(session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[UserPublic]:
    admins = session.exec(select(User).where(User.role == Role.ADMIN).offset(offset).limit(limit)).all()
    return admins

@router.get("/users/collectors", response_model=list[UserPublic])
def get_collectors(session: SessionDependency, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[UserPublic]:
    collectors = session.exec(select(User).where(User.role == Role.COLLECTOR).offset(offset).limit(limit)).all()
    return collectors

@router.post("/users/signup", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def signup_user(user_create: UserCreate, session: SessionDependency) -> UserPublic:
    user_create = UserCreate.model_validate(user_create)

    # email format validation already handled by EmailStr
    userdup = session.exec(select(User).where(User.email == str(user_create.email))).first()
    if userdup:
        raise HTTPException(status_code=422, detail="Email already exists")

    if user_create.password != user_create.password_confirm:
        raise HTTPException(status_code=422, detail="Passwords do not match")

    password_valid = re.search("^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[^A-Za-z\\d]).{8,}$", user_create.password)
    if not password_valid:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters long and have at least one of all the following: lowercase letter, uppercase letter, number, special character")

    user = User(
        firstname=user_create.firstname,
        lastname=user_create.lastname,
        email=user_create.email,
        role=user_create.role,
        password_hash="mock hash", # hash passwords properly according to the specifications of the authentication service
        date_created=datetime.utcnow()
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    return user

# the remaining endpoints need that authentication service to be available first

@router.post("/users/login")
def login_user(session: SessionDependency):
    ...

@router.post("/users/logout")
def logout_user(session: SessionDependency):
    # add authentication guards
    ...