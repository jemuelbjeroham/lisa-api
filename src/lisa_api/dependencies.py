
import hashlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, status
from lisa.identity.models import User
from lisa.memory.user_context.repository_models import (
    UserProfileModel,
    UserSessionModel,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

SESSION_COOKIE_NAME = "lisa_session"


async def get_db_session(request: Request):
    lisa = request.app.state.lisa

    async with lisa.database.session() as session:
        yield session


DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(
    session: DatabaseSession,
    session_token: Annotated[
        str | None,
        Cookie(alias=SESSION_COOKIE_NAME),
    ] = None,
) -> User:
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    token_hash = hashlib.sha256(session_token.encode()).hexdigest()
    now = datetime.now(UTC)

    result = await session.execute(
        select(UserSessionModel, UserProfileModel)
        .join(
            UserProfileModel,
            UserProfileModel.user_id == UserSessionModel.user_id,
        )
        .where(
            UserSessionModel.token_hash == token_hash,
            UserSessionModel.revoked_at.is_(None),
            UserSessionModel.expires_at > now,
            UserProfileModel.is_active.is_(True),
        )
    )

    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    _, profile = row

    return User(
        id=profile.user_id,
        display_name=profile.display_name,
    )


async def get_current_admin(
    user: Annotated[User, Depends(get_current_user)],
    session: DatabaseSession,
) -> User:
    result = await session.execute(
        select(UserProfileModel.is_admin).where(
            UserProfileModel.user_id == user.id,
            UserProfileModel.is_active.is_(True),
        )
    )

    is_admin = result.scalar_one_or_none()

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )

    return user
