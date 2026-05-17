import os
import sys

# ── Make all files importable from flat structure ──
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, Text, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
import enum

# ── DATABASE ─────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/careerpilot")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── MODELS ───────────────────────────────────────────
class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"

class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
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

class Contact(Base):
    __tablename__ = "contacts"
    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, nullable=True)
    full_name  = Column(String(100), nullable=False)
    email      = Column(String(150), nullable=False)
    phone      = Column(String(20))
    service    = Column(String(100))
    message    = Column(Text)
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Booking(Base):
    __tablename__ = "bookings"
    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, nullable=True)
    full_name     = Column(String(100), nullable=False)
    email         = Column(String(150), nullable=False)
    phone         = Column(String(20))
    service_type  = Column(String(100))
    booking_date  = Column(DateTime(timezone=True), nullable=False)
    duration_mins = Column(Integer, default=30)
    status        = Column(Enum(BookingStatus), default=BookingStatus.pending)
    notes         = Column(Text)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

class Payment(Base):
    __tablename__ = "payments"
    id                  = Column(Integer, primary_key=True, index=True)
    user_id             = Column(Integer, nullable=True)
    plan_name           = Column(String(100), nullable=False)
    amount              = Column(Float, nullable=False)
    currency            = Column(String(10), default="INR")
    razorpay_order_id   = Column(String(255), unique=True, nullable=True)
    razorpay_payment_id = Column(String(255), nullable=True)
    status              = Column(Enum(PaymentStatus), default=PaymentStatus.pending)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

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

Base.metadata.create_all(bind=engine)

# ── AUTH UTILS ───────────────────────────────────────
pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
SECRET_KEY    = os.getenv("SECRET_KEY", "careerpilot-secret-2025")
ALGORITHM     = "HS256"
EXPIRE_MIN    = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

def hash_password(p): return pwd_context.hash(p)
def verify_password(p, h): return pwd_context.verify(p, h)
def create_token(data):
    d = data.copy()
    d["exp"] = datetime.utcnow() + timedelta(minutes=EXPIRE_MIN)
    return jwt.encode(d, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    exc = HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = payload.get("sub")
        if not uid: raise exc
    except JWTError:
        raise exc
    user = db.query(User).filter(User.id == int(uid)).first()
    if not user or not user.is_active: raise exc
    return user

def require_admin(u: User = Depends(get_current_user)):
    if u.role != "admin": raise HTTPException(status_code=403, detail="Admin required")
    return u

# ── SCHEMAS ──────────────────────────────────────────
class UserRegister(BaseModel):
    full_name: str; email: EmailStr; phone: Optional[str] = None; password: str

class UserLogin(BaseModel):
    email: EmailStr; password: str

class UserOut(BaseModel):
    id: int; full_name: str; email: str; phone: Optional[str]
    role: UserRole; is_active: bool; created_at: datetime
    class Config: from_attributes = True

class Token(BaseModel):
    access_token: str; token_type: str; user: UserOut

class ContactCreate(BaseModel):
    full_name: str; email: EmailStr; phone: Optional[str] = None
    service: Optional[str] = None; message: Optional[str] = None

class ContactOut(BaseModel):
    id: int; full_name: str; email: str; service: Optional[str]
    message: Optional[str]; is_read: bool; created_at: datetime
    class Config: from_attributes = True

class BookingCreate(BaseModel):
    full_name: str; email: EmailStr; phone: Optional[str] = None
    service_type: str; booking_date: datetime
    duration_mins: Optional[int] = 30; notes: Optional[str] = None

class BookingOut(BaseModel):
    id: int; full_name: str; email: str; service_type: str
    booking_date: datetime; status: BookingStatus; created_at: datetime
    class Config: from_attributes = True

class PaymentCreate(BaseModel):
    plan_name: str; amount: float; currency: str = "INR"

class PaymentOut(BaseModel):
    id: int; plan_name: str; amount: float; currency: str
    status: PaymentStatus; razorpay_order_id: Optional[str]; created_at: datetime
    class Config: from_attributes = True

class BlogCreate(BaseModel):
    title: str; slug: str; summary: Optional[str] = None; content: str
    tag: Optional[str] = None; author: Optional[str] = "CareerPilot Team"; is_published: bool = False

class BlogOut(BaseModel):
    id: int; title: str; slug: str; summary: Optional[str]; tag: Optional[str]
    author: str; is_published: bool; created_at: datetime
    class Config: from_attributes = True

class BlogDetailOut(BlogOut):
    content: str

# ── EMAIL ────────────────────────────────────────────
SENDGRID_KEY = os.getenv("SENDGRID_API_KEY", "")
FROM_EMAIL   = os.getenv("FROM_EMAIL", "hello@careerpilotai.com")
ADMIN_EMAIL  = os.getenv("ADMIN_EMAIL", "admin@careerpilotai.com")

def send_email(to, subject, html):
    if not SENDGRID_KEY or SENDGRID_KEY in ("skip-for-now", ""):
        print(f"[EMAIL] To:{to} Subject:{subject}"); return
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        SendGridAPIClient(SENDGRID_KEY).send(Mail(FROM_EMAIL, to, subject, html))
    except Exception as e:
        print(f"Email error: {e}")

# ── APP ──────────────────────────────────────────────
app = FastAPI(title="CareerPilot AI API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

from fastapi import APIRouter
auth_router    = APIRouter()
contact_router = APIRouter()
booking_router = APIRouter()
payment_router = APIRouter()
admin_router   = APIRouter()
blog_router    = APIRouter()
resume_router  = APIRouter()

# ── AUTH ROUTES ──────────────────────────────────────
@auth_router.post("/register", response_model=Token, status_code=201)
def register(p: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == p.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(full_name=p.full_name, email=p.email, phone=p.phone,
                hashed_password=hash_password(p.password))
    db.add(user); db.commit(); db.refresh(user)
    return {"access_token": create_token({"sub": str(user.id)}), "token_type": "bearer", "user": user}

@auth_router.post("/login", response_model=Token)
def login(p: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == p.email).first()
    if not user or not verify_password(p.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_token({"sub": str(user.id)}), "token_type": "bearer", "user": user}

@auth_router.get("/me", response_model=UserOut)
def me(u: User = Depends(get_current_user)): return u

@auth_router.put("/me", response_model=UserOut)
def update_me(full_name: str = None, phone: str = None,
              u: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if full_name: u.full_name = full_name
    if phone: u.phone = phone
    db.commit(); db.refresh(u); return u

# ── CONTACT ROUTES ───────────────────────────────────
@contact_router.post("/", response_model=ContactOut, status_code=201)
def submit_contact(p: ContactCreate, bg: BackgroundTasks, db: Session = Depends(get_db)):
    c = Contact(**p.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    bg.add_task(send_email, p.email, "We got your message — CareerPilot AI",
                f"<h2>Hi {p.full_name}!</h2><p>We'll reply within 24 hours.</p>")
    return c

# ── BOOKING ROUTES ───────────────────────────────────
@booking_router.post("/", response_model=BookingOut, status_code=201)
def create_booking(p: BookingCreate, bg: BackgroundTasks,
                   db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    b = Booking(**p.model_dump(), user_id=u.id)
    db.add(b); db.commit(); db.refresh(b)
    bg.add_task(send_email, p.email, "Booking Confirmed — CareerPilot AI",
                f"<h2>Booked!</h2><p>Your {p.service_type} session is confirmed.</p>")
    return b

@booking_router.get("/my", response_model=List[BookingOut])
def my_bookings(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return db.query(Booking).filter(Booking.user_id == u.id).order_by(Booking.booking_date.desc()).all()

@booking_router.get("/slots")
def slots(date: str):
    return {"date": date, "available_slots": ["09:00 AM","10:00 AM","11:00 AM","02:00 PM","03:00 PM","04:00 PM","05:00 PM"]}

@booking_router.put("/{bid}/cancel", response_model=BookingOut)
def cancel(bid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    b = db.query(Booking).filter(Booking.id == bid, Booking.user_id == u.id).first()
    if not b: raise HTTPException(404, "Not found")
    b.status = "cancelled"; db.commit(); db.refresh(b); return b

# ── PAYMENT ROUTES ───────────────────────────────────
@payment_router.post("/create-order", status_code=201)
def create_order(p: PaymentCreate, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    key = os.getenv("RAZORPAY_KEY_ID", "")
    if not key or key in ("skip-for-now", "rzp_test_key", ""):
        raise HTTPException(400, "Razorpay not configured. Add your API keys.")
    try:
        import razorpay
        client = razorpay.Client(auth=(key, os.getenv("RAZORPAY_KEY_SECRET", "")))
        order = client.order.create({"amount": int(p.amount*100), "currency": p.currency, "payment_capture": 1})
        pay = Payment(user_id=u.id, plan_name=p.plan_name, amount=p.amount,
                      currency=p.currency, razorpay_order_id=order["id"])
        db.add(pay); db.commit(); db.refresh(pay)
        return {"order_id": order["id"], "amount": int(p.amount*100), "currency": p.currency, "key_id": key}
    except Exception as e:
        raise HTTPException(500, str(e))

@payment_router.get("/my", response_model=List[PaymentOut])
def my_payments(db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    return db.query(Payment).filter(Payment.user_id == u.id).all()

# ── ADMIN ROUTES ─────────────────────────────────────
@admin_router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _=Depends(require_admin)):
    return {
        "total_users":       db.query(User).count(),
        "total_contacts":    db.query(Contact).count(),
        "total_bookings":    db.query(Booking).count(),
        "total_revenue":     db.query(func.sum(Payment.amount)).filter(Payment.status=="success").scalar() or 0,
        "unread_contacts":   db.query(Contact).filter(Contact.is_read==False).count(),
        "pending_bookings":  db.query(Booking).filter(Booking.status=="pending").count(),
    }

@admin_router.get("/contacts", response_model=List[ContactOut])
def all_contacts(skip:int=0, limit:int=50, db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(Contact).order_by(Contact.created_at.desc()).offset(skip).limit(limit).all()

@admin_router.put("/contacts/{cid}/read")
def mark_read(cid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    c = db.query(Contact).filter(Contact.id==cid).first()
    if c: c.is_read=True; db.commit()
    return {"message": "done"}

@admin_router.get("/bookings", response_model=List[BookingOut])
def all_bookings(skip:int=0, limit:int=50, db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(Booking).order_by(Booking.booking_date.desc()).offset(skip).limit(limit).all()

@admin_router.put("/bookings/{bid}/confirm")
def confirm_booking(bid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    b = db.query(Booking).filter(Booking.id==bid).first()
    if b: b.status="confirmed"; db.commit()
    return {"message": "confirmed"}

@admin_router.get("/users", response_model=List[UserOut])
def all_users(skip:int=0, limit:int=50, db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(User).order_by(User.created_at.desc()).offset(skip).limit(limit).all()

# ── BLOG ROUTES ──────────────────────────────────────
@blog_router.get("/", response_model=List[BlogOut])
def get_blogs(skip:int=0, limit:int=10, db: Session = Depends(get_db)):
    return db.query(Blog).filter(Blog.is_published==True).order_by(Blog.created_at.desc()).offset(skip).limit(limit).all()

@blog_router.get("/{slug}", response_model=BlogDetailOut)
def get_blog(slug: str, db: Session = Depends(get_db)):
    b = db.query(Blog).filter(Blog.slug==slug, Blog.is_published==True).first()
    if not b: raise HTTPException(404, "Not found")
    return b

@blog_router.post("/", response_model=BlogDetailOut, status_code=201)
def create_blog(p: BlogCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    if db.query(Blog).filter(Blog.slug==p.slug).first(): raise HTTPException(400, "Slug exists")
    b = Blog(**p.model_dump()); db.add(b); db.commit(); db.refresh(b); return b

@blog_router.put("/{bid}", response_model=BlogDetailOut)
def update_blog(bid: int, p: BlogCreate, db: Session = Depends(get_db), _=Depends(require_admin)):
    b = db.query(Blog).filter(Blog.id==bid).first()
    if not b: raise HTTPException(404, "Not found")
    for k,v in p.model_dump().items(): setattr(b,k,v)
    db.commit(); db.refresh(b); return b

@blog_router.delete("/{bid}")
def delete_blog(bid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    b = db.query(Blog).filter(Blog.id==bid).first()
    if b: db.delete(b); db.commit()
    return {"message": "deleted"}

# ── RESUME ROUTES ────────────────────────────────────
from fastapi import UploadFile, File
import re, json

ROLE_KEYWORDS = {
    "software_engineer": ["python","java","javascript","react","node","sql","api","git","agile","docker","testing","aws"],
    "data_analyst": ["python","sql","excel","tableau","pandas","machine learning","statistics","analytics"],
    "product_manager": ["roadmap","agile","stakeholder","kpi","metrics","jira","prioritization"],
    "mba_management": ["leadership","strategy","revenue","stakeholder","business development","operations"],
    "general": ["communication","leadership","teamwork","problem solving","project management","excel"],
}

@resume_router.post("/analyze")
async def analyze(file: UploadFile = File(...), role: str = "general"):
    content = await file.read()
    if len(content) > 5*1024*1024: raise HTTPException(400, "Max 5MB")
    try:
        if file.filename.lower().endswith(".pdf"):
            import io, pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        elif file.filename.lower().endswith(".docx"):
            import tempfile, docx2txt
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(content); name = tmp.name
            text = docx2txt.process(name); os.unlink(name)
        else:
            text = content.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(400, f"Could not read file: {e}")

    tl = text.lower()
    kw = ROLE_KEYWORDS.get(role, ROLE_KEYWORDS["general"])
    matched = [k for k in kw if k in tl]
    missing = [k for k in kw if k not in tl]
    kw_score = round(len(matched)/len(kw)*100)
    checks = {
        "Email":          bool(re.search(r'[\w.+-]+@[\w-]+\.\w+', text)),
        "Phone":          bool(re.search(r'[\+\(]?[0-9][0-9\s\-\(\)]{8,}[0-9]', text)),
        "LinkedIn":       "linkedin" in tl,
        "Summary":        any(w in tl for w in ["summary","objective","profile"]),
        "Experience":     any(w in tl for w in ["experience","employment","work"]),
        "Education":      any(w in tl for w in ["education","degree","university","college"]),
        "Skills":         "skills" in tl,
        "Bullets":        text.count("•")+text.count("-") > 5,
        "Good Length":    300 < len(text.split()) < 900,
    }
    st_score = round(sum(checks.values())/len(checks)*100)
    total    = round(kw_score*0.55 + st_score*0.45)
    return {
        "filename": file.filename, "role": role, "status": "success",
        "scores": {"total_score": total, "keyword_score": kw_score, "structure_score": st_score,
                   "word_count": len(text.split()), "matched_keywords": matched,
                   "missing_keywords": missing[:8], "structure_checks": checks},
        "feedback": {
            "overall_verdict": f"Your resume scored {total}/100.",
            "grade": "A" if total>=85 else "B" if total>=70 else "C" if total>=55 else "D",
            "strengths":      [f"Matched {len(matched)} keywords", "Resume processed successfully"],
            "critical_fixes": missing[:3] or ["Add more keywords"],
            "quick_wins":     ["Add LinkedIn URL", "Quantify achievements", "Add professional summary"],
            "tone_feedback":  "Use strong action verbs and quantify your results.",
            "impact_score":   total,
            "recruiter_tip":  "Tailor your resume for each job description."
        }
    }

@resume_router.get("/roles")
def roles():
    return {"roles": [
        {"id":"software_engineer","label":"Software Engineer"},
        {"id":"data_analyst","label":"Data Analyst"},
        {"id":"product_manager","label":"Product Manager"},
        {"id":"mba_management","label":"MBA / Management"},
        {"id":"general","label":"General / Other"},
    ]}

# ── REGISTER ROUTERS ─────────────────────────────────
app.include_router(auth_router,    prefix="/api/auth")
app.include_router(contact_router, prefix="/api/contact")
app.include_router(booking_router, prefix="/api/booking")
app.include_router(payment_router, prefix="/api/payment")
app.include_router(admin_router,   prefix="/api/admin")
app.include_router(blog_router,    prefix="/api/blog")
app.include_router(resume_router,  prefix="/api/resume")

@app.get("/")
def root(): return {"message": "CareerPilot AI API is running!"}

@app.get("/health")
def health(): return {"status": "healthy"}
