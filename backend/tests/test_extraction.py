
import sys
import os
import re

# Add backend to path so we can import services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.pdf_engine_v2 import find_resume_sections

class MockPage:
    def __init__(self, blocks):
        self._blocks = blocks
    
    def get_text(self, mode, flags=None):
        if mode == "dict":
            return {"blocks": self._blocks}
        return ""

class MockDoc:
    def __init__(self, pages):
        self._pages = pages
    
    def __iter__(self):
        return iter(self._pages)

def test_template(name, pages_data):
    print(f"\n--- Testing Template: {name} ---")
    mock_pages = []
    for page_blocks in pages_data:
        blocks = []
        for block_text in page_blocks:
            lines = []
            for line_text in block_text.split('\n'):
                lines.append({"spans": [{"text": line_text}]})
            blocks.append({"type": 0, "lines": lines})
        mock_pages.append(MockPage(blocks))
    
    mock_doc = MockDoc(mock_pages)
    sections = find_resume_sections(mock_doc)
    
    summary_count = len(sections['summary'])
    experience_count = len(sections['experience'])
    
    print(f"Summary Blocks: {summary_count}")
    print(f"Experience Blocks: {experience_count}")
    
    if summary_count > 0:
        print(f"First Summary: {sections['summary'][0]['text'][:100]}...")
    if experience_count > 0:
        print(f"First Experience: {sections['experience'][0]['text'][:100]}...")
    
    return sections

# Scenario 1: Traditional Simple Layout
traditional_pages = [
    [
        "John Doe\nSoftware Engineer",
        "SUMMARY",
        "Experienced engineer with 5 years in Python and AWS. Specialized in building scalable backends.",
        "EXPERIENCE",
        "Lead Developer at TechCorp\nBuilt a high-performance API using FastAPI."
    ]
]

# Scenario 2: Multi-page with Header at End of Page
multipage_pages = [
    [
        "Professional Summary",
        "Experienced cloud architect.",
        "WORK EXPERIENCE" # Header at bottom
    ],
    [
        "Senior Engineer at Cloudly\nManaged 100+ microservices.",
        "Junior Dev at Startup\nLearned the ropes of JS."
    ]
]

# Scenario 3: Mixed Headers (Simulating Sidebar or different naming)
sidebar_pages = [
    [
        "Contact\ntest@test.com",
        "Professional Profile", # Summary-like
        "I love coding.",
        "Employment History", # Experience-like
        "Dev at Google",
        "Education", # STOP header
        "BS Computer Science"
    ]
]

test_template("Traditional", traditional_pages)
test_template("Multi-page", multipage_pages)
test_template("Sidebar/Mixed", sidebar_pages)
