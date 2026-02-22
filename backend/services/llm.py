"""
Groq LLM Integration (llama-3.3-70b-versatile)
- Generates ATS match scores
- Provides suggestions for improvement
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
Your job is to analyze a resume against a job description and provide specific suggestions for improvement.

STRICT RULES — NEVER VIOLATE:
1. COMPARATIVE OUTPUT: For each suggestion, provide the "original" text and a "suggested" version that incorporates JD keywords.
2. MISSING SKILLS: Identify specifically which hard skills and technologies from the JD are missing from the resume.
3. ANTI-HALLUCINATION: Do NOT add any new employers, job titles, or companies.
4. NATURAL TONE: The suggested text must sound human-written.
5. OUTPUT FORMAT: Return ONLY valid JSON. No explanation, no markdown. 
   The JSON must have this structure:
   {
     "missing_skills": ["Skill 1", "Skill 2"],
     "summary_suggestions": [{"original": "...", "suggested": "..."}],
     "experience_suggestions": [{"original": "...", "suggested": "..."}]
   }"""

SCORING_SYSTEM_PROMPT = """You are an ATS (Applicant Tracking System) expert evaluator and optimization strategist.
Your goal is to provide a realistic current score but a HIGHLY AGGRESSIVE prospective score.
Assume that if the user incorporates all suggested surgical rewrites and keywords, they will achieve near-perfect alignment (95-100).
Return ONLY valid JSON, no explanation or markdown."""

def rewrite_sections(resume_sections: dict, jd_text: str) -> dict:
    """
    Uses Groq to generate display suggestions for Summary and Experience sections.
    """
    client = get_client()

    summary_texts = [e["text"] for e in resume_sections.get("summary", [])]
    experience_texts = [e["text"] for e in resume_sections.get("experience", [])]

    if not summary_texts and not experience_texts:
        return {"missing_skills": [], "summary_suggestions": [], "experience_suggestions": []}

    user_prompt = f"""
RESUME SECTIONS:

--- SUMMARY ---
{json.dumps(summary_texts, indent=2)}

--- EXPERIENCE ---
{json.dumps(experience_texts, indent=2)}

--- JOB DESCRIPTION ---
{jd_text[:4000]}

TASK: 
1. Identify missing skills from the JD.
2. Suggest rewrites for the summary and experience blocks to weave in missing keywords.
Return ONLY JSON.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
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
            result = {"missing_skills": [], "summary_suggestions": [], "experience_suggestions": []}

    return result

def score_resume(resume_text: str, jd_text: str) -> dict:
    """
    Scores a resume against the JD using Groq.
    """
    client = get_client()

    user_prompt = f"""
Score this resume against the job description below.

--- RESUME TEXT ---
{resume_text[:3000]}

--- JOB DESCRIPTION ---
{jd_text[:2000]}

SCORING LOGIC:
1. Current Score: Be honest and critical about the existing resume. 
2. Prospective Score: Be AGGRESSIVE. If the user follows our expert optimization strategy (weaving in all missing hard skills and fixing impact statements), estimate a score in the 95-100 range. This represents the 'Unlocked Potential' of the profile.

Return ONLY a JSON object with this exact structure:
{{
  "keyword_match": <integer 0-40>,
  "role_relevancy": <integer 0-40>,
  "formatting_simplicity": <integer 0-20>,
  "total": <sum of above three, 0-100>,
  "prospective_score": <aggressive estimate 95-100 assuming optimizations are applied>,
  "feedback": "<2-3 sentence summary of strengths and areas to improve>",
  "top_matched_keywords": ["keyword1", "keyword2", "keyword3"],
  "missing_keywords": ["keyword1", "keyword2", "keyword3"]
}}
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
                "feedback": "Scoring failed.",
                "top_matched_keywords": [],
                "missing_keywords": [],
            }

    result["total"] = min(100, max(0, int(result.get("total", 0))))
    result["prospective_score"] = min(100, max(0, int(result.get("prospective_score", result["total"]))))
    return result
