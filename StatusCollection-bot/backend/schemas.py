from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class Category(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class Product(BaseModel):
    id: int
    category_id: Optional[int] = None
    name: str
    price: int
    color: Optional[str] = None
    image_url: Optional[str] = None
    material: Optional[str] = None
    description: Optional[str] = None
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    image_url: Optional[str] = None
    last_name: Optional[str] = None


class User(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    telegram_id: int
    customer_name: str
    phone: str
    address: str
    comment: Optional[str] = None
    items: List[OrderItemCreate]


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    price: int

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: int
    status: str
    total_price: int
    customer_name: str
    phone: str
    address: str
    created_at: datetime
    items: List[OrderItemOut]

    model_config = ConfigDict(from_attributes=True)

class ProductCreate(BaseModel):
    category_id: int
    name: str
    price: int
    color: Optional[str] = None
    material: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_available: bool = True

class OrderStatusUpdate(BaseModel):
        status: str