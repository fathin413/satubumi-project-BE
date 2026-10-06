from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    phone_number: str | None = None
    role: str | None = "client"
    profile_image: str | None = None
    has_rapidfs_access: bool = False


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    phone_number: str | None = None
    role: str | None = None
    is_active: bool | None = None
    has_rapidfs_access: bool | None = None
    password: str | None = None
    profile_image: str | None = None


class ProfileUpdate(BaseModel):
    """Schema untuk user mengedit profil miliknya sendiri (tanpa izin ubah role/status)."""
    full_name: str | None = None
    phone_number: str | None = None
    email: EmailStr | None = None
    password: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: str | None = None
