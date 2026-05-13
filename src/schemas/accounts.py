import re
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict

from src.database import accounts_validators


class BaseEmailPasswordSchema(BaseModel):
    email: EmailStr
    password: str

    model_config = {"from_attributes": True}

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        return accounts_validators.validate_password_strength(value)


class UserRegistrationRequestSchema(BaseEmailPasswordSchema):
    pass


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must contain at least 8 characters.")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one digit.")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lower letter.")
        if not re.search(r"[@$!%*?#&]", v):
            raise ValueError(
                "Password must contain at least one special character: @, $, !, %, *, ?, #, &."
            )
        return v


class UserResponse(BaseModel):
    id: int
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class PasswordResetCompleteRequestSchema(BaseEmailPasswordSchema):
    token: str


class UserLoginRequestSchema(BaseEmailPasswordSchema):
    pass


class UserLoginResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRegistrationResponseSchema(BaseModel):
    id: int
    email: EmailStr

    model_config = {"from_attributes": True}


class UserActivationRequestSchema(BaseModel):
    email: EmailStr
    token: str


class MessageResponseSchema(BaseModel):
    message: str


class TokenRefreshRequestSchema(BaseModel):
    refresh_token: str


class TokenRefreshResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
