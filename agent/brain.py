"""
agent/brain.py — The Claude-powered reasoning core.
Handles: job matching, resume tailoring, cover letter writing.
"""

from __future__ import annotations
import json
from typing import Optional
import anthropic
from rich.console import Console
from config import EnvConfig, JobListing, MatchAnalysis, TailoredApplication

console = Console()
_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=EnvConfig.ANTHROPIC_API_KEY)
    return _client


# ── Resume loader ──────────────────────────────────────────────────────
def load_resume(resume_path: str) -> str:
    """Load plain-text resume from file."""
    try:
        with open(resume_path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return _sample_resume()


def _sample_resume() -> str:
    return f"""
{EnvConfig.CANDIDATE_NAME}
{EnvConfig.CANDIDATE_EMAIL} | {EnvConfig.CANDIDATE_PHONE}
{EnvConfig.CANDIDATE_LINKEDIN} | {EnvConfig.CANDIDATE_GITHUB}

SUMMARY
Experienced Software Engineer with 5+ years building scalable backend systems and APIs.
Passionate about Python, distributed systems, and clean architecture.

SKILLS
Languages: Python, JavaScript, TypeScript, SQL, Bash
Frameworks: FastAPI, Django, React, Node.js, LangChain
Infrastructure: AWS, Docker, Kubernetes, PostgreSQL, Redis, Kafka
AI/ML: OpenAI API, Anthropic Claude, LangChain, Vector DBs

EXPERIENCE
Senior Backend Engineer — StartupXYZ (2021–Present)
- Built microservices handling 10M+ daily requests using Python/FastAPI
- Reduced API latency by 40% through Redis caching and query optimization
- Led migration from monolith to microservices architecture
- Mentored 3 junior engineers

Software Engineer — MediumCo (2019–2021)
- Developed REST APIs for mobile app serving 500k users
- Implemented CI/CD pipeline with GitHub Actions + Docker
- Built data pipelines using Airflow and PostgreSQL

EDUCATION
B.S. Computer Science — State University, 2019

PROJECTS
- AI Job Agent: Autonomous agent that applies to jobs using LLMs
- OpenSource CLI Tool: 1.2k GitHub stars
""".strip()


# ── Core AI Functions ──────────────────────────────────────────────────

def analyze_job_match(job: JobListing, resume: str) -> MatchAnalysis:
    """
    Use Claude to analyze how well the candidate matches a job.
    Returns a structured MatchAnalysis with a 0-100 score.
    """
    console.print(f"  [dim]Analyzing match: {job.title} @ {job.company}...[/dim]")

    prompt = f"""You are an expert technical recruiter. Analyze how well this candidate matches the job.

CANDIDATE RESUME:
{resume}

JOB POSTING:
Title: {job.title}
Company: {job.company}
Location: {job.location}
Description:
{job.description}

Respond ONLY with a JSON object (no markdown, no explanation):
{{
  "job_id": "{job.id}",
  "match_score": <integer 0-100>,
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1", "skill2"],
  "strengths": ["strength1", "strength2"],
  "concerns": ["concern1"],
  "recommendation": "apply" | "strong_apply" | "skip",
  "reasoning": "2-3 sentence summary of the match"
}}

Scoring guide: 90-100 = perfect fit, 70-89 = good fit apply, 50-69 = stretch, <50 = skip."""

    try:
        resp = get_client().messages.create(
            model="claude-opus-4-5",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        # strip accidental markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return MatchAnalysis(**data)
    except Exception as e:
        console.print(f"  [red]Match analysis failed:[/red] {e}")
        return MatchAnalysis(
            job_id=job.id,
            match_score=0,
            matched_skills=[],
            missing_skills=[],
            strengths=[],
            concerns=["Analysis failed"],
            recommendation="skip",
            reasoning=str(e),
        )


def tailor_application(
    job: JobListing, resume: str, match: MatchAnalysis
) -> TailoredApplication:
    """
    Use Claude to write a tailored resume summary + cover letter for a specific job.
    """
    console.print(f"  [dim]Writing application for {job.title} @ {job.company}...[/dim]")

    prompt = f"""You are an expert career coach. Write a tailored job application for this candidate.

CANDIDATE RESUME:
{resume}

JOB:
Title: {job.title}
Company: {job.company}
Description: {job.description[:2000]}

MATCH ANALYSIS:
Score: {match.match_score}/100
Matched Skills: {', '.join(match.matched_skills)}
Strengths: {', '.join(match.strengths)}

Write a professional, specific, non-generic application. Mirror keywords from the job description.

Respond ONLY with JSON (no markdown):
{{
  "job_id": "{job.id}",
  "company": "{job.company}",
  "title": "{job.title}",
  "tailored_resume_summary": "3-4 sentence professional summary tailored to this exact role",
  "cover_letter": "Full cover letter, 3 paragraphs, professional, specific to this company and role",
  "key_talking_points": ["point1", "point2", "point3"],
  "subject_line": "Email subject line for this application"
}}"""

    try:
        resp = get_client().messages.create(
            model="claude-opus-4-5",
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        return TailoredApplication(**data)
    except Exception as e:
        console.print(f"  [red]Tailoring failed:[/red] {e}")
        return TailoredApplication(
            job_id=job.id,
            company=job.company,
            title=job.title,
            tailored_resume_summary="",
            cover_letter="",
            key_talking_points=[],
            subject_line=f"Application for {job.title}",
        )


def extract_skills_from_jd(description: str) -> list[str]:
    """Quick skill extraction from a job description using Claude."""
    prompt = f"""Extract the technical skills and tools mentioned in this job description.
Return ONLY a JSON array of strings. No markdown.

Job Description:
{description[:1500]}"""

    try:
        resp = get_client().messages.create(
            model="claude-haiku-4-5-20251001",  # Use fast/cheap model for this
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip().replace("```json", "").replace("```", "")
        return json.loads(raw)
    except Exception:
        return []
