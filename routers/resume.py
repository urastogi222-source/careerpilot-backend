import os, re, json
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models.database import get_db
from models.models import User
from utils.auth import get_current_user
import pdfplumber
import docx2txt
from anthropic import Anthropic

router = APIRouter()
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── ATS Keyword bank per role ─────────────────────────
ROLE_KEYWORDS = {
    "software_engineer": [
        "python","java","javascript","react","node","sql","api","git",
        "agile","scrum","docker","kubernetes","ci/cd","rest","microservices",
        "problem solving","algorithms","data structures","testing","aws"
    ],
    "data_analyst": [
        "python","sql","excel","tableau","power bi","pandas","numpy",
        "data visualization","machine learning","statistics","etl",
        "reporting","dashboard","analytics","r","matplotlib"
    ],
    "product_manager": [
        "product roadmap","agile","scrum","stakeholder","user stories",
        "kpi","metrics","market research","jira","confluence","wireframe",
        "a/b testing","go-to-market","prioritization","customer discovery"
    ],
    "mba_management": [
        "leadership","strategy","p&l","revenue","stakeholder management",
        "business development","team management","budget","forecasting",
        "operations","consulting","presentation","negotiation","excel","analytics"
    ],
    "general": [
        "communication","leadership","teamwork","problem solving","analytical",
        "project management","microsoft office","excel","presentation",
        "time management","critical thinking","adaptability","result-oriented"
    ]
}

def extract_text(file: UploadFile, content: bytes) -> str:
    """Extract text from PDF or DOCX."""
    filename = file.filename.lower()
    if filename.endswith(".pdf"):
        import io
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif filename.endswith(".docx"):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        text = docx2txt.process(tmp_path)
        os.unlink(tmp_path)
        return text
    elif filename.endswith(".txt"):
        return content.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Upload PDF, DOCX, or TXT.")

def rule_based_ats(text: str, role: str) -> dict:
    """Fast rule-based ATS scoring."""
    text_lower = text.lower()
    keywords = ROLE_KEYWORDS.get(role, ROLE_KEYWORDS["general"])

    matched   = [k for k in keywords if k in text_lower]
    missing   = [k for k in keywords if k not in text_lower]
    kw_score  = round((len(matched) / len(keywords)) * 100)

    # Structural checks
    has_email   = bool(re.search(r'[\w.+-]+@[\w-]+\.\w+', text))
    has_phone   = bool(re.search(r'[\+\(]?[0-9][0-9\s\-\(\)]{8,}[0-9]', text))
    has_linkedin= "linkedin" in text_lower
    has_summary = any(w in text_lower for w in ["summary","objective","profile","about"])
    has_exp     = any(w in text_lower for w in ["experience","work history","employment"])
    has_edu     = any(w in text_lower for w in ["education","degree","university","college","b.tech","mba","b.sc"])
    has_skills  = "skills" in text_lower
    has_bullets = text.count("•") + text.count("-") + text.count("*") > 5
    word_count  = len(text.split())
    good_length = 300 < word_count < 900

    structure_checks = {
        "Contact Info (Email)":   has_email,
        "Phone Number":           has_phone,
        "LinkedIn URL":           has_linkedin,
        "Professional Summary":   has_summary,
        "Work Experience":        has_exp,
        "Education Section":      has_edu,
        "Skills Section":         has_skills,
        "Bullet Points Used":     has_bullets,
        "Good Length (300-900w)": good_length,
    }
    passed = sum(structure_checks.values())
    struct_score = round((passed / len(structure_checks)) * 100)
    total_score  = round(kw_score * 0.55 + struct_score * 0.45)

    return {
        "total_score":       total_score,
        "keyword_score":     kw_score,
        "structure_score":   struct_score,
        "word_count":        word_count,
        "matched_keywords":  matched,
        "missing_keywords":  missing[:8],
        "structure_checks":  structure_checks,
        "passed_checks":     passed,
        "total_checks":      len(structure_checks),
    }

def ai_feedback(text: str, role: str, scores: dict) -> dict:
    """Use Claude AI for deep resume feedback."""
    prompt = f"""You are an expert resume coach and ATS specialist. Analyze this resume for a {role.replace('_',' ')} role.

ATS Score: {scores['total_score']}/100
Keyword Score: {scores['keyword_score']}/100
Structure Score: {scores['structure_score']}/100
Matched Keywords: {', '.join(scores['matched_keywords'][:10])}
Missing Keywords: {', '.join(scores['missing_keywords'])}

RESUME TEXT:
{text[:3000]}

Respond ONLY with a valid JSON object (no markdown, no extra text):
{{
  "overall_verdict": "one sentence verdict",
  "grade": "A/B/C/D/F",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "critical_fixes": ["fix 1", "fix 2", "fix 3"],
  "quick_wins": ["quick win 1", "quick win 2", "quick win 3"],
  "missing_sections": ["section 1", "section 2"],
  "tone_feedback": "one sentence about writing tone and style",
  "impact_score": 75,
  "recruiter_tip": "one insider tip from a recruiter's perspective"
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        return {
            "overall_verdict": "Resume analyzed successfully.",
            "grade": "B" if scores['total_score'] >= 60 else "C",
            "strengths": matched[:3] if (matched := scores['matched_keywords']) else ["Resume submitted"],
            "critical_fixes": scores['missing_keywords'][:3],
            "quick_wins": ["Add more industry keywords", "Quantify achievements", "Add LinkedIn URL"],
            "missing_sections": [],
            "tone_feedback": "Review tone for professionalism.",
            "impact_score": scores['total_score'],
            "recruiter_tip": "Tailor your resume for each job description."
        }

@router.post("/analyze")
async def analyze_resume(
    file: UploadFile = File(...),
    role: str = "general",
    db: Session = Depends(get_db),
):
    """
    Upload a resume (PDF/DOCX/TXT) and get ATS score + AI feedback.
    role options: software_engineer, data_analyst, product_manager, mba_management, general
    """
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB.")

    content = await file.read()
    text    = extract_text(file, content)

    if len(text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Could not extract text from file. Try a text-based PDF.")

    scores   = rule_based_ats(text, role)
    feedback = ai_feedback(text, role, scores)

    return {
        "filename":    file.filename,
        "role":        role,
        "scores":      scores,
        "feedback":    feedback,
        "status":      "success"
    }

@router.get("/roles")
def get_roles():
    """Get available roles for ATS analysis."""
    return {
        "roles": [
            {"id": "software_engineer", "label": "Software Engineer / Developer"},
            {"id": "data_analyst",      "label": "Data Analyst / Data Scientist"},
            {"id": "product_manager",   "label": "Product Manager"},
            {"id": "mba_management",    "label": "MBA / Management"},
            {"id": "general",           "label": "General / Other"},
        ]
    }
