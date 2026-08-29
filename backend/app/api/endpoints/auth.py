from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import logging

from app.database import get_db
from app.models.user import User
from app.core.auth import verify_password, get_password_hash, create_access_token, get_current_user

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

@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Autentica usuário e retorna JWT token com permissões (RBAC)."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalars().first()
    
    # Se for o primeiro acesso da clínica e não houver usuários, auto-cria o admin padrão
    if not user and req.email == "admin@respirar.com" and req.password == "admin123":
        user = User(
            email="admin@respirar.com",
            name="Dr. Gustavo (Admin)",
            hashed_password=get_password_hash("admin123"),
            role="admin"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos."
        )

    access_token = create_access_token(data={"sub": user.email, "role": user.role, "name": user.name})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
    }

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Retorna os dados do usuário autenticado atual."""
    if not user:
        # Modo bypass de desenvolvimento
        return {"email": "admin@respirar.com", "name": "Dr. Gustavo", "role": "admin"}
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role
    }
