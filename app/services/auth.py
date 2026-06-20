import os
import hashlib
import secrets
from datetime import datetime, timedelta

import jwt

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated

from sqlmodel import select

from app.schemas import User
from .database import SessionDependency
from app.config import settings

token_security = HTTPBearer()

def hash_password(password: str) -> str:
    salt_bytes = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        settings.HASHING_ITERATIONS
    )
    return f"{salt_bytes.hex()}:{hash_bytes.hex()}"

def get_token_from_credentials(email: str, password: str, session: SessionDependency) -> str:
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=400, detail="Email is not associated with a user")

    stored_password_hash = user.password_hash

    salt, hash = stored_password_hash.split(":")
    salt_bytes, hash_bytes = bytes.fromhex(salt), bytes.fromhex(hash)
    new_hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        settings.HASHING_ITERATIONS
    )

    if not secrets.compare_digest(hash_bytes, new_hash_bytes):
        raise HTTPException(status_code=400, detail="Incorrect password")

    payload = {
        "email": email,
        "creation": datetime.utcnow().timestamp()
    }
    token = jwt.encode(payload, settings.JWT_SIGNATURE, algorithm="HS256")

    return token

def get_user_from_token(credentials: Annotated[HTTPAuthorizationCredentials, Depends(token_security)], session: SessionDependency) -> User:
    token = credentials.credentials
    payload = jwt.decode(token, settings.JWT_SIGNATURE, algorithms=["HS256"])
    email, creation = payload.get("email"), payload.get("creation")

    if email is None or creation is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    if datetime.utcnow() >= datetime.fromtimestamp(creation) + timedelta(hours=settings.TOKEN_EXPIRY_HOURS):
        raise HTTPException(status_code=401, detail="Access token is invalid")

    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Could not get user from token")

    if creation <= user.reject_tokens_before_timestamp:
        raise HTTPException(status_code=401, detail="Access token is invalid")

    return user

def update_token_rejection_timestamp(user: User, session: SessionDependency) -> None:
    user_data = user.model_dump()
    user_data["reject_tokens_before_timestamp"] = datetime.utcnow().timestamp()
    user.sqlmodel_update(user_data)
    session.add(user)
    session.commit()
    session.refresh(user)

CurrentUser = Annotated[User, Depends(get_user_from_token)]