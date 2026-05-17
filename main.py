from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, contact, booking, payment, admin, blog, resume
from models.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CareerPilot AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,    prefix="/api/auth",    tags=["Auth"])
app.include_router(contact.router, prefix="/api/contact", tags=["Contact"])
app.include_router(booking.router, prefix="/api/booking", tags=["Booking"])
app.include_router(payment.router, prefix="/api/payment", tags=["Payment"])
app.include_router(admin.router,   prefix="/api/admin",   tags=["Admin"])
app.include_router(blog.router,    prefix="/api/blog",    tags=["Blog"])
app.include_router(resume.router,  prefix="/api/resume",  tags=["Resume"])

@app.get("/")
def root():
    return {"message": "CareerPilot AI API is running!"}

@app.get("/health")
def health():
    return {"status": "healthy"}
