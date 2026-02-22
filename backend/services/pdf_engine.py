"""
PDF Surgical Swap Engine
Uses PyMuPDF (fitz) to:
1. Map text block coordinates + font metadata
2. Redact original text regions
3. Overlay new text using the original font size and approximate style

Font matching note: Custom embedded fonts (e.g., Calibri.ttf) may not be available
in the PDF renderer. We default to Helvetica/Times as closest alternatives.
"""

import io
import fitz  # PyMuPDF
from typing import Optional

from utils.text_utils import enforce_length_constraint


# Keywords that signal the start of target sections
SUMMARY_KEYWORDS = {"summary", "professional summary", "profile", "objective", "about me", "overview"}
EXPERIENCE_KEYWORDS = {"experience", "work experience", "professional experience", "employment", "career"}
STOP_KEYWORDS = {"education", "skills", "certifications", "projects", "awards", "references"}


def _match_section(text: str) -> Optional[str]:
    t = text.strip().lower()
    if t in SUMMARY_KEYWORDS:
        return "summary"
    if t in EXPERIENCE_KEYWORDS:
        return "experience"
    if t in STOP_KEYWORDS:
        return "stop"
    return None


def extract_pdf_sections(file_path_or_bytes) -> dict:
    """
    Extracts text blocks from Summary and Experience sections of a PDF resume.

    Returns:
        {
            "summary": [
                {
                    "page": int,
                    "rect": [x0, y0, x1, y1],
                    "text": str,
                    "fontsize": float,
                    "fontname": str,
                    "color": int,
                    "block_idx": int
                }
            ],
            "experience": [...],
            "all_text": str
        }
    """
    if isinstance(file_path_or_bytes, bytes):
        doc = fitz.open(stream=file_path_or_bytes, filetype="pdf")
    else:
        doc = fitz.open(file_path_or_bytes)

    sections = {"summary": [], "experience": [], "all_text": ""}
    all_text_parts = []
    current_section = None

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        for block_idx, block in enumerate(blocks):
            if block.get("type") != 0:  # 0 = text block
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue

                    all_text_parts.append(text)

                    # Check if this span is a section heading
                    section_match = _match_section(text)
                    if section_match == "stop":
                        current_section = None
                        continue
                    elif section_match in ("summary", "experience"):
                        current_section = section_match
                        continue

                    if current_section in ("summary", "experience"):
                        rect = span["bbox"]  # (x0, y0, x1, y1)
                        sections[current_section].append({
                            "page": page_num,
                            "rect": list(rect),
                            "text": text,
                            "fontsize": span.get("size", 11.0),
                            "fontname": span.get("font", "Helvetica"),
                            "color": span.get("color", 0),
                            "block_idx": block_idx,
                        })

    doc.close()
    sections["all_text"] = "\n".join(all_text_parts)
    return sections


def _map_font(fontname: str) -> str:
    """
    Map PDF-embedded font names to PyMuPDF built-in fonts.
    Picks the closest available standard font.
    """
    name = fontname.lower()
    if any(k in name for k in ["bold", "heavy", "black"]):
        if any(k in name for k in ["italic", "oblique"]):
            return "tibo"   # Times-BoldItalic
        return "helv"       # Helvetica (bold not directly available as separate name, use helv)
    if any(k in name for k in ["italic", "oblique"]):
        return "tiit"       # Times-Italic
    if any(k in name for k in ["times", "serif", "georgia", "garamond"]):
        return "tiro"       # Times-Roman
    return "helv"           # Helvetica (default sans-serif)


def inject_pdf_rewrites(
    file_path_or_bytes,
    rewrites: dict,   # {"summary": [...new texts...], "experience": [...]}
    tolerance: float = 0.05,
) -> bytes:
    """
    Redacts original text blocks and overlays new text in the PDF.

    Returns bytes of the modified PDF.
    """
    if isinstance(file_path_or_bytes, bytes):
        doc = fitz.open(stream=file_path_or_bytes, filetype="pdf")
    else:
        doc = fitz.open(file_path_or_bytes)

    # We need to re-extract to get fresh rect mappings
    if isinstance(file_path_or_bytes, bytes):
        sections = extract_pdf_sections(file_path_or_bytes)
    else:
        with open(file_path_or_bytes, "rb") as f:
            sections = extract_pdf_sections(f.read())

    for section_name in ("summary", "experience"):
        entries = sections.get(section_name, [])
        new_texts = rewrites.get(section_name, [])

        for i, entry in enumerate(entries):
            if i >= len(new_texts):
                break

            page = doc[entry["page"]]
            rect = fitz.Rect(entry["rect"])
            original_text = entry["text"]
            new_text = new_texts[i]

            # Enforce ±5% length constraint
            new_text = enforce_length_constraint(original_text, new_text, tolerance)

            # Step 1: Redact (erase) the original text area
            # Use white fill to blank the area cleanly
            page.add_redact_annot(rect, fill=(1, 1, 1))

        # Apply all redactions on each page before inserting new text
        for page in doc:
            page.apply_redacts(images=fitz.PDF_REDACT_IMAGE_NONE)

    # Step 2: Re-open to re-get pages (apply_redacts modifies in-place)
    # Re-extract to get updated state — actually we insert AFTER apply_redacts
    # So we reload the document from bytes
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)

    doc2 = fitz.open(stream=buf.read(), filetype="pdf")

    # Re-extract section entries for positioning
    buf.seek(0)
    if isinstance(file_path_or_bytes, bytes):
        sections = extract_pdf_sections(file_path_or_bytes)
    else:
        with open(file_path_or_bytes, "rb") as f:
            sections = extract_pdf_sections(f.read())

    for section_name in ("summary", "experience"):
        entries = sections.get(section_name, [])
        new_texts = rewrites.get(section_name, [])

        for i, entry in enumerate(entries):
            if i >= len(new_texts):
                break

            page = doc2[entry["page"]]
            rect = fitz.Rect(entry["rect"])
            original_text = entry["text"]
            new_text = new_texts[i]

            new_text = enforce_length_constraint(original_text, new_text, tolerance)

            fontname = _map_font(entry.get("fontname", "Helvetica"))
            fontsize = entry.get("fontsize", 11.0)

            # Decode color from integer (0xRRGGBB) to float tuple
            raw_color = entry.get("color", 0)
            r = ((raw_color >> 16) & 0xFF) / 255.0
            g = ((raw_color >> 8) & 0xFF) / 255.0
            b = (raw_color & 0xFF) / 255.0

            # Insert text at the top-left origin of the original span
            origin = fitz.Point(rect.x0, rect.y1)  # baseline = y1 of bounding box
            page.insert_text(
                origin,
                new_text,
                fontname=fontname,
                fontsize=fontsize,
                color=(r, g, b),
            )

    final_buf = io.BytesIO()
    doc2.save(final_buf)
    final_buf.seek(0)
    doc2.close()
    return final_buf.read()


def get_full_pdf_text(file_path_or_bytes) -> str:
    """Returns all text content from a PDF file."""
    if isinstance(file_path_or_bytes, bytes):
        doc = fitz.open(stream=file_path_or_bytes, filetype="pdf")
    else:
        doc = fitz.open(file_path_or_bytes)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text
