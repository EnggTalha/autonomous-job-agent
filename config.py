"""
config.py — Central configuration and Pydantic models for the Job Agent.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RESUME_DIR = DATA_DIR / "resumes"
JOBS_DIR = DATA_DIR / "jobs"
APPS_DIR = DATA_DIR / "applications"
LOG_DIR = BASE_DIR / "logs"

for d in [RESUME_DIR, JOBS_DIR, APPS_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ── Environment ────────────────────────────────────────────────────────
class EnvConfig:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    NOTION_TOKEN: str = os.getenv("NOTION_TOKEN", "")
    NOTION_DATABASE_ID: str = os.getenv("NOTION_DATABASE_ID", "")
    MAX_APPLICATIONS: int = int(os.getenv("MAX_APPLICATIONS_PER_RUN", "10"))
    MIN_MATCH_SCORE: int = int(os.getenv("MIN_MATCH_SCORE", "70"))
    DRY_RUN: bool = os.getenv("DRY_RUN", "true").lower() == "true"
    CANDIDATE_NAME: str = os.getenv("CANDIDATE_NAME", "")
    CANDIDATE_EMAIL: str = os.getenv("CANDIDATE_EMAIL", "")
    CANDIDATE_PHONE: str = os.getenv("CANDIDATE_PHONE", "")
    CANDIDATE_LOCATION: str = os.getenv("CANDIDATE_LOCATION", "")
    CANDIDATE_LINKEDIN: str = os.getenv("CANDIDATE_LINKEDIN", "")
    CANDIDATE_GITHUB: str = os.getenv("CANDIDATE_GITHUB", "")


# ── Data Models ────────────────────────────────────────────────────────
class JobListing(BaseModel):
    id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str  # "indeed" | "linkedin" | "glassdoor"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    posted_date: Optional[str] = None
    job_type: Optional[str] = None  # "full-time" | "remote" | etc.
    skills_required: List[str] = Field(default_factory=list)


class MatchAnalysis(BaseModel):
    job_id: str
    match_score: int  # 0–100
    matched_skills: List[str]
    missing_skills: List[str]
    strengths: List[str]
    concerns: List[str]
    recommendation: str  # "apply" | "skip" | "strong_apply"
    reasoning: str


class TailoredApplication(BaseModel):
    job_id: str
    company: str
    title: str
    tailored_resume_summary: str
    cover_letter: str
    key_talking_points: List[str]
    subject_line: str  # for email applications


class ApplicationRecord(BaseModel):
    job_id: str
    title: str
    company: str
    url: str
    status: str  # "pending" | "applied" | "failed" | "skipped"
    match_score: int
    applied_at: Optional[str] = None
    notes: Optional[str] = None


# ── Search Config ──────────────────────────────────────────────────────
DEFAULT_SEARCH_QUERIES = [
    {"title": "Software Engineer", "location": "Remote", "results": 20},
    {"title": "Python Developer", "location": "Remote", "results": 20},
    {"title": "Full Stack Engineer", "location": "Remote", "results": 15},
]
