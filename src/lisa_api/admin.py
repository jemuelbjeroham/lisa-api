import secrets
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from lisa.identity.models import User
from lisa.memory.user_context.repository_models import (
    UserCredentialModel,
    UserProfileModel,
    UserSessionModel,
)
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from lisa_api.dependencies import DatabaseSession, get_current_admin

router = APIRouter(prefix="/admin/users", tags=["admin-users"])
password_hash = PasswordHash.recommended()


class CreateUserRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    is_admin: bool = False
    password: str | None = Field(default=None, min_length=12, max_length=128)


class UserResponse(BaseModel):
    user_id: UUID
    display_name: str | None
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    temporary_password: str | None = None


class UpdateUserRequest(BaseModel):
    is_active: bool


class UpdateRoleRequest(BaseModel):
    is_admin: bool


class ResetPasswordResponse(BaseModel):
    user_id: UUID
    email: str
    temporary_password: str


def _generate_password() -> str:
    """Generate a high-entropy temporary password."""
    return secrets.token_urlsafe(18)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: CreateUserRequest,
    session: DatabaseSession,
    admin: Annotated[User, Depends(get_current_admin)],
) -> UserResponse:
    email = str(payload.email).strip().lower()
    display_name = payload.display_name.strip()
    if not display_name:
        raise HTTPException(status_code=422, detail="Display name cannot be empty")

    existing_user = await session.scalar(
        select(UserProfileModel.user_id).where(func.lower(UserProfileModel.email) == email)
    )
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    now = datetime.now(UTC)
    user_id = uuid4()
    temporary_secret = payload.password or _generate_password()
    profile = UserProfileModel(
        user_id=user_id,
        display_name=display_name,
        email=email,
        is_active=True,
        is_admin=payload.is_admin,
        details={},
        created_at=now,
        updated_at=now,
    )
    credential = UserCredentialModel(
        user_id=user_id,
        password_hash=password_hash.hash(temporary_secret),
        password_updated_at=now,
    )

    # The credential has a foreign-key dependency on the profile/user row.
    try:
        session.add(profile)
        await session.flush()
        session.add(credential)
        await session.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="The user could not be created; the email may already exist",
        ) from exc

    return UserResponse(
        user_id=user_id,
        display_name=display_name,
        email=email,
        is_active=True,
        is_admin=profile.is_admin,
        created_at=now,
        temporary_password=temporary_secret,
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    session: DatabaseSession,
    admin: Annotated[User, Depends(get_current_admin)],
) -> list[UserResponse]:
    result = await session.scalars(
        select(UserProfileModel).order_by(UserProfileModel.created_at.desc())
    )
    return [
        UserResponse(
            user_id=profile.user_id,
            display_name=profile.display_name,
            email=profile.email or "",
            is_active=profile.is_active,
            is_admin=profile.is_admin,
            created_at=profile.created_at,
        )
        for profile in result.all()
    ]


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: UpdateUserRequest,
    session: DatabaseSession,
    admin: Annotated[User, Depends(get_current_admin)],
) -> UserResponse:
    profile = await session.get(UserProfileModel, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="User not found")
    if profile.user_id == admin.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    profile.is_active = payload.is_active
    profile.updated_at = datetime.now(UTC)
    if not payload.is_active:
        await session.execute(
            update(UserSessionModel)
            .where(
                UserSessionModel.user_id == profile.user_id,
                UserSessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    return UserResponse(
        user_id=profile.user_id,
        display_name=profile.display_name,
        email=profile.email or "",
        is_active=profile.is_active,
        is_admin=profile.is_admin,
        created_at=profile.created_at,
    )


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: UUID,
    payload: UpdateRoleRequest,
    session: DatabaseSession,
    admin: Annotated[User, Depends(get_current_admin)],
) -> UserResponse:
    profile = await session.get(UserProfileModel, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="User not found")
    if profile.user_id == admin.id and not payload.is_admin:
        raise HTTPException(status_code=400, detail="You cannot remove your own admin role")

    profile.is_admin = payload.is_admin
    profile.updated_at = datetime.now(UTC)
    return UserResponse(
        user_id=profile.user_id,
        display_name=profile.display_name,
        email=profile.email or "",
        is_active=profile.is_active,
        is_admin=profile.is_admin,
        created_at=profile.created_at,
    )


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_user_password(
    user_id: UUID,
    session: DatabaseSession,
    admin: Annotated[User, Depends(get_current_admin)],
) -> ResetPasswordResponse:
    profile = await session.get(UserProfileModel, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="User not found")

    credential = await session.get(UserCredentialModel, user_id)
    if credential is None:
        raise HTTPException(status_code=404, detail="User credentials not found")

    temporary_secret = _generate_password()
    now = datetime.now(UTC)
    credential.password_hash = password_hash.hash(temporary_secret)
    credential.password_updated_at = now
    await session.execute(
        update(UserSessionModel)
        .where(
            UserSessionModel.user_id == user_id,
            UserSessionModel.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    return ResetPasswordResponse(
        user_id=user_id,
        email=profile.email or "",
        temporary_password=temporary_secret,
    )
