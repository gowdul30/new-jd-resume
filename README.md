# 🚀 ResumeAI — Zero-Format-Loss Resume Tailor & ATS Scorer

Surgically rewrite your resume to match any job description — without losing a single font, margin, or layout element. Powered by **Groq (llama-3.3-70b-versatile)**.

---

## ✨ Features

- **Zero-format-loss DOCX rewriting** — only `.text` is changed, every font/bold/alignment stays intact
- **PDF surgical swap** — redacts and overlays text at exact coordinates with original font metadata
- **Multi-site JD scraper** — LinkedIn, Indeed, Greenhouse, Lever, Workday, or paste manually
- **Anti-hallucination guardrails** — AI cannot add new jobs, certifications, or experience
- **±5% character count enforcement** — prevents layout overflow (no 1-page → 1.5-page disasters)
- **ATS Score (0–100)** — Keyword Match + Role Relevancy + Formatting Simplicity
- **Dark glassmorphism UI** — animated score gauge, step progress tracker, keyword tags

---

## 🔧 Setup

### Prerequisites
- Python 3.9+ ([download](https://www.python.org/downloads/))
- A free [Groq API key](https://console.groq.com) (no credit card required)

### 1. Configure API Key

```bash
# Copy the example env file
copy .env.example .env
```

Open `.env` and replace `your_groq_api_key_here` with your actual key:
```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

### 2. Start the App

**Option A — One-click (Windows):**
```
Double-click start.bat
```

**Option B — Manual:**
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### 3. Open in Browser

Navigate to: **[http://localhost:8000](http://localhost:8000)**

---

## 🗂️ Project Structure

```
jd-resume/
├── backend/
│   ├── main.py                # FastAPI entry point
│   ├── requirements.txt
│   ├── routers/
│   │   └── optimize.py        # /api/optimize + /api/download
│   ├── services/
│   │   ├── docx_engine.py     # DOCX surgical swap engine
│   │   ├── pdf_engine.py      # PDF surgical swap engine
│   │   ├── llm.py             # Groq rewrite + ATS scoring
│   │   ├── ats_scorer.py      # Keyword overlap pre-scorer
│   │   └── scraper.py         # JD URL scraper
│   └── utils/
│       └── text_utils.py      # Length constraint helpers
├── frontend/
│   ├── index.html             # Single-page UI
│   ├── style.css              # Dark glassmorphism design
│   └── app.js                 # State machine + animations
├── .env.example               # API key template
├── .gitignore
└── start.bat                  # One-click Windows launcher
```

---

## 🛡️ AI Guardrails

| Guardrail | Behavior |
|-----------|----------|
| Anti-hallucination | Cannot add new employers, certifications, skills, or experience years |
| Natural tone | No keyword stuffing — reads like a human wrote it |
| Length constraint | Each rewritten block must be within **±5%** of original character count |
| Format preservation | DOCX: only `.text` modified. PDF: exact coordinate re-overlay |

---

## 📊 ATS Score Breakdown

| Dimension | Max |
|-----------|-----|
| Keyword Match | 40 |
| Role Relevancy | 40 |
| Formatting Simplicity | 20 |
| **Total** | **100** |

---

## ⚠️ Known Limitations

- **LinkedIn scraping** may fail (anti-bot protection) — use the **Paste Text** tab as fallback
- **PDF custom fonts** (Calibri, Garamond, etc.) — best-effort font matching; may render in Helvetica/Times
- Session storage is in-memory — restarting the server clears download sessions

---

## 🔑 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/optimize` | Upload resume + JD → returns ATS score + session_id |
| `GET` | `/api/download/{session_id}` | Download optimized file |
| `GET` | `/api/health` | Health check |
