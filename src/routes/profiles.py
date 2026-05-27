from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    status
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import select

from src.schemas.profiles import ProfileCreateForm
from src.database import get_db, UserModel, UserProfileModel, UserGroupEnum
from src.storages import S3StorageInterface
from src.storages.s3 import AvatarService
from src.config import get_s3_storage_client
from src.config.dependencies import get_current_user_id, get_current_active_user, check_profile_edit_permission
from src.exceptions.storage import S3FileUploadError
from src.validation.profile import (
    GenderEnum,
    validate_name,
    validate_image,
    validate_gender,
    validate_birth_date,
    validate_user,
    validate_full_name_user,
)


router = APIRouter()


@router.post("/users/{user_id}/profile/", status_code=status.HTTP_201_CREATED)
async def create_profile(
    user_id: int,
    current_user_id: int = Depends(get_current_user_id),
    first_name: str = Form(...),
    last_name: str = Form(...),
    gender: str = Form(...),
    date_of_birth: str = Form(...),
    info: str = Form(...),
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    s3_client: S3StorageInterface = Depends(get_s3_storage_client),
):
    # функция по пользователю
    # 1. Валидация существования пользователя
    # Обычно это проверяется в зависимости get_current_user_id,
    # но если ваш менеджер токенов этого не делает, добавим проверку здесь:
    stmt = (
        select(UserModel)
        .options(joinedload(UserModel.group))
        .where(UserModel.id == current_user_id)
    )
    result = await db.execute(stmt)
    user = result.scalars().first()

    # --------------------------- #
    # if not user:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Token has expired.",
    #     )

    # if not user.is_active:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="User not found or not active.",
    #     )

    # Проверка прав (Admin или владелец)
    # Используем безопасную проверку группы
    # user_group_name = user.group.name if user.group else ""
    # if user_id != current_user_id and user_group_name != UserGroupEnum.ADMIN.value:
    #     raise HTTPException(
    #         status_code=403, detail="You don't have permission to edit this profile."
    #     )
    # --------------------------- #
    validate_user(user, user_id, current_user_id)

    # функция по валидации формы
    # --------------------------- #
    # Проверка на существующий профиль
    # Предотвращает IntegrityError UNIQUE constraint failed
    existing_profile = await db.execute(
        select(UserProfileModel).where(UserProfileModel.user_id == user_id)
    )
    if existing_profile.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has a profile.",
        )

    # 1.1 Валидация имени и фамилии
    # try:
    #     validate_name(first_name)
    # except ValueError:
    #     raise HTTPException(
    #         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    #         detail=f"{first_name} contains non-english letters"
    #     )

    # try:
    #     validate_name(last_name)
    # except ValueError:
    #     raise HTTPException(
    #         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    #         detail=f"{last_name} contains non-english letters"
    #     )
    validate_full_name_user(first_name, last_name)

    # 2. Валидация поля info
    if not info or info.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Info field cannot be empty or contain only spaces.",
        )

    # 3. Валидация gender (исправленная и усиленная)
    valid_genders = [item.value for item in GenderEnum]

    if not gender or gender.strip() == "":
        raise HTTPException(
            status_code=422, detail=f"Gender must be one of {valid_genders}."
        )

    if gender not in valid_genders:
        raise HTTPException(
            status_code=422, detail=f"Gender must be one of {valid_genders}."
        )

    gender_enum = GenderEnum(gender)

    # 4. Валидация даты рождения
    try:
        birth_date_obj = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Use YYYY-MM-DD.",
        )

    # Вызов функций валидации (убедитесь, что они выбрасывают 422)
    try:
        validate_birth_date(birth_date_obj)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    # --------------------------- #

    # функция по загрузки аватара
    # --------------------------- #
    # 5. Обработка аватара
    try:
        validate_image(avatar)

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        )

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
    # --------------------------- #

    # 6. Создание профиля
    new_profile = UserProfileModel(
        user_id=user_id,
        first_name=first_name.lower(),
        last_name=last_name.lower(),
        gender=gender_enum.value,
        date_of_birth=birth_date_obj,
        info=info,
        avatar=file_path,
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
        "avatar": avatar_url,
    }
