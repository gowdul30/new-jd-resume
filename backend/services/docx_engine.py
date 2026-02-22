"""
DOCX Extraction Engine
- Extracts text for analysis
- Extracts specific sections for targeted feedback
"""

import io
from docx import Document

# Keywords for section detection
SUMMARY_KEYWORDS = {"summary", "professional summary", "profile", "objective", "about me", "overview", "executive summary"}
EXPERIENCE_KEYWORDS = {"experience", "work experience", "professional experience", "employment", "career", "work history", "employment history"}
STOP_KEYWORDS = {"education", "skills", "certifications", "projects", "awards", "languages", "references", "volunteer", "organizations", "links"}

def _is_heading(para) -> bool:
    if para.style and para.style.name and "heading" in para.style.name.lower():
        return True
    text = para.text.strip()
    if not text:
        return False
    if all(run.bold for run in para.runs if run.text.strip()):
        return True
    return False

def extract_docx_sections(file_path_or_bytes) -> dict:
    if isinstance(file_path_or_bytes, (str, bytes)):
        doc = Document(io.BytesIO(file_path_or_bytes) if isinstance(file_path_or_bytes, bytes) else file_path_or_bytes)
    else:
        doc = Document(io.BytesIO(file_path_or_bytes))

    sections = {"summary": [], "experience": [], "all_text": ""}
    all_text_parts = []
    current_section = None

    for para_idx, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        all_text_parts.append(text)
        if not text: continue

        text_lower = text.lower()
        if _is_heading(para) or (len(text) < 60 and text_lower in (SUMMARY_KEYWORDS | EXPERIENCE_KEYWORDS | STOP_KEYWORDS)):
            if text_lower in SUMMARY_KEYWORDS: current_section = "summary"
            elif text_lower in EXPERIENCE_KEYWORDS: current_section = "experience"
            elif text_lower in STOP_KEYWORDS: current_section = None
            continue

        if current_section in ("summary", "experience"):
            sections[current_section].append({"text": text})

    sections["all_text"] = "\n".join(all_text_parts)
    return sections

def get_full_docx_text(file_path_or_bytes) -> str:
    if isinstance(file_path_or_bytes, bytes):
        doc = Document(io.BytesIO(file_path_or_bytes))
    else:
        doc = Document(file_path_or_bytes)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
