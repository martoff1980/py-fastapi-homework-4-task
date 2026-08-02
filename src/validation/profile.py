import re
from datetime import date
from io import BytesIO

from PIL import Image
from fastapi import UploadFile, status, HTTPException

from database.models.accounts import GenderEnum


def validate_name(name: str):
    if re.search(r"^[A-Za-z]*$", name) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{name} contains non-english letters",
        )


def validate_image(avatar: UploadFile) -> None:
    supported_image_formats = ["JPG", "JPEG", "PNG"]
    max_file_size = 1 * 1024 * 1024

    contents = avatar.file.read()
    if len(contents) > max_file_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image size exceeds 1 MB",
        )

    try:
        image = Image.open(BytesIO(contents))
        avatar.file.seek(0)
        image_format = image.format
        if image_format not in supported_image_formats:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported image format: {image_format}. Use one of next: {supported_image_formats}",
            )

    except IOError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid image format",
        )


def validate_gender(gender: str) -> None:
    if gender.lower() not in [g.value for g in GenderEnum]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Gender must be one of: {', '.join(g.value for g in GenderEnum)}",
        )


def validate_birth_date(birth_date: date) -> None:
    if birth_date.year < 1900:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid birth date - year must be greater than 1900.",
        )

    age = (date.today() - birth_date).days // 365
    if age < 18:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must be at least 18 years old to register.",
        )
