"""
Groq LLM Integration (llama-3.3-70b-versatile)
- Rewrites Resume Summary and Experience sections to align with JD
- Generates ATS match scores

Guardrails:
  1. Anti-hallucination: No new jobs, certs, skills, or years added
  2. Natural tone: No keyword stuffing
  3. Length: ±5% of original character count per block
"""

import json
import os
import re
from typing import Optional
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client: Optional[Groq] = None


def get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set in environment / .env file")
        _client = Groq(api_key=api_key)
    return _client


REWRITE_SYSTEM_PROMPT = """You are a professional resume writer and ATS optimization expert.
Your job is to rewrite specific sections of a resume to better align with a job description.

STRICT RULES — NEVER VIOLATE:
1. ANTI-HALLUCINATION: Do NOT add any new employers, job titles, companies, certifications, 
   degrees, years of experience, or skills that are not already in the original text.
   You may only REPHRASE existing content to emphasize keywords from the JD.
2. NATURAL TONE: The rewritten text must sound human-written and professional.
   Do NOT stuff keywords unnaturally. Read like a real person wrote it.
3. LENGTH CONSTRAINT: Each rewritten block must be within ±5% of the original character count.
   Do not write significantly shorter or longer text.
4. PRESERVE STRUCTURE: Keep the same number of bullet points, sentences, and paragraphs 
   as the original.
5. OUTPUT FORMAT: Return ONLY valid JSON. No explanation, no markdown. 
   The JSON must have two keys: "summary" and "experience", each containing 
   an array of strings (one per original text block in the input)."""

SCORING_SYSTEM_PROMPT = """You are an ATS (Applicant Tracking System) expert evaluator.
Score a resume against a job description on three dimensions.
Return ONLY valid JSON, no explanation or markdown."""


def rewrite_sections(resume_sections: dict, jd_text: str) -> dict:
    """
    Uses Groq to rewrite Summary and Experience sections of the resume.

    Args:
        resume_sections: Output from extract_docx_sections or extract_pdf_sections
                         with keys "summary" and "experience" as lists of entry dicts
        jd_text: Full job description text

    Returns:
        {
            "summary": ["rewritten text 1", "rewritten text 2", ...],
            "experience": ["rewritten text 1", ...]
        }
    """
    client = get_client()

    # Build compact text lists for the prompt
    summary_texts = [e["text"] for e in resume_sections.get("summary", [])]
    experience_texts = [e["text"] for e in resume_sections.get("experience", [])]

    if not summary_texts and not experience_texts:
        return {"summary": [], "experience": []}

    user_prompt = f"""
RESUME SECTIONS TO REWRITE:

--- SUMMARY BLOCKS (one per array element) ---
{json.dumps(summary_texts, indent=2)}

--- EXPERIENCE BLOCKS (one per array element) ---
{json.dumps(experience_texts, indent=2)}

--- JOB DESCRIPTION ---
{jd_text[:4000]}

TASK: Rewrite the summary and experience blocks to emphasize keywords and responsibilities 
from the job description, following ALL rules in your system prompt.

Remember: Return ONLY a JSON object with keys "summary" and "experience", 
each an array of strings matching the length of the input arrays.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=4096,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Attempt to extract JSON object from mixed response
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            result = json.loads(match.group())
        else:
            # Fallback: return originals unchanged
            result = {"summary": summary_texts, "experience": experience_texts}

    # Ensure arrays are same length as inputs (pad with originals if needed)
    for key, originals in [("summary", summary_texts), ("experience", experience_texts)]:
        if key not in result or not isinstance(result[key], list):
            result[key] = originals
        while len(result[key]) < len(originals):
            result[key].append(originals[len(result[key])])

    return result


def score_resume(optimized_text: str, jd_text: str) -> dict:
    """
    Scores an optimized resume against the JD using Groq.

    Returns:
        {
            "total": int (0-100),
            "keyword_match": int (0-40),
            "role_relevancy": int (0-40),
            "formatting_simplicity": int (0-20),
            "feedback": str,
            "top_matched_keywords": [str],
            "missing_keywords": [str]
        }
    """
    client = get_client()

    user_prompt = f"""
Score this resume against the job description below.

--- RESUME TEXT ---
{optimized_text[:3000]}

--- JOB DESCRIPTION ---
{jd_text[:2000]}

Return ONLY a JSON object with this exact structure:
{{
  "keyword_match": <integer 0-40>,
  "role_relevancy": <integer 0-40>,
  "formatting_simplicity": <integer 0-20>,
  "total": <sum of above three, 0-100>,
  "feedback": "<2-3 sentence summary of strengths and areas to improve>",
  "top_matched_keywords": ["keyword1", "keyword2", "keyword3"],
  "missing_keywords": ["keyword1", "keyword2", "keyword3"]
}}

Scoring criteria:
- keyword_match (0-40): How many important JD keywords appear naturally in the resume
- role_relevancy (0-40): Semantic alignment between resume experience and JD responsibilities
- formatting_simplicity (0-20): Penalize tables, columns, graphics. Reward clean single-column text.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SCORING_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            result = json.loads(match.group())
        else:
            result = {
                "total": 0,
                "keyword_match": 0,
                "role_relevancy": 0,
                "formatting_simplicity": 0,
                "feedback": "Scoring failed. Please try again.",
                "top_matched_keywords": [],
                "missing_keywords": [],
            }

    # Ensure total is correctly computed
    result["total"] = min(100, max(0, int(result.get("total", 0))))
    return result
