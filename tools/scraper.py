"""
tools/scraper.py — Free job scraping via JobSpy (no API key needed).
Scrapes Indeed, LinkedIn, Glassdoor, and ZipRecruiter.
"""

from __future__ import annotations
import hashlib
import json
from typing import List, Dict, Any
from pathlib import Path
from rich.console import Console

console = Console()


def _make_id(title: str, company: str, url: str) -> str:
    """Create a stable unique ID for a job listing."""
    raw = f"{title}{company}{url}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def scrape_jobs(
    search_term: str,
    location: str = "Remote",
    results_wanted: int = 20,
    site_names: List[str] = None,
) -> List[Dict[str, Any]]:
    """
    Scrape jobs using jobspy (free, no API key).
    Falls back to mock data if jobspy isn't installed.

    Returns a list of raw job dicts.
    """
    if site_names is None:
        site_names = ["indeed", "linkedin", "glassdoor"]

    try:
        from jobspy import scrape_jobs as _scrape

        console.print(
            f"[cyan]Scraping[/cyan] '{search_term}' in '{location}' "
            f"from {', '.join(site_names)}..."
        )
        df = _scrape(
            site_name=site_names,
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=72,
            country_indeed="USA",
        )

        jobs = []
        for _, row in df.iterrows():
            desc = str(row.get("description", "")) or ""
            job = {
                "id": _make_id(
                    str(row.get("title", "")),
                    str(row.get("company", "")),
                    str(row.get("job_url", "")),
                ),
                "title": str(row.get("title", "Unknown")),
                "company": str(row.get("company", "Unknown")),
                "location": str(row.get("location", location)),
                "description": desc[:4000],  # trim for token budget
                "url": str(row.get("job_url", "")),
                "source": str(row.get("site", "unknown")),
                "salary_min": _safe_int(row.get("min_amount")),
                "salary_max": _safe_int(row.get("max_amount")),
                "posted_date": str(row.get("date_posted", "")),
                "job_type": str(row.get("job_type", "")),
            }
            jobs.append(job)

        console.print(f"[green]✓[/green] Found {len(jobs)} jobs.")
        return jobs

    except ImportError:
        console.print(
            "[yellow]⚠ jobspy not installed — using mock data. "
            "Run: pip install python-jobspy[/yellow]"
        )
        return _mock_jobs(search_term, location)

    except Exception as e:
        console.print(f"[red]✗ Scraping error:[/red] {e}")
        return _mock_jobs(search_term, location)


def _safe_int(val: Any) -> int | None:
    try:
        return int(float(val)) if val and str(val) not in ("nan", "None", "") else None
    except (ValueError, TypeError):
        return None


def _mock_jobs(search_term: str, location: str) -> List[Dict[str, Any]]:
    """Return realistic mock jobs for testing without live scraping."""
    return [
        {
            "id": "mock001",
            "title": f"Senior {search_term}",
            "company": "TechCorp Inc.",
            "location": location,
            "description": (
                "We are looking for a Senior Software Engineer to join our platform team. "
                "You will design and build scalable microservices using Python and FastAPI. "
                "Requirements: 4+ years Python, REST APIs, PostgreSQL, Docker, AWS. "
                "Nice to have: Kubernetes, Redis, Kafka. "
                "We offer remote-first work, $130k-$160k, equity, and great benefits."
            ),
            "url": "https://example.com/job/mock001",
            "source": "indeed",
            "salary_min": 130000,
            "salary_max": 160000,
            "posted_date": "2024-01-15",
            "job_type": "fulltime",
        },
        {
            "id": "mock002",
            "title": f"{search_term} — AI/ML Focus",
            "company": "AI Startup Labs",
            "location": location,
            "description": (
                "Join our small but mighty team building the next generation of AI tooling. "
                "We need someone who loves Python, LLMs, and shipping fast. "
                "Stack: Python, LangChain, FastAPI, React, PostgreSQL, GCP. "
                "5+ years experience. Strong ML background preferred. "
                "Salary: $140k-$180k + 0.5% equity."
            ),
            "url": "https://example.com/job/mock002",
            "source": "linkedin",
            "salary_min": 140000,
            "salary_max": 180000,
            "posted_date": "2024-01-14",
            "job_type": "fulltime",
        },
        {
            "id": "mock003",
            "title": f"Junior {search_term}",
            "company": "Enterprise Solutions LLC",
            "location": "New York, NY",
            "description": (
                "Entry-level position for a motivated developer. "
                "You'll work on internal Java Spring Boot applications. "
                "Requirements: Java, Spring, SQL. No remote option. "
                "Salary: $65k-$80k."
            ),
            "url": "https://example.com/job/mock003",
            "source": "glassdoor",
            "salary_min": 65000,
            "salary_max": 80000,
            "posted_date": "2024-01-10",
            "job_type": "fulltime",
        },
    ]


def save_jobs(jobs: List[Dict], output_path: Path) -> None:
    """Save raw scraped jobs to JSON for debugging / re-runs."""
    with open(output_path, "w") as f:
        json.dump(jobs, f, indent=2, default=str)
    console.print(f"[dim]Saved {len(jobs)} raw jobs → {output_path}[/dim]")
