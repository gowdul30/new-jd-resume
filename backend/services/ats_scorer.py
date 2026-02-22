"""
ATS Scoring Service
Provides keyword-based pre-scoring (without LLM) for fast validation,
and wraps the LLM-based scoring from llm.py.
"""

import re
from collections import Counter
from typing import Optional


def extract_keywords(text: str, top_n: int = 50) -> list[str]:
    """
    Extracts significant keywords from text using simple frequency analysis.
    Filters out stopwords.
    """
    STOPWORDS = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "not", "that", "this",
        "these", "those", "as", "it", "its", "we", "you", "your", "our",
        "their", "they", "he", "she", "i", "me", "us", "him", "her",
        "which", "who", "what", "when", "where", "how", "if", "then",
        "than", "so", "also", "all", "any", "each", "more", "most", "other"
    }

    words = re.findall(r'\b[a-zA-Z][a-zA-Z\+#\.\-]{2,}\b', text.lower())
    filtered = [w for w in words if w not in STOPWORDS]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(top_n)]


def calculate_keyword_overlap(resume_text: str, jd_text: str) -> dict:
    """
    Fast keyword-overlap ATS pre-score (no LLM).
    Useful for quick validation.
    
    Returns:
        {
            "matched": [str],
            "missing": [str],
            "match_rate": float (0.0 - 1.0),
            "quick_score": int (0-100)
        }
    """
    jd_keywords = set(extract_keywords(jd_text, top_n=40))
    resume_words = set(extract_keywords(resume_text, top_n=200))

    matched = list(jd_keywords & resume_words)
    missing = list(jd_keywords - resume_words)

    match_rate = len(matched) / len(jd_keywords) if jd_keywords else 0.0
    quick_score = int(match_rate * 100)

    return {
        "matched": matched,
        "missing": missing,
        "match_rate": round(match_rate, 3),
        "quick_score": quick_score,
    }
