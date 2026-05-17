# CareerPilot AI — Backend (FastAPI + PostgreSQL)

## 🗂 Project Structure
```
backend/
├── main.py                  # FastAPI app entry point
├── requirements.txt
├── .env.example             # Copy to .env and fill values
├── models/
│   ├── database.py          # DB connection & session
│   └── models.py            # SQLAlchemy ORM models
├── schemas/
│   └── schemas.py           # Pydantic request/response schemas
├── routers/
│   ├── auth.py              # Register, Login, Profile
│   ├── contact.py           # Contact form submissions
│   ├── booking.py           # Consultation bookings
│   ├── payment.py           # Razorpay payment integration
│   ├── admin.py             # Admin dashboard & management
│   └── blog.py              # Blog CRUD
└── utils/
    ├── auth.py              # JWT helpers, password hashing
    └── email.py             # SendGrid email utility
```

## ⚙️ Setup

### 1. Prerequisites
- Python 3.11+
- PostgreSQL running locally or on a cloud (Railway, Supabase, etc.)

### 2. Clone & Install
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your actual values
```

### 4. Create PostgreSQL Database
```sql
CREATE DATABASE careerpilot;
```

### 5. Run Migrations (tables auto-created on startup)
```bash
uvicorn main:app --reload
# Tables are created automatically via SQLAlchemy
```

### 6. Run the Server
```bash
uvicorn main:app --reload --port 8000
```

API Docs available at: http://localhost:8000/docs

---

## 🔌 API Endpoints

### Auth
| Method | Endpoint            | Description        |
|--------|---------------------|--------------------|
| POST   | /api/auth/register  | Register new user  |
| POST   | /api/auth/login     | Login, get token   |
| GET    | /api/auth/me        | Get current user   |
| PUT    | /api/auth/me        | Update profile     |

### Contact
| Method | Endpoint        | Description           |
|--------|-----------------|-----------------------|
| POST   | /api/contact/   | Submit contact form   |

### Booking
| Method | Endpoint                      | Description          |
|--------|-------------------------------|----------------------|
| POST   | /api/booking/                 | Create booking       |
| GET    | /api/booking/my               | My bookings          |
| GET    | /api/booking/slots?date=...   | Available slots      |
| PUT    | /api/booking/{id}/cancel      | Cancel booking       |

### Payment (Razorpay)
| Method | Endpoint                   | Description          |
|--------|----------------------------|----------------------|
| POST   | /api/payment/create-order  | Create Razorpay order|
| POST   | /api/payment/verify        | Verify payment       |
| GET    | /api/payment/my            | My payments          |

### Admin (requires admin role)
| Method | Endpoint                          | Description         |
|--------|-----------------------------------|---------------------|
| GET    | /api/admin/dashboard              | Stats overview      |
| GET    | /api/admin/contacts               | All contacts        |
| PUT    | /api/admin/contacts/{id}/read     | Mark read           |
| GET    | /api/admin/bookings               | All bookings        |
| PUT    | /api/admin/bookings/{id}/confirm  | Confirm booking     |
| GET    | /api/admin/users                  | All users           |

### Blog
| Method | Endpoint          | Description          |
|--------|-------------------|----------------------|
| GET    | /api/blog/        | List published blogs |
| GET    | /api/blog/{slug}  | Get single blog      |
| POST   | /api/blog/        | Create blog (admin)  |
| PUT    | /api/blog/{id}    | Update blog (admin)  |
| DELETE | /api/blog/{id}    | Delete blog (admin)  |

---

## 🚀 Deployment Options
- **Railway** — Connect GitHub repo, add PostgreSQL plugin, set env vars
- **Render** — Free tier, add PostgreSQL addon
- **Heroku** — With Postgres add-on
- **VPS (DigitalOcean/AWS EC2)** — Run with `gunicorn` behind Nginx

## 🔑 Getting API Keys
- **Razorpay**: https://dashboard.razorpay.com → Settings → API Keys
- **SendGrid**: https://app.sendgrid.com → Settings → API Keys
