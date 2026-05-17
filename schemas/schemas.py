from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from models.models import UserRole, BookingStatus, PaymentStatus

# ── AUTH ──────────────────────────────────────────────
class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    class Config: from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

# ── CONTACT ───────────────────────────────────────────
class ContactCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    service: Optional[str] = None
    message: Optional[str] = None

class ContactOut(BaseModel):
    id: int
    full_name: str
    email: str
    service: Optional[str]
    message: Optional[str]
    is_read: bool
    created_at: datetime
    class Config: from_attributes = True

# ── BOOKING ───────────────────────────────────────────
class BookingCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    service_type: str
    booking_date: datetime
    duration_mins: Optional[int] = 30
    notes: Optional[str] = None

class BookingOut(BaseModel):
    id: int
    full_name: str
    email: str
    service_type: str
    booking_date: datetime
    status: BookingStatus
    created_at: datetime
    class Config: from_attributes = True

# ── PAYMENT ───────────────────────────────────────────
class PaymentCreate(BaseModel):
    plan_name: str
    amount: float
    currency: str = "INR"

class PaymentVerify(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class PaymentOut(BaseModel):
    id: int
    plan_name: str
    amount: float
    currency: str
    status: PaymentStatus
    razorpay_order_id: Optional[str]
    created_at: datetime
    class Config: from_attributes = True

# ── BLOG ──────────────────────────────────────────────
class BlogCreate(BaseModel):
    title: str
    slug: str
    summary: Optional[str] = None
    content: str
    tag: Optional[str] = None
    author: Optional[str] = "CareerPilot Team"
    is_published: bool = False

class BlogOut(BaseModel):
    id: int
    title: str
    slug: str
    summary: Optional[str]
    tag: Optional[str]
    author: str
    is_published: bool
    created_at: datetime
    class Config: from_attributes = True

class BlogDetailOut(BlogOut):
    content: str
