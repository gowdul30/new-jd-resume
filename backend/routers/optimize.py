"""
FastAPI optimize router — the core pipeline endpoint.

POST /api/optimize
  - Accepts: uploaded resume file + JD text or URL
  - Returns: session_id + ATS score dict

GET /api/download/{session_id}
  - Returns: the optimized resume file as a download
"""

import uuid
import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import aiofiles

from services.scraper import scrape_jd, parse_manual_jd
from services.docx_engine import extract_docx_sections, inject_docx_rewrites, get_full_docx_text
from services.pdf_engine import extract_pdf_sections, inject_pdf_rewrites, get_full_pdf_text
from services.llm import rewrite_sections, score_resume
from services.ats_scorer import calculate_keyword_overlap

router = APIRouter()

# In-memory session store (temp files keyed by session_id)
# In production, use Redis or a proper storage backend
SESSION_STORE: dict[str, dict] = {}


@router.post("/optimize")
async def optimize_resume(
    file: UploadFile = File(...),
    jd_url: Optional[str] = Form(None),
    jd_text: Optional[str] = Form(None),
):
    """
    Main pipeline:
    1. Read uploaded resume
    2. Get JD (scrape URL or use pasted text)
    3. Extract sections
    4. Rewrite via Groq
    5. Inject rewrites
    6. Score optimized resume
    7. Store in session, return score
    """
    # --- Validate file type ---
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in (".docx", ".pdf"):
        raise HTTPException(status_code=400, detail="Only DOCX and PDF files are supported.")

    file_bytes = await file.read()

    # --- Get Job Description ---
    if jd_url and jd_url.strip():
        jd_data = scrape_jd(jd_url.strip())
        if jd_data.get("error"):
            # If scraping failed and no manual text, raise error
            if not jd_text or not jd_text.strip():
                raise HTTPException(
                    status_code=422,
                    detail=f"JD scraping failed: {jd_data['error']}. Please paste the JD text manually."
                )
        combined_jd = jd_data["description"] or jd_text or ""
    elif jd_text and jd_text.strip():
        jd_data = parse_manual_jd(jd_text.strip())
        combined_jd = jd_data["description"]
    else:
        raise HTTPException(status_code=400, detail="Please provide a JD URL or paste the job description text.")

    if not combined_jd.strip():
        raise HTTPException(status_code=422, detail="Could not extract job description content.")

    # --- Extract resume sections ---
    try:
        if ext == ".docx":
            sections = extract_docx_sections(file_bytes)
        else:
            sections = extract_pdf_sections(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume parsing failed: {str(e)}")

    original_text = sections.get("all_text", "")

    # --- Rewrite via Groq ---
    try:
        rewrites = rewrite_sections(sections, combined_jd)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM rewrite failed: {str(e)}")

    # --- Apply surgical swap ---
    try:
        if ext == ".docx":
            optimized_bytes = inject_docx_rewrites(file_bytes, rewrites)
            optimized_text = get_full_docx_text(optimized_bytes)
        else:
            optimized_bytes = inject_pdf_rewrites(file_bytes, rewrites)
            optimized_text = get_full_pdf_text(optimized_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume injection failed: {str(e)}")

    # --- ATS Scoring (LLM-based) ---
    try:
        llm_score = score_resume(optimized_text, combined_jd)
    except Exception as e:
        # Fallback to keyword-overlap score if LLM scoring fails
        kw = calculate_keyword_overlap(optimized_text, combined_jd)
        llm_score = {
            "total": kw["quick_score"],
            "keyword_match": int(kw["match_rate"] * 40),
            "role_relevancy": 0,
            "formatting_simplicity": 20,
            "feedback": "LLM scoring unavailable. Quick keyword score used.",
            "top_matched_keywords": kw["matched"][:5],
            "missing_keywords": kw["missing"][:5],
        }

    # --- Quick keyword validation ---
    kw_overlap = calculate_keyword_overlap(optimized_text, combined_jd)

    # --- Store session ---
    session_id = str(uuid.uuid4())
    SESSION_STORE[session_id] = {
        "bytes": optimized_bytes,
        "filename": f"optimized_{filename}",
        "content_type": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if ext == ".docx"
            else "application/pdf"
        ),
        "ext": ext,
    }

    return JSONResponse({
        "session_id": session_id,
        "job_title": jd_data.get("title", "Unknown"),
        "ats_score": llm_score,
        "keyword_overlap": kw_overlap,
        "sections_found": {
            "summary_blocks": len(sections.get("summary", [])),
            "experience_blocks": len(sections.get("experience", [])),
        },
    })


@router.get("/download/{session_id}")
async def download_resume(session_id: str):
    """
    Returns the optimized resume file for download.
    """
    session = SESSION_STORE.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired.")

    import io
    file_stream = io.BytesIO(session["bytes"])
    file_stream.seek(0)

    return StreamingResponse(
        file_stream,
        media_type=session["content_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{session["filename"]}"'
        },
    )
