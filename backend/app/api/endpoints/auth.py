import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.auth import (
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    create_access_token,
    get_current_user,
    get_password_hash,
    get_request_token,
    oauth2_scheme,
    revoke_access_token,
    set_session_cookie,
    verify_password,
)
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "recepcionista"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str


import os

from app.core.limiter import limiter
from app.core.security import validate_cookie_origin
from app.core.config import settings


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    req: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Autentica o usuário e cria uma sessão HttpOnly protegida contra força bruta."""
    validate_cookie_origin(request)
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalars().first()

    # Se for o primeiro acesso da clínica e não houver usuários, auto-cria o admin padrão
    initial_admin_pwd = settings.INITIAL_ADMIN_PASSWORD.strip()
    if (
        not user
        and initial_admin_pwd
        and len(initial_admin_pwd) >= 12
        and req.email == "admin@respirar.com"
        and req.password == initial_admin_pwd
    ):
        user = User(
            email="admin@respirar.com",
            name="Dr. Gustavo (Admin)",
            hashed_password=get_password_hash(initial_admin_pwd),
            role="admin",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha incorretos."
        )

    access_token = create_access_token(data={"sub": user.id})
    set_session_cookie(response, access_token)
    return {
        "user": {"id": user.id, "email": user.email, "name": user.name, "role": user.role}
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    bearer_token: str = Depends(oauth2_scheme),
):
    """Revoga a sessão atual no servidor e remove o cookie do navegador."""
    token = get_request_token(request, bearer_token)
    if token:
        if request.cookies.get(SESSION_COOKIE_NAME):
            validate_cookie_origin(request)
        await revoke_access_token(token)
    clear_session_cookie(response)
    return {"status": "ok"}


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado atual."""
    if not user:
        # Modo bypass de desenvolvimento
        return {"email": "admin@respirar.com", "name": "Dr. Gustavo", "role": "admin"}
    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Lista todos os usuários cadastrados na clínica (Acesso Restrito)."""
    if current_user and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem listar colaboradores.",
        )

    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.strftime("%d/%m/%Y %H:%M")
            if u.created_at
            else None,
        }
        for u in users
    ]


@router.post("/users")
async def create_user(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria um novo login de acesso para a equipe da clínica (Acesso Restrito ao Admin)."""
    if current_user and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem criar novos colaboradores.",
        )

    if len(req.password) < 12:
        raise HTTPException(
            status_code=400, detail="A senha deve ter no mínimo 12 caracteres."
        )

    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")

    new_user = User(
        email=req.email,
        name=req.name,
        hashed_password=get_password_hash(req.password),
        role=req.role,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {
        "status": "ok",
        "message": f"Usuário {new_user.name} criado com sucesso!",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "role": new_user.role,
        },
    }


class ChangePasswordRequest(BaseModel):
    email: str
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Altera a senha de um usuário autenticado."""
    if current_user and current_user.email != req.email and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não é permitido alterar a senha de outro usuário.",
        )

    if len(req.new_password) < 12:
        raise HTTPException(
            status_code=400, detail="A nova senha deve ter no mínimo 12 caracteres."
        )

    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalars().first()

    if not user or not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")

    user.hashed_password = get_password_hash(req.new_password)
    await db.commit()
    return {"status": "ok", "message": "Senha alterada com sucesso!"}
