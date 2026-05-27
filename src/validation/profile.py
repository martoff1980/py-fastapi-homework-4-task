import re
from datetime import date
from io import BytesIO

from PIL import Image
from fastapi import UploadFile, HTTPException, status

from src.database.models.accounts import GenderEnum, UserModel, UserGroupEnum


def validate_name(name: str):
    if re.fullmatch(r'^[A-Za-z]+$', name) is None:
        raise ValueError(f'{name} contains non-english letters')


def validate_image(avatar: UploadFile) -> None:
    supported_image_formats = ["JPG", "JPEG", "PNG"]
    max_file_size = 1 * 1024 * 1024

    contents = avatar.file.read()
    if len(contents) > max_file_size:
        raise ValueError("Image size exceeds 1 MB")

    try:
        image = Image.open(BytesIO(contents))
        avatar.file.seek(0)
        image_format = image.format
        if image_format not in supported_image_formats:
            raise ValueError(f"Unsupported image format: {image_format}. Use one of next: {supported_image_formats}")
    except IOError:
        raise ValueError("Invalid image format")


def validate_gender(gender: str) -> None:
    if gender not in GenderEnum.__members__.values():
        raise ValueError(f"Gender must be one of: {', '.join(g.value for g in GenderEnum)}")


def validate_birth_date(birth_date: date) -> None:
    if birth_date.year < 1900:
        raise ValueError('Invalid birth date - year must be greater than 1900.')

    age = (date.today() - birth_date).days // 365
    if age < 18:
        raise ValueError('You must be at least 18 years old to register.')


def validate_user(user: UserModel, user_id: int, current_user_id: int) -> None:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or not active.",
        )

    # Проверка прав (Admin или владелец)
    # Используем безопасную проверку группы
    user_group_name = user.group.name if user.group else ""
    if user_id != current_user_id and user_group_name != UserGroupEnum.ADMIN.value:
        raise HTTPException(
            status_code=403, detail="You don't have permission to edit this profile."
        )


def validate_full_name_user(first_name, last_name):
    try:
        validate_name(first_name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{first_name} contains non-english letters"
        )

    try:
        validate_name(last_name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{last_name} contains non-english letters"
        )


def validate_profile_data():
    ...
