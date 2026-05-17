from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models.database import get_db
from models.models import Blog
from schemas.schemas import BlogCreate, BlogOut, BlogDetailOut
from utils.auth import require_admin

router = APIRouter()

@router.get("/", response_model=List[BlogOut])
def get_blogs(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(Blog).filter(Blog.is_published == True)\
             .order_by(Blog.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/{slug}", response_model=BlogDetailOut)
def get_blog(slug: str, db: Session = Depends(get_db)):
    blog = db.query(Blog).filter(Blog.slug == slug, Blog.is_published == True).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog post not found")
    return blog

@router.post("/", response_model=BlogDetailOut, status_code=201)
def create_blog(payload: BlogCreate, db: Session = Depends(get_db),
                _=Depends(require_admin)):
    if db.query(Blog).filter(Blog.slug == payload.slug).first():
        raise HTTPException(status_code=400, detail="Slug already exists")
    blog = Blog(**payload.model_dump())
    db.add(blog); db.commit(); db.refresh(blog)
    return blog

@router.put("/{blog_id}", response_model=BlogDetailOut)
def update_blog(blog_id: int, payload: BlogCreate,
                db: Session = Depends(get_db), _=Depends(require_admin)):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    for k, v in payload.model_dump().items():
        setattr(blog, k, v)
    db.commit(); db.refresh(blog)
    return blog

@router.delete("/{blog_id}")
def delete_blog(blog_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if blog:
        db.delete(blog); db.commit()
    return {"message": "Blog deleted"}
