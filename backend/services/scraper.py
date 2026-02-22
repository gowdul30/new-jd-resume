"""
JD Scraper — extracts job title and description text from a URL.
Falls back gracefully so users can also paste JD text directly.
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import Optional


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Ordered list of CSS selectors per site type
SELECTORS = [
    # LinkedIn
    {"title": "h1.t-24", "body": "div.jobs-description__content"},
    # Indeed
    {"title": "h1.jobsearch-JobInfoHeader-title", "body": "#jobDescriptionText"},
    # Greenhouse
    {"title": "h1.app-title", "body": "div#content"},
    # Lever
    {"title": "h2.posting-headline", "body": "div.posting-description"},
    # Workday
    {"title": "h1[data-automation-id='jobPostingHeader']", "body": "div[data-automation-id='jobPostingDescription']"},
    # Generic fallback
    {"title": "h1", "body": "main"},
]


def scrape_jd(url: str, timeout: int = 10) -> dict:
    """
    Scrapes job title and description from a public job listing URL.

    Returns:
        {
            "title": str,
            "description": str,
            "source": "scraped" | "error",
            "error": Optional[str]
        }
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        return {
            "title": "Unknown",
            "description": "",
            "source": "error",
            "error": f"Failed to fetch URL: {str(e)}",
        }

    soup = BeautifulSoup(resp.text, "html.parser")

    title = ""
    description = ""

    for sel in SELECTORS:
        if not title:
            el = soup.select_one(sel["title"])
            if el:
                title = el.get_text(strip=True)
        if not description:
            el = soup.select_one(sel["body"])
            if el:
                description = el.get_text(separator="\n", strip=True)
        if title and description:
            break

    # Last-resort: grab all visible text from body
    if not description:
        body = soup.find("body")
        if body:
            description = body.get_text(separator="\n", strip=True)

    if not title:
        title = soup.title.string if soup.title else "Job Posting"

    # Clean up whitespace
    description = re.sub(r"\n{3,}", "\n\n", description).strip()

    return {
        "title": title,
        "description": description,
        "source": "scraped",
        "error": None,
    }


def parse_manual_jd(text: str) -> dict:
    """
    Wraps manually pasted JD text into the standard dict format.
    Tries to extract the first line as title.
    """
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    title = lines[0] if lines else "Job Posting"
    description = "\n".join(lines)
    return {
        "title": title,
        "description": description,
        "source": "manual",
        "error": None,
    }
