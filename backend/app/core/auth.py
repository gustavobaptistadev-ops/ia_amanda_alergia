"""Authentication, secure session cookies, and server-side revocation."""

import hashlib
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import require_secret
from app.database import get_db
from app.models.user import User
from app.core.config import settings

SECRET_KEY = require_secret("JWT_SECRET_KEY")
ALGORITHM = "HS256"
SESSION_TOKEN_VERSION = 2
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
SESSION_COOKIE_NAME = "lifeline_session"
SESSION_COOKIE_SECURE = settings.SESSION_COOKIE_SECURE
SESSION_COOKIE_SAMESITE = settings.SESSION_COOKIE_SAMESITE
if SESSION_COOKIE_SAMESITE not in {"lax", "strict", "none"}:
    raise RuntimeError("SESSION_COOKIE_SAMESITE must be lax, strict, or none")
REVOCATION_KEY_PREFIX = "revoked-session:"

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    issued_at = datetime.now(UTC)
    expire = issued_at + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        **data,
        "exp": expire,
        "iat": issued_at,
        "jti": str(uuid.uuid4()),
        "ver": SESSION_TOKEN_VERSION,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_request_token(request: Request, bearer_token: str | None = None) -> str | None:
    """Prefer explicit Bearer credentials, then the protected session cookie."""
    return bearer_token or request.cookies.get(SESSION_COOKIE_NAME)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=SESSION_COOKIE_SECURE,
        httponly=True,
        samesite=SESSION_COOKIE_SAMESITE,
    )


def _revocation_key(token: str) -> str:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"{REVOCATION_KEY_PREFIX}{digest}"


async def is_access_token_revoked(token: str) -> bool:
    import redis.asyncio as redis

    redis_url = settings.REDIS_URL
    try:
        async with redis.Redis.from_url(redis_url) as client:
            return bool(await client.exists(_revocation_key(token)))
    except Exception as exc:
        logger.error("Falha ao validar revogacao de sessao: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servico de autenticacao temporariamente indisponivel.",
        ) from exc


async def revoke_access_token(token: str) -> None:
    import redis.asyncio as redis

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        expires_at = int(payload.get("exp", 0))
    except JWTError:
        return

    ttl = max(1, expires_at - int(datetime.now(UTC).timestamp()))
    redis_url = settings.REDIS_URL
    try:
        async with redis.Redis.from_url(redis_url) as client:
            await client.setex(_revocation_key(token), ttl, "1")
    except Exception as exc:
        logger.error("Falha ao revogar sessao: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nao foi possivel encerrar a sessao com seguranca.",
        ) from exc


async def get_current_user(
    request: Request,
    bearer_token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    token = get_request_token(request, bearer_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticacao obrigatoria",
        )
    if await is_access_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao encerrada"
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None or payload.get("ver") != SESSION_TOKEN_VERSION:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido"
            )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado ou invalido",
        ) from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inativo ou nao encontrado",
        )
    return user
