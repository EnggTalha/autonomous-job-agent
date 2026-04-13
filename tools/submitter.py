"""
tools/submitter.py — Handles job application submission.
In DRY_RUN mode: just logs what it would do.
In live mode: uses Selenium to submit Easy Apply forms.
"""

from __future__ import annotations
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from rich.console import Console
from config import EnvConfig, TailoredApplication, ApplicationRecord, APPS_DIR

console = Console()


def submit_application(
    app: TailoredApplication,
    job_url: str,
    match_score: int,
) -> ApplicationRecord:
    """
    Submit a job application.
    DRY_RUN=true → saves to disk and prints.
    DRY_RUN=false → attempts Selenium form submission.
    """
    record = ApplicationRecord(
        job_id=app.job_id,
        title=app.title,
        company=app.company,
        url=job_url,
        status="pending",
        match_score=match_score,
    )

    if EnvConfig.DRY_RUN:
        return _dry_run_submit(app, record)
    else:
        return _live_submit(app, record, job_url)


def _dry_run_submit(app: TailoredApplication, record: ApplicationRecord) -> ApplicationRecord:
    """Save application materials to disk without submitting."""
    out_dir = APPS_DIR / app.job_id
    out_dir.mkdir(exist_ok=True)

    # Save cover letter
    with open(out_dir / "cover_letter.txt", "w") as f:
        f.write(f"Subject: {app.subject_line}\n\n")
        f.write(app.cover_letter)

    # Save tailored summary
    with open(out_dir / "resume_summary.txt", "w") as f:
        f.write(app.tailored_resume_summary)

    # Save talking points
    with open(out_dir / "talking_points.json", "w") as f:
        json.dump(app.key_talking_points, f, indent=2)

    record.status = "applied"
    record.applied_at = datetime.now().isoformat()
    record.notes = f"[DRY RUN] Materials saved to {out_dir}"

    console.print(
        f"  [green]✓ [DRY RUN][/green] Application saved → [dim]{out_dir}[/dim]"
    )
    return record


def _live_submit(
    app: TailoredApplication, record: ApplicationRecord, job_url: str
) -> ApplicationRecord:
    """
    Attempt live submission via Selenium.
    Currently handles LinkedIn Easy Apply.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service

        console.print(f"  [yellow]Attempting live submit for {app.title} @ {app.company}[/yellow]")

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=options
        )

        try:
            driver.get(job_url)
            time.sleep(2)

            # LinkedIn Easy Apply detection
            if "linkedin.com" in job_url:
                result = _handle_linkedin_easy_apply(driver, app)
            else:
                result = "unsupported_platform"

            if result == "success":
                record.status = "applied"
                record.applied_at = datetime.now().isoformat()
                console.print(f"  [green]✓ Applied successfully![/green]")
            else:
                record.status = "failed"
                record.notes = f"Submit result: {result}"
                console.print(f"  [red]✗ Could not submit: {result}[/red]")

        finally:
            driver.quit()

    except ImportError:
        console.print("  [yellow]Selenium not available — falling back to dry run[/yellow]")
        return _dry_run_submit(app, record)
    except Exception as e:
        record.status = "failed"
        record.notes = str(e)
        console.print(f"  [red]✗ Submission error:[/red] {e}")

    return record


def _handle_linkedin_easy_apply(driver, app: TailoredApplication) -> str:
    """Handle LinkedIn Easy Apply flow."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        wait = WebDriverWait(driver, 10)

        # Click Easy Apply button
        easy_apply_btn = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, ".jobs-apply-button--top-card button")
            )
        )
        easy_apply_btn.click()
        time.sleep(1.5)

        # Fill phone if prompted
        phone_fields = driver.find_elements(By.CSS_SELECTOR, "input[id*='phoneNumber']")
        for field in phone_fields:
            field.clear()
            field.send_keys(EnvConfig.CANDIDATE_PHONE)

        # Handle multi-page forms — click Next up to 5 times
        for _ in range(5):
            next_btns = driver.find_elements(
                By.CSS_SELECTOR,
                "button[aria-label='Continue to next step'], button[aria-label='Submit application']",
            )
            if not next_btns:
                break

            btn = next_btns[0]
            label = btn.get_attribute("aria-label") or ""

            if "Submit" in label:
                btn.click()
                return "success"
            else:
                btn.click()
                time.sleep(1)

        return "form_navigation_failed"

    except Exception as e:
        return f"error: {e}"


def log_applications(records: list[ApplicationRecord], output_path: Path) -> None:
    """Append application records to a master log JSON."""
    existing = []
    if output_path.exists():
        with open(output_path) as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    all_records = existing + [r.model_dump() for r in records]
    with open(output_path, "w") as f:
        json.dump(all_records, f, indent=2, default=str)
    console.print(f"[dim]Application log → {output_path}[/dim]")
