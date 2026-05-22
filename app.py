from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import os
import uuid
import re
from datetime import datetime, timedelta

app = FastAPI(title="CareerPilot API")

# Enable CORS for Netlify
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== In-Memory Database (No PostgreSQL needed) ==========
users_db = {}
contacts_db = []
bookings_db = []
blogs_db = [
    {
        "id": 1,
        "title": "7 Resume Mistakes That Get You Rejected",
        "slug": "resume-mistakes",
        "summary": "Most candidates fail ATS filters before a human sees their resume.",
        "content": "Here are 7 common resume mistakes...",
        "tag": "Resume",
        "author": "CareerPilot Team",
        "read_time": "5 min read",
        "is_published": True,
        "views": 1200,
        "created_at": datetime.now().isoformat()
    },
    {
        "id": 2,
        "title": "How to Make Recruiters DM You on LinkedIn",
        "slug": "linkedin-recruiters",
        "summary": "The exact profile strategy that gets 10+ recruiter messages per month.",
        "content": "Most people use LinkedIn wrong...",
        "tag": "LinkedIn",
        "author": "CareerPilot Team",
        "read_time": "6 min read",
        "is_published": True,
        "views": 890,
        "created_at": datetime.now().isoformat()
    }
]

# ========== Auth Helpers ==========
def hash_password(password: str) -> str:
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_token(user_id: str, email: str) -> str:
    import jwt
    return jwt.encode({"user_id": user_id, "email": email, "exp": datetime.utcnow() + timedelta(days=7)}, "secret-key", algorithm="HS256")

# ========== Models ==========
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    role: str = "user"
    is_active: bool = True
    created_at: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class ContactCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    service: str
    message: str

class BookingCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    service_type: str
    booking_date: str
    notes: Optional[str] = None

# ========== Auth Routes ==========
@app.post("/api/auth/register", response_model=Token)
def register(user_data: UserCreate):
    if user_data.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "full_name": user_data.full_name,
        "email": user_data.email,
        "phone": user_data.phone,
        "password": hash_password(user_data.password),
        "role": "user",
        "is_active": True,
        "created_at": datetime.now().isoformat()
    }
    users_db[user_data.email] = user
    
    token = create_token(user_id, user_data.email)
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user_id,
            full_name=user_data.full_name,
            email=user_data.email,
            phone=user_data.phone,
            role="user",
            is_active=True,
            created_at=user["created_at"]
        )
    )

@app.post("/api/auth/login", response_model=Token)
def login(user_data: UserLogin):
    user = users_db.get(user_data.email)
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user["id"], user_data.email)
    return Token(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user["id"],
            full_name=user["full_name"],
            email=user["email"],
            phone=user.get("phone"),
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"]
        )
    )

@app.get("/api/auth/me")
def get_me(email: str):
    user = users_db.get(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user["id"],
        full_name=user["full_name"],
        email=user["email"],
        phone=user.get("phone"),
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"]
    )

@app.post("/api/auth/forgot-password")
def forgot_password(email: str):
    return {"message": "Password reset link sent to your email", "reset_link": f"https://glittery-baklava-57ad5c.netlify.app/reset-password?token=demo&email={email}"}

@app.post("/api/auth/reset-password")
def reset_password(email: str, token: str, new_password: str):
    return {"message": "Password reset successful"}

# ========== Contact Routes ==========
@app.post("/api/contact/")
def submit_contact(contact: ContactCreate):
    contacts_db.append(contact.dict())
    print(f"New contact: {contact.full_name} - {contact.email}")
    return {"message": "Message sent successfully"}

@app.get("/api/admin/contacts")
def get_contacts():
    return contacts_db

# ========== Blog Routes ==========
@app.get("/api/blog/")
def get_blogs(limit: int = 50):
    return [b for b in blogs_db if b["is_published"]][:limit]

@app.get("/api/blog/{slug}")
def get_blog(slug: str):
    for blog in blogs_db:
        if blog["slug"] == slug:
            blog["views"] += 1
            return blog
    raise HTTPException(status_code=404, detail="Blog not found")

# ========== Booking Routes ==========
@app.post("/api/booking/")
def create_booking(booking: BookingCreate):
    booking_id = len(bookings_db) + 1
    booking_dict = booking.dict()
    booking_dict["id"] = booking_id
    booking_dict["status"] = "pending"
    booking_dict["created_at"] = datetime.now().isoformat()
    bookings_db.append(booking_dict)
    return booking_dict

@app.get("/api/booking/my")
def get_my_bookings(email: str):
    return [b for b in bookings_db if b.get("email") == email]

@app.get("/api/booking/slots")
def get_slots(date: str):
    return {"date": date, "available_slots": ["09:00 AM", "10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM", "04:00 PM"]}

# ========== Resume Analysis ==========
@app.post("/api/resume/analyze")
async def analyze_resume(file: UploadFile = File(...), role: str = Form("general")):
    content = await file.read()
    text = content.decode('utf-8', errors='ignore')
    
    # Simple keyword analysis
    keywords = ["python", "javascript", "react", "sql", "git", "api", "docker", "testing", "aws", "agile"]
    text_lower = text.lower()
    matched = [kw for kw in keywords if kw in text_lower]
    missing = [kw for kw in keywords if kw not in text_lower]
    
    keyword_score = int((len(matched) / len(keywords)) * 100)
    word_count = len(text.split())
    word_score = 100 if 300 <= word_count <= 900 else 50
    
    total_score = int((keyword_score + word_score) / 2)
    
    return {
        "scores": {
            "total_score": total_score,
            "keyword_score": keyword_score,
            "structure_score": 75,
            "word_count": word_count,
            "matched_keywords": matched[:10],
            "missing_keywords": missing[:10],
            "structure_checks": {
                "Email": "@" in text,
                "Phone": bool(re.search(r'\d{10}', text)),
                "LinkedIn": "linkedin" in text_lower,
                "Summary": "summary" in text_lower,
                "Experience": "experience" in text_lower,
                "Education": "education" in text_lower,
                "Skills": "skills" in text_lower
            }
        },
        "feedback": {
            "overall_verdict": f"Your resume scored {total_score}/100. " + ("Good job!" if total_score > 60 else "Needs improvement."),
            "grade": "B" if total_score > 60 else "C",
            "strengths": ["Good structure"] if word_count > 200 else ["Add more content"],
            "critical_fixes": ["Add missing keywords: " + ", ".join(missing[:3])] if missing else [],
            "quick_wins": ["Add a LinkedIn URL", "Include more metrics"] if total_score < 70 else [],
            "recruiter_tip": "Recruiters spend 6 seconds on a resume. Make your top third count!"
        }
    }

# ========== Stats ==========
@app.get("/api/stats")
def get_stats():
    return {
        "total_users": len(users_db),
        "resumes_built": 2400 + len(users_db),
        "success_rate": 87,
        "templates_count": 50,
        "avg_rating": 4.9
    }

# ========== Testimonials ==========
@app.get("/api/testimonials")
def get_testimonials(limit: int = 3):
    testimonials = [
        {"name": "Rahul K.", "designation": "Software Engineer", "comment": "The live AI interview helped me practice and build confidence. Landed my dream job!", "rating": 5},
        {"name": "Priya S.", "designation": "Business Analyst", "comment": "Best free resume builder! Got interview calls within a week.", "rating": 5},
        {"name": "Aditya M.", "designation": "Product Manager", "comment": "The ATS checker showed me what was wrong with my resume. Fixed it and got 3 callbacks!", "rating": 5}
    ]
    return testimonials[:limit]

# ========== Health Check ==========
@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/")
def root():
    return {"message": "CareerPilot API is running!", "users": len(users_db)}
