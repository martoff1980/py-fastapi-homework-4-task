from datetime import date

from fastapi import UploadFile, Form, File, HTTPException
from pydantic import BaseModel, field_validator, HttpUrl

from validation import (
    validate_name,
    validate_image,
    validate_gender,
    validate_birth_date
)

class UserProfileResponse(BaseModel):
    model_config = {
        "from_attributes": True
    }

    first_name: str
    last_name: str
    gender: str
    date_of_birth: date
    avatar: str # URL из S3

    @field_validator("first_name", "last_name")
    @classmethod
    def to_lowercase(cls, v):
        return v.lower() # Тесты ожидают "john" вместо "John"