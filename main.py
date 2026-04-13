"""
main.py — CLI entry point for the Autonomous Job Application Agent.

Usage:
  python main.py                          # run with defaults
  python main.py --title "ML Engineer" --location "Remote" --dry-run
  python main.py --resume path/to/resume.txt --max 5 --min-score 75
"""

import argparse
import sys
from rich.console import Console
from config import EnvConfig

console = Console()


def validate_env() -> bool:
    """Check required environment variables are set."""
    errors = []
    if not EnvConfig.ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY is not set")
    if not EnvConfig.CANDIDATE_NAME:
        errors.append("CANDIDATE_NAME is not set")
    if not EnvConfig.CANDIDATE_EMAIL:
        errors.append("CANDIDATE_EMAIL is not set")

    if errors:
        console.print("[bold red]Configuration errors:[/bold red]")
        for e in errors:
            console.print(f"  [red]✗[/red] {e}")
        console.print("\nCopy [dim].env.example[/dim] → [dim].env[/dim] and fill in your values.")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Job Application Agent — powered by Claude"
    )
    parser.add_argument("--title", type=str, help="Job title to search for")
    parser.add_argument("--location", type=str, default="Remote", help="Job location")
    parser.add_argument("--results", type=int, default=20, help="Results per source")
    parser.add_argument("--resume", type=str, default="data/resumes/resume.txt",
                        help="Path to your resume .txt file")
    parser.add_argument("--max", type=int, help="Max applications this run")
    parser.add_argument("--min-score", type=int, help="Minimum match score (0-100)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Dry run: generate materials but don't submit")
    parser.add_argument("--live", action="store_true",
                        help="Live mode: actually submit applications")
    args = parser.parse_args()

    # Override env config from CLI flags
    if args.max:
        EnvConfig.MAX_APPLICATIONS = args.max
    if args.min_score:
        EnvConfig.MIN_MATCH_SCORE = args.min_score
    if args.dry_run:
        EnvConfig.DRY_RUN = True
    if args.live:
        EnvConfig.DRY_RUN = False

    if not validate_env():
        sys.exit(1)

    # Build search queries
    if args.title:
        queries = [{"title": args.title, "location": args.location, "results": args.results}]
    else:
        from config import DEFAULT_SEARCH_QUERIES
        queries = DEFAULT_SEARCH_QUERIES

    # Run the agent
    from agent.orchestrator import JobApplicationAgent
    agent = JobApplicationAgent(resume_path=args.resume)
    agent.run(search_queries=queries)


if __name__ == "__main__":
    main()
