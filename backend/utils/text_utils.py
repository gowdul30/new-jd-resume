"""
Text utility helpers for the Resume Tailor engine.
"""

def char_count_ratio(original: str, rewritten: str) -> float:
    """Returns the ratio of rewritten length to original length."""
    if len(original) == 0:
        return 1.0
    return len(rewritten) / len(original)


def enforce_length_constraint(
    original: str, rewritten: str, tolerance: float = 0.05
) -> str:
    """
    Ensures rewritten text is within ±tolerance of the original character count.
    If too long: truncate at the last word boundary within the limit.
    If too short: pad with a space (shouldn't normally happen with LLM output).
    """
    max_len = int(len(original) * (1 + tolerance))
    min_len = int(len(original) * (1 - tolerance))

    if len(rewritten) > max_len:
        # Truncate at last word boundary within limit
        truncated = rewritten[:max_len]
        last_space = truncated.rfind(" ")
        if last_space > min_len:
            return truncated[:last_space]
        return truncated

    return rewritten


def clean_text(text: str) -> str:
    """Strips excessive whitespace while preserving single newlines."""
    import re
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
