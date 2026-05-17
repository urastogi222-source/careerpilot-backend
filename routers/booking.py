from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models.database import get_db
from models.models import Booking, User
from schemas.schemas import BookingCreate, BookingOut
from utils.auth import get_current_user
from utils.email import send_booking_confirmation

router = APIRouter()

@router.post("/", response_model=BookingOut, status_code=201)
def create_booking(payload: BookingCreate, background_tasks: BackgroundTasks,
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    booking = Booking(**payload.model_dump(), user_id=current_user.id)
    db.add(booking); db.commit(); db.refresh(booking)
    background_tasks.add_task(
        send_booking_confirmation,
        payload.full_name, payload.email,
        payload.service_type,
        payload.booking_date.strftime("%d %b %Y, %I:%M %p IST")
    )
    return booking

@router.get("/my", response_model=List[BookingOut])
def my_bookings(db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    return db.query(Booking).filter(Booking.user_id == current_user.id)\
             .order_by(Booking.booking_date.desc()).all()

@router.get("/slots")
def available_slots(date: str):
    """
    Returns available time slots for a given date (YYYY-MM-DD).
    Integrate with Google Calendar API for real availability.
    """
    slots = [
        "09:00 AM", "10:00 AM", "11:00 AM",
        "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM"
    ]
    return {"date": date, "available_slots": slots}

@router.put("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(booking_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    booking = db.query(Booking).filter(
        Booking.id == booking_id, Booking.user_id == current_user.id
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = "cancelled"
    db.commit(); db.refresh(booking)
    return booking
