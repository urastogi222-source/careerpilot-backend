import os, hmac, hashlib
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import Payment, User
from schemas.schemas import PaymentCreate, PaymentVerify, PaymentOut
from utils.auth import get_current_user
from utils.email import send_payment_success
import razorpay

router = APIRouter()

RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID", "rzp_test_key")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "secret")

def get_razorpay_client():
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@router.post("/create-order", response_model=dict, status_code=201)
def create_order(payload: PaymentCreate, db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    client = get_razorpay_client()
    amount_paise = int(payload.amount * 100)  # Razorpay uses paise
    order = client.order.create({
        "amount": amount_paise,
        "currency": payload.currency,
        "payment_capture": 1
    })
    payment = Payment(
        user_id=current_user.id,
        plan_name=payload.plan_name,
        amount=payload.amount,
        currency=payload.currency,
        razorpay_order_id=order["id"],
        status="pending"
    )
    db.add(payment); db.commit(); db.refresh(payment)
    return {
        "order_id": order["id"],
        "amount": amount_paise,
        "currency": payload.currency,
        "key_id": RAZORPAY_KEY_ID,
        "payment_db_id": payment.id
    }

@router.post("/verify", response_model=PaymentOut)
def verify_payment(payload: PaymentVerify, background_tasks: BackgroundTasks,
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    payment = db.query(Payment).filter(
        Payment.razorpay_order_id == payload.razorpay_order_id,
        Payment.user_id == current_user.id
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Order not found")

    # Verify Razorpay signature
    body = f"{payload.razorpay_order_id}|{payload.razorpay_payment_id}"
    expected_sig = hmac.new(
        RAZORPAY_KEY_SECRET.encode(), body.encode(), hashlib.sha256
    ).hexdigest()

    if expected_sig != payload.razorpay_signature:
        payment.status = "failed"
        db.commit()
        raise HTTPException(status_code=400, detail="Payment signature mismatch")

    payment.razorpay_payment_id = payload.razorpay_payment_id
    payment.razorpay_signature  = payload.razorpay_signature
    payment.status              = "success"
    db.commit(); db.refresh(payment)

    background_tasks.add_task(
        send_payment_success,
        current_user.full_name, current_user.email,
        payment.plan_name, payment.amount
    )
    return payment

@router.get("/my", response_model=list[PaymentOut])
def my_payments(db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    return db.query(Payment).filter(Payment.user_id == current_user.id)\
             .order_by(Payment.created_at.desc()).all()
