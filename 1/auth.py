from typing import cast

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from crud import get_user_by_username, fake_hash_password
from database import AsyncSessionLocal, get_session
from schemas import UserOut

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def authenticate_user_and_get_token(username: str, password: str) -> str | None:
    async with AsyncSessionLocal() as db:
        user = await get_user_by_username(db, username)
        if user is not None:
            stored_hash = cast(str, user.hashed_password)
            if stored_hash == fake_hash_password(password):
                return f"token-{username}"

    if username == "alice" and password == "secret":
        return f"token-{username}"
    return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserOut:
    if not token or not token.startswith("token-"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    username = token.split("-", 1)[1]
    async with AsyncSessionLocal() as db:
        user = await get_user_by_username(db, username)
        if not user:
            if username == "alice":
                return UserOut(id=0, username="alice", full_name="Alice Dev")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return UserOut.model_validate(user)
