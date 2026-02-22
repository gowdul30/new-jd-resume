"""
FastAPI optimize router — Analysis and Suggestions only.
"""

import uuid
import traceback
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import fitz

from services.scraper import scrape_jd, parse_manual_jd
from services.docx_engine import extract_docx_sections, get_full_docx_text
from services.pdf_engine_v2 import find_resume_sections
from services.pdf_engine import get_full_pdf_text
from services.llm import rewrite_sections, score_resume
from services.ats_scorer import calculate_keyword_overlap

router = APIRouter()

@router.post("/optimize")
async def optimize_resume(
    file: UploadFile = File(...),
    jd_url: Optional[str] = Form(None),
    jd_text: Optional[str] = Form(None),
):
    """
    Pipeline:
    1. Read resume
    2. Get JD
    3. Extract sections
    4. Generate suggestions via Groq
    5. Score resume
    6. Return analysis JSON
    """
    filename = file.filename or ""
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ("docx", "pdf"):
        raise HTTPException(status_code=400, detail="Only DOCX and PDF files are supported.")

    file_bytes = await file.read()

    # --- Get Job Description ---
    if jd_url and jd_url.strip():
        jd_data = scrape_jd(jd_url.strip())
        if jd_data.get("error") and (not jd_text or not jd_text.strip()):
            raise HTTPException(status_code=422, detail=f"JD scraping failed: {jd_data['error']}")
        combined_jd = jd_data["description"] or jd_text or ""
    elif jd_text and jd_text.strip():
        jd_data = parse_manual_jd(jd_text.strip())
        combined_jd = jd_data["description"]
    else:
        raise HTTPException(status_code=400, detail="Please provide a JD URL or text.")

    if not combined_jd.strip():
        raise HTTPException(status_code=422, detail="Could not extract job description content.")

    # --- Extract resume sections ---
    try:
        if ext == "docx":
            sections = extract_docx_sections(file_bytes)
            full_text = get_full_docx_text(file_bytes)
        else:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            sections = find_resume_sections(doc)
            doc.close()
            full_text = get_full_pdf_text(file_bytes)
    except Exception as e:
        print(f"[ERROR] Parsing failed: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Resume parsing failed: {str(e)}")

    # --- Analysis via Groq ---
    try:
         print(f"[DEBUG] Sending {len(sections.get('experience', []))} experience blocks to LLM...")
         analysis = rewrite_sections(sections, combined_jd)
    except Exception as e:
        print(f"[ERROR] Analysis failed: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    # --- ATS Scoring ---
    try:
        score = score_resume(full_text, combined_jd)
    except Exception as e:
        # Fallback
        kw = calculate_keyword_overlap(full_text, combined_jd)
        score = {
            "total": kw["quick_score"],
            "keyword_match": int(kw["match_rate"] * 40),
            "role_relevancy": 0,
            "formatting_simplicity": 20,
            "feedback": "Deep scoring failed. Basic keyword score used.",
            "top_matched_keywords": kw["matched"][:5],
            "missing_keywords": kw["missing"][:5],
        }

    return JSONResponse({
        "job_title": jd_data.get("title", "Unknown"),
        "ats_score": score,
        "analysis": analysis,
        "sections_found": {
            "summary_blocks": len(sections.get("summary", [])),
            "experience_blocks": len(sections.get("experience", [])),
        },
    })
