from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import Contact
from schemas.schemas import ContactCreate, ContactOut
from utils.email import send_contact_confirmation

router = APIRouter()

@router.post("/", response_model=ContactOut, status_code=201)
def submit_contact(payload: ContactCreate, background_tasks: BackgroundTasks,
                   db: Session = Depends(get_db)):
    contact = Contact(**payload.model_dump())
    db.add(contact); db.commit(); db.refresh(contact)
    background_tasks.add_task(
        send_contact_confirmation,
        payload.full_name, payload.email, payload.service or "General Enquiry"
    )
    return contact
