from fastapi import Request
from lisa.identity.models import User


async def get_current_user(request: Request) -> User:
    identity_provider = request.app.state.identity_provider
    return await identity_provider.get_current_user()

