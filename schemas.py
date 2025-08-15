from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


# Base schemas
class UserBase(BaseModel):
    tg_id: int = Field(..., description="Telegram ID пользователя")
    username: Optional[str] = Field(None, max_length=64, description="Username в Telegram")
    first_name: Optional[str] = Field(None, max_length=128, description="Имя пользователя")
    last_name: Optional[str] = Field(None, max_length=128, description="Фамилия пользователя")
    phone: Optional[str] = Field(None, max_length=20, description="Номер телефона")


class StockBase(BaseModel):
    title: str = Field(..., max_length=128, description="Название слота")
    completed: bool = Field(default=False, description="Завершен ли слот")


# Request schemas
class RegisterPayload(UserBase):
    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('Некорректный номер телефона')
        return v


class StockUpdatePayload(BaseModel):
    incrementSlot: Optional[bool] = Field(None, description="Увеличить количество слотов")
    filledSlots: Optional[int] = Field(None, ge=0, le=100, description="Количество заполненных слотов")


# Response schemas
class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StockResponse(StockBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileResponse(BaseModel):
    registered: bool
    completedStocks: int
    user: Optional[UserResponse] = None


class RegisterResponse(BaseModel):
    success: bool
    user: UserResponse


class StockListResponse(BaseModel):
    stocks: List[StockResponse]
    total: int
    completed: int
    available: int


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SuccessResponse(BaseModel):
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
