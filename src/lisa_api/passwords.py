
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from lisa.identity.models import User
from lisa.memory.user_context.repository_models import (
    UserCredentialModel,
    UserSessionModel,
)
from pwdlib import PasswordHash
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from lisa_api.dependencies import DatabaseSession, get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["passwords"],
)

password_hash = PasswordHash.recommended()


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=12, max_length=1024)


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    session: DatabaseSession,
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    credential = await session.scalar(
        select(UserCredentialModel).where(
            UserCredentialModel.user_id == user.id
        )
    )

    if credential is None or not password_hash.verify(
        payload.current_password,
        credential.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from the current password",
        )

    credential.password_hash = password_hash.hash(payload.new_password)
    credential.password_updated_at = datetime.now(UTC)
    await session.execute(
        update(UserSessionModel)
        .where(
            UserSessionModel.user_id == user.id,
            UserSessionModel.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )

    return {"message": "Password changed successfully"}
