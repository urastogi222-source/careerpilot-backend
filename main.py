# main.py - CareerPilot AI Complete Backend
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, JSON, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr
import bcrypt
import jwt
import os
import re
from dotenv import load_dotenv

load_dotenv()

# ========== Database Setup ==========
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./careerpilot.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ========== Models ==========
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, index=True, nullable=False)
    phone = Column(String(20))
    hashed_password = Column(String(200), nullable=False)
    role = Column(String(50), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    bookings = relationship("Booking", back_populates="user")
    resumes = relationship("Resume", back_populates="user")
    ats_analyses = relationship("ATSAnalysis", back_populates="user")

class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    full_name = Column(String(200))
    email = Column(String(200))
    phone = Column(String(20))
    service_type = Column(String(200))
    booking_date = Column(DateTime)
    notes = Column(Text)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="bookings")

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(200))
    email = Column(String(200))
    phone = Column(String(20))
    service = Column(String(200))
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Blog(Base):
    __tablename__ = "blogs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300))
    slug = Column(String(300), unique=True, index=True)
    summary = Column(Text)
    content = Column(Text)
    tag = Column(String(100))
    author = Column(String(200), default="CareerPilot Team")
    read_time = Column(String(50), default="5 min read")
    is_published = Column(Boolean, default=False)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(200))
    title = Column(String(200))
    email = Column(String(200))
    phone = Column(String(20))
    linkedin = Column(String(300))
    location = Column(String(200))
    github = Column(String(300))
    summary = Column(Text)
    skills = Column(Text)
    tools = Column(Text)
    soft_skills = Column(Text)
    experience = Column(JSON, default=list)
    education = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="resumes")

class ATSAnalysis(Base):
    __tablename__ = "ats_analyses"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String(300))
    role = Column(String(100))
    total_score = Column(Integer)
    keyword_score = Column(Integer)
    structure_score = Column(Integer)
    word_count = Column(Integer)
    matched_keywords = Column(JSON, default=list)
    missing_keywords = Column(JSON, default=list)
    structure_checks = Column(JSON, default=dict)
    strengths = Column(JSON, default=list)
    critical_fixes = Column(JSON, default=list)
    quick_wins = Column(JSON, default=list)
    feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="ats_analyses")

Base.metadata.create_all(bind=engine)

# ========== Schemas ==========
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    class Config: from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class BookingCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    service_type: str
    booking_date: datetime
    notes: Optional[str] = None

class BookingResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    service_type: str
    booking_date: datetime
    notes: Optional[str] = None
    status: str
    created_at: datetime
    class Config: from_attributes = True

class ContactCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    service: str
    message: str

class BlogCreate(BaseModel):
    title: str
    slug: str
    summary: Optional[str] = None
    content: str
    tag: Optional[str] = "Career"
    author: Optional[str] = "CareerPilot Team"
    is_published: bool = False

class BlogResponse(BaseModel):
    id: int
    title: str
    slug: str
    summary: Optional[str] = None
    content: str
    tag: str
    author: str
    read_time: str
    is_published: bool
    views: int
    created_at: datetime
    class Config: from_attributes = True

# ========== Auth ==========
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
ALGORITHM = "HS256"
security = HTTPBearer()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: int, email: str, role: str) -> str:
    payload = {"user_id": user_id, "email": email, "role": role, "exp": datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(SessionLocal)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.query(User).filter(User.id == payload.get("user_id")).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# ========== Resume Analysis ==========
def analyze_resume_text(text: str, role: str) -> Dict[str, Any]:
    text_lower = text.lower()
    
    keywords = {
        "software_engineer": ["python", "java", "javascript", "react", "sql", "git", "api", "docker", "testing", "aws"],
        "data_analyst": ["python", "sql", "excel", "tableau", "pandas", "statistics", "visualization", "analytics"],
        "product_manager": ["roadmap", "agile", "scrum", "jira", "strategy", "stakeholder", "analytics", "kpis"],
        "general": ["communication", "teamwork", "leadership", "problem solving", "project management"]
    }.get(role, keywords["general"])
    
    matched = [kw for kw in keywords if kw in text_lower]
    missing = [kw for kw in keywords if kw not in text_lower]
    keyword_score = int((len(matched) / len(keywords)) * 100) if keywords else 70
    
    structure_checks = {
        "Email": bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)),
        "Phone": bool(re.search(r'\+?\d[\d\s\-\(\)]{8,}\d', text)),
        "LinkedIn": bool(re.search(r'linkedin\.com/in/', text_lower)),
        "Summary": any(w in text_lower for w in ["summary", "profile", "about"]),
        "Experience": any(w in text_lower for w in ["experience", "work", "employment"]),
        "Education": any(w in text_lower for w in ["education", "degree", "university"]),
        "Skills": any(w in text_lower for w in ["skills", "technical"]),
        "Bullet Points": text.count('\n•') + text.count('\n-') > 3,
    }
    
    structure_score = int((sum(structure_checks.values()) / len(structure_checks)) * 100)
    word_count = len(text.split())
    word_score = 100 if 300 <= word_count <= 900 else 50
    total_score = int((keyword_score + structure_score + word_score) / 3)
    
    strengths = []
    critical_fixes = []
    quick_wins = []
    
    if structure_checks["Email"]: strengths.append("Email address present")
    else: critical_fixes.append("Add your email address")
    
    if structure_checks["LinkedIn"]: strengths.append("LinkedIn URL included")
    else: quick_wins.append("Add your LinkedIn URL")
    
    if structure_checks["Summary"]: strengths.append("Professional summary present")
    else: quick_wins.append("Write a professional summary")
    
    if len(matched) > 3: strengths.append(f"{len(matched)} keywords matched")
    else: critical_fixes.append(f"Add keywords: {', '.join(missing[:3])}")
    
    if word_count < 300: quick_wins.append(f"Add more content ({word_count} words)")
    elif word_count > 900: quick_wins.append(f"Shorten your resume ({word_count} words)")
    
    grade = "A" if total_score >= 80 else "B" if total_score >= 60 else "C" if total_score >= 40 else "D"
    
    return {
        "total_score": total_score, "keyword_score": keyword_score, "structure_score": structure_score,
        "word_count": word_count, "matched_keywords": matched[:10], "missing_keywords": missing[:10],
        "structure_checks": structure_checks, "strengths": strengths[:5], "critical_fixes": critical_fixes[:5],
        "quick_wins": quick_wins[:5], "grade": grade,
        "overall_verdict": "Good resume!" if total_score >= 60 else "Needs improvement",
        "recruiter_tip": "Keep your resume to 1-2 pages and use keywords from the job description."
    }

# ========== FastAPI App ==========
app = FastAPI(title="CareerPilot AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Auth Routes ==========
@app.post("/api/auth/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(SessionLocal)):
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(full_name=user_data.full_name, email=user_data.email, phone=user_data.phone, hashed_password=hash_password(user_data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return Token(access_token=create_token(user.id, user.email, user.role), token_type="bearer", user=UserResponse.model_validate(user))

@app.post("/api/auth/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(SessionLocal)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return Token(access_token=create_token(user.id, user.email, user.role), token_type="bearer", user=UserResponse.model_validate(user))

@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

# ========== Booking Routes ==========
@app.post("/api/booking/", response_model=BookingResponse)
def create_booking(booking: BookingCreate, db: Session = Depends(SessionLocal), current_user: User = Depends(get_current_user)):
    db_booking = Booking(user_id=current_user.id, **booking.dict())
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return BookingResponse.model_validate(db_booking)

@app.get("/api/booking/my")
def get_my_bookings(db: Session = Depends(SessionLocal), current_user: User = Depends(get_current_user)):
    return [BookingResponse.model_validate(b) for b in db.query(Booking).filter(Booking.user_id == current_user.id).order_by(Booking.booking_date.desc()).all()]

@app.put("/api/booking/{booking_id}/cancel")
def cancel_booking(booking_id: int, db: Session = Depends(SessionLocal), current_user: User = Depends(get_current_user)):
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = "cancelled"
    db.commit()
    return {"message": "Booking cancelled"}

@app.get("/api/booking/slots")
def get_slots(date: str):
    return {"date": date, "available_slots": ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM", "04:00 PM"]}

# ========== Contact Routes ==========
@app.post("/api/contact/")
def submit_contact(contact: ContactCreate, db: Session = Depends(SessionLocal)):
    db.add(Contact(**contact.dict()))
    db.commit()
    return {"message": "Message sent"}

# ========== Blog Routes ==========
@app.get("/api/blog/")
def get_blogs(limit: int = 50, tag: str = None, db: Session = Depends(SessionLocal)):
    query = db.query(Blog).filter(Blog.is_published == True)
    if tag and tag != "all":
        query = query.filter(Blog.tag == tag)
    return [BlogResponse.model_validate(b) for b in query.order_by(Blog.created_at.desc()).limit(limit).all()]

@app.get("/api/blog/{slug}")
def get_blog(slug: str, db: Session = Depends(SessionLocal)):
    blog = db.query(Blog).filter(Blog.slug == slug).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Not found")
    blog.views += 1
    db.commit()
    return BlogResponse.model_validate(blog)

@app.post("/api/blog/")
def create_blog(blog: BlogCreate, db: Session = Depends(SessionLocal), admin: User = Depends(get_admin_user)):
    db_blog = Blog(**blog.dict())
    db.add(db_blog)
    db.commit()
    db.refresh(db_blog)
    return BlogResponse.model_validate(db_blog)

@app.put("/api/blog/{blog_id}")
def update_blog(blog_id: int, blog: BlogCreate, db: Session = Depends(SessionLocal), admin: User = Depends(get_admin_user)):
    db_blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not db_blog:
        raise HTTPException(status_code=404, detail="Not found")
    for key, value in blog.dict().items():
        setattr(db_blog, key, value)
    db.commit()
    return BlogResponse.model_validate(db_blog)

@app.delete("/api/blog/{blog_id}")
def delete_blog(blog_id: int, db: Session = Depends(SessionLocal), admin: User = Depends(get_admin_user)):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(blog)
    db.commit()
    return {"message": "Deleted"}

# ========== Resume Routes ==========
@app.post("/api/resume/analyze")
async def analyze_resume(file: UploadFile = File(...), role: str = Form("general"), db: Session = Depends(SessionLocal), current_user: User = Depends(get_current_user)):
    content = await file.read()
    text = content.decode('utf-8', errors='ignore')
    result = analyze_resume_text(text, role)
    
    ats = ATSAnalysis(user_id=current_user.id, filename=file.filename, role=role, total_score=result["total_score"], keyword_score=result["keyword_score"], structure_score=result["structure_score"], word_count=result["word_count"], matched_keywords=result["matched_keywords"], missing_keywords=result["missing_keywords"], structure_checks=result["structure_checks"], strengths=result["strengths"], critical_fixes=result["critical_fixes"], quick_wins=result["quick_wins"], feedback=result["overall_verdict"])
    db.add(ats)
    db.commit()
    
    return {"scores": {"total_score": result["total_score"], "keyword_score": result["keyword_score"], "structure_score": result["structure_score"], "word_count": result["word_count"], "matched_keywords": result["matched_keywords"], "missing_keywords": result["missing_keywords"], "structure_checks": result["structure_checks"]}, "feedback": {"overall_verdict": result["overall_verdict"], "grade": result["grade"], "strengths": result["strengths"], "critical_fixes": result["critical_fixes"], "quick_wins": result["quick_wins"], "recruiter_tip": result["recruiter_tip"]}}

@app.get("/api/resume/ats-history")
def get_ats_history(db: Session = Depends(SessionLocal), current_user: User = Depends(get_current_user)):
    return db.query(ATSAnalysis).filter(ATSAnalysis.user_id == current_user.id).order_by(ATSAnalysis.created_at.desc()).all()

# ========== Admin Routes ==========
@app.get("/api/admin/dashboard")
def admin_dashboard(db: Session = Depends(SessionLocal), admin: User = Depends(get_admin_user)):
    return {"total_users": db.query(User).count(), "total_contacts": db.query(Contact).count(), "total_bookings": db.query(Booking).count(), "unread_contacts": db.query(Contact).filter(Contact.is_read == False).count(), "pending_bookings": db.query(Booking).filter(Booking.status == "pending").count(), "total_revenue": 0}

@app.get("/api/admin/users")
def get_all_users(limit: int = 100, db: Session = Depends(SessionLocal), admin: User = Depends(get_admin_user)):
    return [UserResponse.model_validate(u) for u in db.query(User).order_by(User.created_at.desc()).limit(limit).all()]

@app.get("/api/admin/contacts")
def get_all_contacts(limit: int = 100, db: Session = Depends(SessionLocal), admin: User = Depends(get_admin_user)):
    return db.query(Contact).order_by(Contact.created_at.desc()).limit(limit).all()

@app.put("/api/admin/contacts/{contact_id}/read")
def mark_read(contact_id: int, db: Session = Depends(SessionLocal), admin: User = Depends(get_admin_user)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if contact:
        contact.is_read = True
        db.commit()
    return {"message": "Marked read"}

@app.get("/api/admin/bookings")
def get_all_bookings(limit: int = 100, db: Session = Depends(SessionLocal), admin: User = Depends(get_admin_user)):
    return db.query(Booking).order_by(Booking.created_at.desc()).limit(limit).all()

@app.put("/api/admin/bookings/{booking_id}/confirm")
def confirm_booking(booking_id: int, db: Session = Depends(SessionLocal), admin: User = Depends(get_admin_user)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking:
        booking.status = "confirmed"
        db.commit()
    return {"message": "Booking confirmed"}

# ========== Health ==========
@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/")
def root():
    return {"message": "CareerPilot AI API is running!"}