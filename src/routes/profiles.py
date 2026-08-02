import re
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from database.factory import get_db
from database.models.accounts import (
    UserModel,
    UserProfileModel,
    GenderEnum,
    UserGroupEnum,
)
from config.dependencies import get_current_user_id, get_current_active_user

from storages import S3StorageInterface
from exceptions import S3FileUploadError
from config.dependencies import get_s3_storage_client
from validation import (
    validate_name,
    validate_image,
    validate_gender,
    validate_birth_date,
)

router = APIRouter()


@router.post("/users/{user_id}/profile/", status_code=status.HTTP_201_CREATED)
async def create_profile(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    current_user: UserModel = Depends(get_current_active_user),
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: GenderEnum = Form(...),
    date_of_birth: str = Form(...),
    info: str = Form(...),
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    s3_client: S3StorageInterface = Depends(get_s3_storage_client),
):
    # Получаем роль/группу текущего пользователя
    stmt = (
        select(UserModel)
        .options(selectinload(UserModel.group))
        .where(UserModel.id == current_user_id)
    )
    result = await db.execute(stmt)
    current_user_admin = result.scalar_one_or_none()

    is_admin = (
        current_user_admin.group.name == UserGroupEnum.ADMIN.value
        if hasattr(current_user_admin, "group") and current_user_admin.group
        else False
    )

    # Дополнительная проверка безопасности:
    # может ли текущий пользователь редактировать профиль именно этого user_id
    if user_id != current_user_id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this profile.",
        )

    # 1. Валидация существования пользователя
    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Валидация поля info (тесты ожидают 422 для пустых строк или пробелов)
    if not info or info.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Info field cannot be empty or contain only spaces.",
        )
    # 3. Валидация имени и фамилии
    validate_name(first_name)
    validate_name(last_name)

    # 4. Валидация даты
    try:
        birth_date_obj = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Use YYYY-MM-DD.",
        )

    # Вызов обновленной функции валидации
    validate_birth_date(birth_date_obj)

    # 5. Валидация пола
    validate_gender(gender)

    # 6. Обработка аватара и загрузка в S3
    validate_image(avatar)

    file_content = await avatar.read()
    file_path = f"avatars/{user_id}_{avatar.filename}"

    try:
        await s3_client.upload_file(file_path, file_content)
    except S3FileUploadError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar. Please try again later.",
        )
    avatar_url = await s3_client.get_file_url(file_path)

    # 7. Проверяем, есть ли уже профиль у пользователя
    stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
    result = await db.execute(stmt)
    profile = result.scalars().first()

    if profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a profile.",
        )

    # 8. Создание профиля в БД (имена в нижнем регистре согласно тестам)
    new_profile = UserProfileModel(
        user_id=user_id,
        first_name=first_name.lower(),
        last_name=last_name.lower(),
        gender=gender.value,
        date_of_birth=birth_date_obj,
        info=info,
        avatar=file_path,  # В БД храним путь/ключ
    )

    db.add(new_profile)
    await db.commit()
    await db.refresh(new_profile)

    return {
        "first_name": new_profile.first_name,
        "last_name": new_profile.last_name,
        "gender": new_profile.gender,
        "date_of_birth": new_profile.date_of_birth.isoformat(),
        "info": new_profile.info,
        "avatar": avatar_url,  # В ответе возвращаем полный URL
    }
