import os
import hashlib
from datetime import datetime, timedelta

import jwt

from fastapi import Depends
from typing import Annotated

from sqlmodel import select

from app.schemas import User
from .database import SessionDependency

# move to .env file in production
ITERATIONS = 694200
SECRET_SIGNATURE = "6308733e506b23bcb530d80642be4498798e5c99cec972b78816f27c38a0fb777018bd06c951e19dbb3b2ec1e1056408248da9d51b15d4a4a3af0d4dc3fe4d80"
TOKEN_EXPIRY_HOURS = 24

def hash_password(password: str) -> str:
    salt_bytes = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        ITERATIONS
    )
    return f"{salt_bytes.hex()}:{hash_bytes.hex()}"

def validate_credentials(email: str, password: str, session: SessionDependency) -> tuple[bool, str]:
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        return False, "Email is not associated with any user"

    stored_password_hash = user.password_hash

    salt, hash = stored_password_hash.split(":")
    salt_bytes, hash_bytes = bytes.fromhex(salt), bytes.fromhex(hash)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        ITERATIONS
    )

    correct_password = password_hash == hash_bytes

    if not correct_password:
        return False, "Incorrect password"

    return True, "Credentials are valid"

def get_token(email: str) -> str:
    payload = {
        "email": email,
        "expiry": (datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)).timestamp()
    }
    encoded_jwt = jwt.encode(payload, SECRET_SIGNATURE, algorithm="HS256")
    return encoded_jwt

# returns User object if token is not expired, else returns None
def get_user(token: str, session: SessionDependency) -> User | None:
    payload = jwt.decode(token, SECRET_SIGNATURE, algorithms=["HS256"])
    expiry = datetime.fromtimestamp(payload["expiry"])
    if datetime.utcnow() >= expiry:
        return None
    user = session.exec(select(User).where(User.email == payload["email"])).first()
    return user

CurrentUser = Annotated[User | None, Depends(get_user)]