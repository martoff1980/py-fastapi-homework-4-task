from fastapi import Request, HTTPException, status, Depends

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.security.interfaces import JWTAuthManagerInterface
from src.config import get_jwt_auth_manager
from src.database import get_db, UserModel


async def get_current_user_id(
    request: Request,
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> int:
    auth_header = request.headers.get("Authorization")

    # 1. Проверка наличия заголовка
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
        )

    # 2. Проверка формата Bearer <token>
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
        )

    token = parts[1]

    # 3. Валидация токена через менеджер
    payload = jwt_manager.decode_access_token(token)
    if not payload or "user_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    return payload["user_id"]


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    jwt_manager: JWTAuthManagerInterface = Depends(get_jwt_auth_manager),
) -> UserModel:
    auth_header = request.headers.get("Authorization")

    # 1. Проверка наличия заголовка
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
        )

    # 2. Проверка формата Bearer <token>
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
        )

    token = parts[1]

    # 3. Валидация токена через менеджер
    payload = jwt_manager.decode_access_token(token)
    if not payload or "user_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    # 4. Извлекаем пользователя из БД
    result = await db.execute(
        select(UserModel).where(UserModel.id == payload["user_id"])
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 5. ПРОВЕРКА НА АКТИВНОСТЬ (Исправляет тест test_inactive_user_cannot_create_profile)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive"
        )

    return user
