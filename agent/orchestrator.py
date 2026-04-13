"""
agent/orchestrator.py — The main agentic loop.
Coordinates: scraping → matching → tailoring → submitting → tracking.
"""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from config import (
    EnvConfig, JobListing, MatchAnalysis, ApplicationRecord,
    DEFAULT_SEARCH_QUERIES, DATA_DIR, JOBS_DIR, LOG_DIR
)
from tools.scraper import scrape_jobs, save_jobs
from tools.submitter import submit_application, log_applications
from tools.notion_tracker import push_to_notion
from agent.brain import analyze_job_match, tailor_application, load_resume, extract_skills_from_jd

console = Console()


class JobApplicationAgent:
    """
    Autonomous job application agent.

    Flow:
    1. Scrape jobs from multiple boards (free, no API key)
    2. Deduplicate against previously seen jobs
    3. Claude analyzes each job for match score
    4. Filter: only apply to jobs above MIN_MATCH_SCORE
    5. Claude writes tailored resume summary + cover letter
    6. Submit (dry run or live via Selenium)
    7. Track in Notion + local JSON log
    """

    def __init__(self, resume_path: str = "data/resumes/resume.txt"):
        self.resume = load_resume(resume_path)
        self.seen_ids: set[str] = self._load_seen_ids()
        self.session_records: List[ApplicationRecord] = []

    def run(self, search_queries: list = None) -> None:
        """Execute the full agent loop."""
        queries = search_queries or DEFAULT_SEARCH_QUERIES

        console.print(
            Panel.fit(
                f"[bold cyan]Autonomous Job Application Agent[/bold cyan]\n"
                f"Mode: {'[yellow]DRY RUN[/yellow]' if EnvConfig.DRY_RUN else '[red]LIVE[/red]'} | "
                f"Min Score: {EnvConfig.MIN_MATCH_SCORE} | "
                f"Max Apps: {EnvConfig.MAX_APPLICATIONS}",
                border_style="cyan",
            )
        )

        # ── Step 1: Scrape ──────────────────────────────────────────────
        all_jobs: List[JobListing] = []
        for q in queries:
            raw = scrape_jobs(
                search_term=q["title"],
                location=q.get("location", "Remote"),
                results_wanted=q.get("results", 20),
            )
            for j in raw:
                if j["id"] not in self.seen_ids:
                    # Extract skills if description present
                    if j.get("description"):
                        j["skills_required"] = extract_skills_from_jd(j["description"])
                    job = JobListing(**j)
                    all_jobs.append(job)

        console.print(f"\n[bold]Found {len(all_jobs)} new jobs across all queries.[/bold]\n")

        if not all_jobs:
            console.print("[yellow]No new jobs to process. Exiting.[/yellow]")
            return

        # Save raw jobs for debugging
        save_jobs(
            [j.model_dump() for j in all_jobs],
            JOBS_DIR / f"jobs_{_ts()}.json",
        )

        # ── Step 2: Match & Filter ──────────────────────────────────────
        console.print("[bold cyan]Analyzing job matches...[/bold cyan]")
        matches: list[tuple[JobListing, MatchAnalysis]] = []

        for job in all_jobs:
            match = analyze_job_match(job, self.resume)
            self.seen_ids.add(job.id)

            if match.match_score >= EnvConfig.MIN_MATCH_SCORE:
                matches.append((job, match))
                status = f"[green]✓ {match.match_score}/100 — {match.recommendation}[/green]"
            else:
                status = f"[dim]✗ {match.match_score}/100 — skipped[/dim]"

            console.print(f"  {job.title} @ {job.company}: {status}")

        self._save_seen_ids()

        console.print(
            f"\n[bold]{len(matches)} jobs passed the {EnvConfig.MIN_MATCH_SCORE}+ threshold.[/bold]\n"
        )

        if not matches:
            console.print("[yellow]No jobs met the match threshold.[/yellow]")
            return

        # Sort by score descending, cap at max applications
        matches.sort(key=lambda x: x[1].match_score, reverse=True)
        matches = matches[: EnvConfig.MAX_APPLICATIONS]

        # ── Step 3: Tailor + Submit ─────────────────────────────────────
        console.print("[bold cyan]Tailoring applications and submitting...[/bold cyan]")

        for job, match in matches:
            console.print(
                f"\n[bold]{job.title}[/bold] @ [bold]{job.company}[/bold] "
                f"(score: [green]{match.match_score}[/green])"
            )

            app = tailor_application(job, self.resume, match)
            record = submit_application(app, job.url, match.match_score)
            self.session_records.append(record)

        # ── Step 4: Track ───────────────────────────────────────────────
        log_path = LOG_DIR / "applications.json"
        log_applications(self.session_records, log_path)
        push_to_notion(self.session_records)

        # ── Step 5: Summary ─────────────────────────────────────────────
        self._print_summary()

    def _print_summary(self) -> None:
        """Print a rich table summary of this session."""
        table = Table(
            title="Session Summary",
            box=box.ROUNDED,
            border_style="cyan",
            show_lines=True,
        )
        table.add_column("Job Title", style="bold", max_width=30)
        table.add_column("Company", max_width=20)
        table.add_column("Score", justify="center")
        table.add_column("Status", justify="center")

        for r in self.session_records:
            score_color = "green" if r.match_score >= 80 else "yellow"
            status_color = "green" if r.status == "applied" else "red"
            table.add_row(
                r.title,
                r.company,
                f"[{score_color}]{r.match_score}[/{score_color}]",
                f"[{status_color}]{r.status}[/{status_color}]",
            )

        console.print("\n")
        console.print(table)

        applied = sum(1 for r in self.session_records if r.status == "applied")
        console.print(
            f"\n[bold green]✓ Done![/bold green] "
            f"Applied to {applied}/{len(self.session_records)} jobs this session.\n"
        )

    # ── Persistence ─────────────────────────────────────────────────────
    def _load_seen_ids(self) -> set[str]:
        path = DATA_DIR / "seen_ids.json"
        if path.exists():
            with open(path) as f:
                return set(json.load(f))
        return set()

    def _save_seen_ids(self) -> None:
        path = DATA_DIR / "seen_ids.json"
        with open(path, "w") as f:
            json.dump(list(self.seen_ids), f)


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
