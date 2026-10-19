
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from lisa.identity.models import User
from lisa.memory.user_context.repository_models import (
    UserCredentialModel,
    UserProfileModel,
    UserSessionModel,
)
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from lisa_api.dependencies import DatabaseSession, get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])
password_hash = PasswordHash.recommended()

SESSION_COOKIE_NAME = "lisa_session"
SESSION_DURATION = timedelta(days=7)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class CurrentUserResponse(BaseModel):
    id: str
    display_name: str | None
    email: str
    is_admin: bool


@router.post("/login")
async def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    session: DatabaseSession,
) -> dict[str, str]:
    email = str(payload.email).strip().lower()

    result = await session.execute(
        select(UserProfileModel, UserCredentialModel)
        .join(
            UserCredentialModel,
            UserCredentialModel.user_id == UserProfileModel.user_id,
        )
        .where(UserProfileModel.email == email)
    )
    row = result.first()

    # Use the same public error for unknown users and incorrect passwords.
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    profile, credential = row

    if not profile.is_active or not password_hash.verify(
        payload.password,
        credential.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    now = datetime.now(UTC)

    session.add(
        UserSessionModel(
            id=uuid4(),
            user_id=profile.user_id,
            token_hash=token_hash,
            expires_at=now + SESSION_DURATION,
        )
    )

    # Persist the session before returning the cookie.
    await session.flush()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=int(SESSION_DURATION.total_seconds()),
        path="/",
    )

    return {"message": "Login successful"}


@router.post("/logout")
async def logout(
    response: Response,
    session: DatabaseSession,
    session_token: Annotated[
        str | None,
        Cookie(alias=SESSION_COOKIE_NAME),
    ] = None,
) -> dict[str, str]:
    if session_token:
        token_hash = hashlib.sha256(session_token.encode()).hexdigest()

        result = await session.execute(
            select(UserSessionModel).where(
                UserSessionModel.token_hash == token_hash,
                UserSessionModel.revoked_at.is_(None),
            )
        )
        db_session = result.scalar_one_or_none()

        if db_session is not None:
            db_session.revoked_at = datetime.now(UTC)

    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
    )

    return {"message": "Logout successful"}


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(
    user: Annotated[User, Depends(get_current_user)],
    session: DatabaseSession,
) -> CurrentUserResponse:
    result = await session.execute(
        select(UserProfileModel).where(
            UserProfileModel.user_id == user.id,
        )
    )
    profile = result.scalar_one()

    return CurrentUserResponse(
        id=str(profile.user_id),
        display_name=profile.display_name,
        email=profile.email or "",
        is_admin=profile.is_admin,
    )
