from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from models.database import get_db
from models.models import User, Contact, Booking, Payment
from schemas.schemas import ContactOut, BookingOut, UserOut
from utils.auth import require_admin

router = APIRouter()

@router.get("/dashboard")
def dashboard_stats(db: Session = Depends(get_db), _=Depends(require_admin)):
    total_users    = db.query(func.count(User.id)).scalar()
    total_contacts = db.query(func.count(Contact.id)).scalar()
    total_bookings = db.query(func.count(Booking.id)).scalar()
    total_revenue  = db.query(func.sum(Payment.amount)).filter(
                        Payment.status == "success").scalar() or 0
    unread_contacts = db.query(func.count(Contact.id))\
                        .filter(Contact.is_read == False).scalar()
    pending_bookings = db.query(func.count(Booking.id))\
                         .filter(Booking.status == "pending").scalar()
    return {
        "total_users":       total_users,
        "total_contacts":    total_contacts,
        "total_bookings":    total_bookings,
        "total_revenue":     total_revenue,
        "unread_contacts":   unread_contacts,
        "pending_bookings":  pending_bookings,
    }

@router.get("/contacts", response_model=List[ContactOut])
def get_all_contacts(skip: int = 0, limit: int = 50,
                     db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(Contact).order_by(Contact.created_at.desc())\
             .offset(skip).limit(limit).all()

@router.put("/contacts/{contact_id}/read")
def mark_contact_read(contact_id: int, db: Session = Depends(get_db),
                      _=Depends(require_admin)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if contact:
        contact.is_read = True
        db.commit()
    return {"message": "Marked as read"}

@router.get("/bookings", response_model=List[BookingOut])
def get_all_bookings(skip: int = 0, limit: int = 50,
                     db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(Booking).order_by(Booking.booking_date.desc())\
             .offset(skip).limit(limit).all()

@router.put("/bookings/{booking_id}/confirm")
def confirm_booking(booking_id: int, db: Session = Depends(get_db),
                    _=Depends(require_admin)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking:
        booking.status = "confirmed"
        db.commit()
    return {"message": "Booking confirmed"}

@router.get("/users", response_model=List[UserOut])
def get_all_users(skip: int = 0, limit: int = 50,
                  db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(User).order_by(User.created_at.desc())\
             .offset(skip).limit(limit).all()
