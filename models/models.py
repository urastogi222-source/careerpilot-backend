from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.database import Base
import enum

class UserRole(str, enum.Enum):
    user  = "user"
    admin = "admin"

class BookingStatus(str, enum.Enum):
    pending   = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"

class PaymentStatus(str, enum.Enum):
    pending  = "pending"
    success  = "success"
    failed   = "failed"
    refunded = "refunded"

class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True, index=True)
    full_name       = Column(String(100), nullable=False)
    email           = Column(String(150), unique=True, index=True, nullable=False)
    phone           = Column(String(20))
    hashed_password = Column(String(255), nullable=False)
    role            = Column(Enum(UserRole), default=UserRole.user)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())
    bookings        = relationship("Booking", back_populates="user")
    payments        = relationship("Payment", back_populates="user")
    contacts        = relationship("Contact", back_populates="user")
    analyses        = relationship("ResumeAnalysis", back_populates="user")

class Contact(Base):
    __tablename__ = "contacts"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    full_name  = Column(String(100), nullable=False)
    email      = Column(String(150), nullable=False)
    phone      = Column(String(20))
    service    = Column(String(100))
    message    = Column(Text)
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user       = relationship("User", back_populates="contacts")

class Booking(Base):
    __tablename__ = "bookings"
    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=True)
    full_name       = Column(String(100), nullable=False)
    email           = Column(String(150), nullable=False)
    phone           = Column(String(20))
    service_type    = Column(String(100))
    booking_date    = Column(DateTime(timezone=True), nullable=False)
    duration_mins   = Column(Integer, default=30)
    status          = Column(Enum(BookingStatus), default=BookingStatus.pending)
    notes           = Column(Text)
    google_event_id = Column(String(255))
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    user            = relationship("User", back_populates="bookings")
    payment         = relationship("Payment", back_populates="booking", uselist=False)

class Payment(Base):
    __tablename__ = "payments"
    id                  = Column(Integer, primary_key=True, index=True)
    user_id             = Column(Integer, ForeignKey("users.id"), nullable=True)
    booking_id          = Column(Integer, ForeignKey("bookings.id"), nullable=True)
    plan_name           = Column(String(100), nullable=False)
    amount              = Column(Float, nullable=False)
    currency            = Column(String(10), default="INR")
    razorpay_order_id   = Column(String(255), unique=True)
    razorpay_payment_id = Column(String(255))
    razorpay_signature  = Column(String(500))
    status              = Column(Enum(PaymentStatus), default=PaymentStatus.pending)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    user                = relationship("User", back_populates="payments")
    booking             = relationship("Booking", back_populates="payment")

class Blog(Base):
    __tablename__ = "blogs"
    id           = Column(Integer, primary_key=True, index=True)
    title        = Column(String(255), nullable=False)
    slug         = Column(String(255), unique=True, nullable=False)
    summary      = Column(Text)
    content      = Column(Text, nullable=False)
    tag          = Column(String(50))
    author       = Column(String(100), default="CareerPilot Team")
    is_published = Column(Boolean, default=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

class ResumeAnalysis(Base):
    __tablename__ = "resume_analyses"
    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename        = Column(String(255))
    role            = Column(String(100))
    total_score     = Column(Integer)
    keyword_score   = Column(Integer)
    structure_score = Column(Integer)
    grade           = Column(String(5))
    feedback_json   = Column(Text)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    user            = relationship("User", back_populates="analyses")
