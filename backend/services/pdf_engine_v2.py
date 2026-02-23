"""
PDF Extraction Engine
- Identifies sections and extracts text for analysis
"""

import re
import fitz
from typing import Dict

def find_resume_sections(doc: fitz.Document) -> Dict[str, any]:
    """
    Identifies Summary and Experience sections in the PDF.
    """
    sections = {"summary": [], "experience": []}
    current_section = None
    
    SUMMARY_HEADS = {"summary", "profile", "objective", "about", "overview", "statement", "background", "professional summary", "professional profile", "career objective"}
    EXP_HEADS = {"experience", "history", "employment", "work", "career", "professional experience", "work experience", "professional history", "employment history"}
    STOP_HEADS = {"education", "skills", "certifications", "certs", "projects", "awards", "references", "languages", "links", "interests", "volunteering", "publications", "affiliations", "academic", "training", "hobbies"}

    all_text_parts = []

    for page_num, page in enumerate(doc):
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        
        for block in text_dict["blocks"]:
            if block["type"] != 0: continue
            
            block_lines = []
            for line in block["lines"]:
                spans = line["spans"]
                if not spans: continue
                
                full_line_text = "".join(s["text"] for s in spans).strip()
                if not full_line_text: continue
                
                norm_text = re.sub(r'[^a-z]', ' ', full_line_text.lower()).strip()
                words_list = norm_text.split()
                words_set = set(words_list)
                condensed = norm_text.replace(" ", "")

                # Section detection (Header check)
                is_header = False
                # Stricter header detection: usually headers are short and alone on a line
                if 1 <= len(norm_text) <= 40:
                    found_sum = (words_set & SUMMARY_HEADS) or (condensed in SUMMARY_HEADS)
                    found_exp = (words_set & EXP_HEADS) or (condensed in EXP_HEADS)
                    found_stop = (words_set & STOP_HEADS) or (condensed in STOP_HEADS)

                    if found_sum:
                        # Before switching section, commit collected block lines to OLD section
                        prev_text = " ".join(block_lines).strip()
                        if prev_text and current_section:
                            sections[current_section].append({"text": prev_text})
                        current_section = "summary"
                        is_header = True
                    elif found_exp:
                        prev_text = " ".join(block_lines).strip()
                        if prev_text and current_section:
                            sections[current_section].append({"text": prev_text})
                        current_section = "experience"
                        is_header = True
                    elif found_stop:
                        prev_text = " ".join(block_lines).strip()
                        if prev_text and current_section:
                            sections[current_section].append({"text": prev_text})
                        current_section = None
                        is_header = True
                
                if is_header:
                    block_lines = []
                    continue
                
                block_lines.append(full_line_text)

            # After processing lines in a block, join them and add to section
            full_block_text = " ".join(block_lines).strip()
            if full_block_text:
                if current_section:
                    sections[current_section].append({"text": full_block_text})
                all_text_parts.append(full_block_text)

    sections["all_text"] = "\n".join(all_text_parts)
    return sections
