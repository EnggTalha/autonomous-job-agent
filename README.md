# 🤖 Autonomous Job Application Agent

> An agentic AI system that scrapes job boards, scores your fit using Claude, writes tailored cover letters, and submits applications — all autonomously.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Claude](https://img.shields.io/badge/Powered%20by-Claude%20Opus-blueviolet?logo=anthropic)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

## 📸 Demo

```
╭──────────────────────────────────────────────────────────╮
│  Autonomous Job Application Agent                        │
│  Mode: DRY RUN | Min Score: 70 | Max Apps: 10           │
╰──────────────────────────────────────────────────────────╯

Scraping 'Python Developer' in 'Remote' from indeed, linkedin...
✓ Found 23 jobs.

Analyzing job matches...
  Senior Python Engineer @ TechCorp:     ✓ 91/100 — strong_apply
  ML Engineer @ AI Startup Labs:         ✓ 84/100 — apply
  Java Developer @ Enterprise LLC:       ✗ 42/100 — skipped

2 jobs passed the 70+ threshold.

Tailoring applications and submitting...

Senior Python Engineer @ TechCorp (score: 91)
  Writing application for Senior Python Engineer @ TechCorp...
  ✓ [DRY RUN] Materials saved → data/applications/mock001/

┌─────────────────────────────────────────────────────────────┐
│                      Session Summary                        │
├──────────────────────┬──────────────┬───────┬──────────────┤
│ Job Title            │ Company      │ Score │ Status       │
├──────────────────────┼──────────────┼───────┼──────────────┤
│ Senior Python Eng.   │ TechCorp     │  91   │ applied      │
│ ML Engineer          │ AI Startup   │  84   │ applied      │
└──────────────────────┴──────────────┴───────┴──────────────┘

✓ Done! Applied to 2/2 jobs this session.
```

---

## 🧠 How It Works

This agent follows a multi-step agentic loop:

```
┌─────────────┐    ┌──────────────┐    ┌──────────────────┐
│  1. SCRAPE  │───▶│  2. ANALYZE  │───▶│  3. FILTER       │
│             │    │              │    │                  │
│  Indeed     │    │  Claude reads│    │  Score ≥ 70?     │
│  LinkedIn   │    │  your resume │    │  Yes → proceed   │
│  Glassdoor  │    │  vs JD       │    │  No  → skip      │
│  (free)     │    │  Score 0-100 │    │                  │
└─────────────┘    └──────────────┘    └──────────────────┘
                                                │
                                                ▼
┌─────────────┐    ┌──────────────┐    ┌──────────────────┐
│  6. TRACK   │◀───│  5. SUBMIT   │◀───│  4. TAILOR       │
│             │    │              │    │                  │
│  Notion DB  │    │  Selenium    │    │  Claude writes   │
│  Local JSON │    │  form fill   │    │  cover letter    │
│  (free)     │    │  (or dry run)│    │  + resume summary│
└─────────────┘    └──────────────┘    └──────────────────┘
```

### Agent Decisions
- **Match Score < 70** → skipped automatically (no wasted API calls on tailoring)
- **Score 70–85** → applies with standard tailoring
- **Score 85+** → `strong_apply` flag, gets extra emphasis in cover letter
- **Already seen job IDs** → deduplicated across runs via `data/seen_ids.json`

---

## ✨ Features

| Feature | Details |
|---|---|
| 🔍 Multi-board scraping | Indeed, LinkedIn, Glassdoor, ZipRecruiter — **no API keys needed** |
| 🧠 AI match scoring | Claude analyzes resume vs JD, returns 0-100 score with reasoning |
| ✍️ Tailored cover letters | Per-job cover letters that mirror keywords and company tone |
| 📄 Resume summary rewrite | Tailored 4-sentence summary for each role |
| 🤖 Auto-submit | Selenium handles LinkedIn Easy Apply forms |
| 📊 Notion tracker | Auto-syncs application status to a Notion database |
| 💾 Full local logs | Every application saved to `data/applications/` |
| 🔁 Deduplication | Never applies to the same job twice |
| 🧪 Dry-run mode | Generate all materials without submitting — safe to test |

---

## 🗂️ Project Structure

```
job-agent/
├── main.py                   # CLI entry point
├── config.py                 # Config, env vars, Pydantic models
├── requirements.txt
├── .env.example
│
├── agent/
│   ├── brain.py              # Claude: job matching + cover letter writing
│   └── orchestrator.py       # Main agentic loop (coordinates all tools)
│
├── tools/
│   ├── scraper.py            # Free job scraping via JobSpy
│   ├── submitter.py          # Selenium form submission + dry-run
│   └── notion_tracker.py     # Optional Notion database sync
│
└── data/
    ├── resumes/
    │   └── resume.txt        # Your resume in plain text
    ├── jobs/                 # Raw scraped job JSON (auto-generated)
    ├── applications/         # Per-job cover letters + summaries
    └── seen_ids.json         # Dedup tracker (auto-generated)
```

---

## 🚀 Quickstart

### 1. Clone & install

```bash
git clone https://github.com/yourusername/autonomous-job-agent.git
cd autonomous-job-agent

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
pip install python-jobspy          # free job scraping
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `ANTHROPIC_API_KEY` — get at [console.anthropic.com](https://console.anthropic.com)
- `CANDIDATE_NAME`, `CANDIDATE_EMAIL`, `CANDIDATE_PHONE`, `CANDIDATE_LOCATION`

### 3. Add your resume

Copy your resume as plain text to:
```
data/resumes/resume.txt
```
See `data/resumes/resume_template.txt` for the expected format.

### 4. Run in dry-run mode (safe — no submissions)

```bash
python main.py --dry-run
```

### 5. Check the output

Generated cover letters and resume summaries appear in:
```
data/applications/<job_id>/
├── cover_letter.txt
├── resume_summary.txt
└── talking_points.json
```

### 6. Go live (when ready)

```bash
# Set DRY_RUN=false in .env, then:
python main.py --live
```

---

## ⚙️ CLI Options

```
python main.py [OPTIONS]

Options:
  --title TEXT        Job title to search for (default: uses config queries)
  --location TEXT     Location / "Remote" (default: Remote)
  --results INT       Results per job board (default: 20)
  --resume PATH       Path to resume .txt (default: data/resumes/resume.txt)
  --max INT           Max applications this run (default: 10)
  --min-score INT     Minimum match score 0-100 (default: 70)
  --dry-run           Generate materials but don't submit
  --live              Actually submit applications

Examples:
  python main.py --title "ML Engineer" --location "Remote" --dry-run
  python main.py --title "Backend Engineer" --min-score 80 --max 5
  python main.py --resume ~/Desktop/resume.txt --live
```

---

## 🔧 Notion Tracker Setup (Optional, Free)

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) → **New Integration**
2. Create a database with these columns:

| Column | Type |
|---|---|
| Title | Title |
| Company | Text |
| Status | Select (Applied, Pending, Failed, Skipped) |
| Score | Number |
| URL | URL |
| Applied At | Text |
| Notes | Text |

3. Share the database with your integration, copy the Database ID from the URL
4. Add to `.env`:
```
NOTION_TOKEN=secret_...
NOTION_DATABASE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

---

## 🔑 API Keys & Cost

| Service | Used For | Cost |
|---|---|---|
| Anthropic Claude | Job matching + cover letter writing | ~$0.01–0.05 per job analyzed |
| JobSpy (no key) | Scraping Indeed/LinkedIn/Glassdoor | Free |
| Notion API | Application tracking dashboard | Free |
| Selenium (local) | Form auto-submission | Free |

**Estimated cost per run (10 jobs):** ~$0.20–0.50

---

## 🛠️ Customization

### Adjust search queries

Edit `config.py`:
```python
DEFAULT_SEARCH_QUERIES = [
    {"title": "Data Scientist", "location": "New York", "results": 30},
    {"title": "ML Engineer", "location": "Remote", "results": 25},
]
```

### Change the Claude model

In `agent/brain.py`, swap `claude-opus-4-5` for `claude-haiku-4-5-20251001` to reduce cost (slightly less quality).

### Add more job platforms

`tools/scraper.py` uses JobSpy which supports: `indeed`, `linkedin`, `glassdoor`, `zip_recruiter`.

---

## ⚠️ Ethical Use

- Always review generated cover letters before going fully autonomous
- Respect job board terms of service — use reasonable rate limits
- Use `DRY_RUN=true` first and review outputs
- Don't apply to jobs you're genuinely not interested in — it wastes recruiters' time

---

## 🤝 Contributing

PRs welcome! Ideas for improvement:

- [ ] Email application support (for jobs that require emailing a resume)
- [ ] GPT-4o Vision to read job post screenshots
- [ ] Greenhouse / Lever / Workday form handlers
- [ ] Daily scheduler (cron / GitHub Actions)
- [ ] Slack/Discord notification on successful applications
- [ ] Interview prep generator per job

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## 🙋 Author

Built by [Your Name](https://github.com/yourusername)

> ⭐ Star this repo if it helped you land a job!
