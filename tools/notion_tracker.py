"""
tools/notion_tracker.py — Push application records to Notion database.
Completely optional — agent works without it.

Setup:
1. Create a free Notion integration at https://www.notion.so/my-integrations
2. Create a database with columns: Title, Company, Status, Score, URL, Applied At, Notes
3. Add NOTION_TOKEN and NOTION_DATABASE_ID to .env
"""

from __future__ import annotations
from typing import List
import requests
from rich.console import Console
from config import EnvConfig, ApplicationRecord

console = Console()

NOTION_API = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {EnvConfig.NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def is_configured() -> bool:
    return bool(EnvConfig.NOTION_TOKEN and EnvConfig.NOTION_DATABASE_ID)


def push_to_notion(records: List[ApplicationRecord]) -> None:
    """Push all application records to Notion database."""
    if not is_configured():
        console.print("[dim]Notion not configured — skipping tracker sync.[/dim]")
        return

    console.print(f"[cyan]Syncing {len(records)} records to Notion...[/cyan]")
    success = 0
    for record in records:
        if _create_page(record):
            success += 1

    console.print(f"[green]✓ Notion sync: {success}/{len(records)} records added.[/green]")


def _create_page(record: ApplicationRecord) -> bool:
    """Create a single page in the Notion database."""
    payload = {
        "parent": {"database_id": EnvConfig.NOTION_DATABASE_ID},
        "properties": {
            "Title": {
                "title": [{"text": {"content": f"{record.title} @ {record.company}"}}]
            },
            "Company": {"rich_text": [{"text": {"content": record.company}}]},
            "Status": {"select": {"name": _status_label(record.status)}},
            "Score": {"number": record.match_score},
            "URL": {"url": record.url},
            "Applied At": {
                "rich_text": [
                    {"text": {"content": record.applied_at or "—"}}
                ]
            },
            "Notes": {
                "rich_text": [{"text": {"content": record.notes or ""}}]
            },
        },
    }

    try:
        resp = requests.post(
            f"{NOTION_API}/pages",
            headers=HEADERS,
            json=payload,
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        else:
            console.print(f"  [red]Notion error {resp.status_code}:[/red] {resp.text[:200]}")
            return False
    except Exception as e:
        console.print(f"  [red]Notion request failed:[/red] {e}")
        return False


def _status_label(status: str) -> str:
    mapping = {
        "applied": "Applied",
        "pending": "Pending",
        "failed": "Failed",
        "skipped": "Skipped",
    }
    return mapping.get(status, "Pending")
