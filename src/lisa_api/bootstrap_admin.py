
import asyncio
import getpass
import os
import sys
from datetime import UTC, datetime
from uuid import uuid4

from lisa.config import Settings
from lisa.infrastructure.postgres.database import Database
from lisa.memory.user_context.repository_models import (
    UserCredentialModel,
    UserProfileModel,
)
from pwdlib import PasswordHash
from sqlalchemy import func, select

password_hash = PasswordHash.recommended()


async def create_first_admin(
    name: str,
    email: str,
    password: str,
) -> None:
    # Settings also requires the model-provider API key, which this
    # database-only command does not use.
    os.environ.setdefault("OPENAI_API_KEY", "bootstrap-unused")

    settings = Settings()
    database = Database(settings)

    try:
        async with database.session() as session:
            existing_admin = await session.scalar(
                select(UserProfileModel.user_id)
                .where(UserProfileModel.is_admin.is_(True))
                .limit(1)
            )

            if existing_admin is not None:
                raise RuntimeError(
                    "An administrator already exists. "
                    "Bootstrap is only for the first administrator."
                )

            normalized_email = email.strip().lower()

            existing_user = await session.scalar(
                select(UserProfileModel.user_id).where(
                    func.lower(UserProfileModel.email) == normalized_email
                )
            )

            if existing_user is not None:
                raise RuntimeError(
                    "An account with this email already exists."
                )

            now = datetime.now(UTC)
            user_id = uuid4()

            profile = UserProfileModel(
                user_id=user_id,
                display_name=name.strip(),
                email=normalized_email,
                is_active=True,
                is_admin=True,
                details={},
                created_at=now,
                updated_at=now,
            )

            credential = UserCredentialModel(
                user_id=user_id,
                password_hash=password_hash.hash(password),
                password_updated_at=now,
            )

            session.add(profile)
            await session.flush()  # Ensure user_profiles is inserted first.

            session.add(credential)
            await session.flush()

        print(f"Administrator created successfully: {normalized_email}")

    finally:
        await database.close()


def main() -> None:
    print("LISA — First Administrator Setup")
    print("--------------------------------")

    name = input("Administrator name: ").strip()
    email = input("Administrator email: ").strip()

    if not name or not email or "@" not in email:
        print("A valid name and email are required.", file=sys.stderr)
        raise SystemExit(1)

    password = getpass.getpass("Password (minimum 12 characters): ")
    confirmation = getpass.getpass("Confirm password: ")

    if len(password) < 12:
        print("Password must be at least 12 characters.", file=sys.stderr)
        raise SystemExit(1)

    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        raise SystemExit(1)

    try:
        asyncio.run(create_first_admin(name, email, password))
    except RuntimeError as exc:
        print(f"Bootstrap refused: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    
    except (OSError, ValueError):
        print(
            "Administrator creation failed. Check database configuration "
            "and application logs.",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
