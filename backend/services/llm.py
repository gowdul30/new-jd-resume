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

REWRITE_SYSTEM_PROMPT = """You are an elite ATS Optimization Architect and Expert Resume Strategist.
Your goal is to transform a standard resume into a high-performance, ATS-dominant document that guarantees a 95+ match score.

STRICT AGGRESSIVE RULES — NEVER VIOLATE:
1. TOTAL SURGICAL SWEEP: You must evaluate and aggressively optimize EVERY experience block across the ENTIRE resume provided. No section or page is to be ignored.
2. STRICT EXPERIENCE FOCUS: Focus EXCLUSIVELY on "experience_suggestions". Do NOT provide summary optimizations.
3. ATS KEYWORD SATURATION: Suture the most critical technical and soft skills from the JD directly into the experience bullet points. Do not just "add" them; weave them into high-impact value statements.
4. QUANTITATIVE DOMINANCE (KPIs): Force the inclusion of measurable results (e.g., "Increased X by 25%", "Reduced latency by 400ms", "Managed $2M budget"). If numbers aren't present in the original, infer high-impact context where possible without fabricating employers.
5. AGGRESSIVE REPHRASING: Replace passive language with powerful action verbs. Ensure every bullet point starts with a strong verb and follows the Google XYZ formula: "Accomplished [X] as measured by [Y], by doing [Z]".
6. COMPARATIVE OUTPUT: For each chunk, provide the "original" text and the "suggested" high-performance version.
7. ANTI-HALLUCINATION: Stay within the bounds of the user's actual career history (Companies/Dates/Titles).
8. OUTPUT FORMAT: Return ONLY valid JSON. 
   {
     "existing_skills": ["Skill A", "Skill B"],
     "missing_skills": ["Skill X", "Skill Y"],
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
ACTION: PERFORM AGGRESSIVE SURGICAL OPTIMIZATION

I am providing you with the full content of a resume experience section and a target job description.

--- TARGET JOB DESCRIPTION ---
{jd_text[:4000]}

--- RESUME EXPERIENCE SECTIONS ---
{json.dumps(experience_texts, indent=2)}

TASK REQUIREMENTS:
1. Audit the experience blocks against the JD. Identify every single opportunity where technical keywords can be injected.
2. Rewrite each block using the "Google XYZ" formula or high-impact "Situation-Task-Action-Result" (STAR) method.
3. Ensure every suggestion is a MAJOR upgrade over the original in terms of ATS readability and keyword density.
4. Identify the top 'existing_skills' and the critical 'missing_skills' required for the candidate to be a top-tier match.

Return ONLY the completed JSON analysis.
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
            result = {"missing_skills": [], "experience_suggestions": []}

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
