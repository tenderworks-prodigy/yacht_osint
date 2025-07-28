# yacht_osint

Automated OSINT scraper for super‑yachts (build ≥2010) and their tenders. The
pipeline collects public articles, extracts structured information and pushes
the resulting CSVs to Google Drive. A shared Google Sheet uses `IMPORTDATA()` to
load these CSVs for analysis.

## Installation

```bash
pip install -r requirements.txt
```

## Required secrets

Environment variables and GitHub secrets used by the pipeline:

- `HF_TOKEN`
- `GROQ_API_KEY`
- `RCLONE_CONFIG`
- `GOOGLE_CSE_API_KEY`
- `GOOGLE_CSE_CX`
- `DRIVE_FOLDER_ID`
- `SPREADSHEET_ID`

## Google Sheets formulas

```
=IMPORTDATA("https://raw.githubusercontent.com/tenderworks-prodigy/yacht_osint/main/data/exports/yachts.csv")
=IMPORTDATA("https://raw.githubusercontent.com/tenderworks-prodigy/yacht_osint/main/data/exports/tenders.csv")
=IMPORTDATA("https://raw.githubusercontent.com/tenderworks-prodigy/yacht_osint/main/data/exports/yacht_aliases.csv")
=IMPORTDATA("https://raw.githubusercontent.com/tenderworks-prodigy/yacht_osint/main/data/exports/yacht_events.csv")
=IMPORTDATA("https://raw.githubusercontent.com/tenderworks-prodigy/yacht_osint/main/data/exports/sources.csv")
```

## Pipeline overview

```
RSS → Sitemap → CSE → Crawl → Wayback → Parse → Extract → Dedupe →
DuckDB → Exports → rclone → QA → Report
```

### Automatic source discovery

Search terms for Google Custom Search are defined in `configs/settings.yml` under
`search.queries`. Running `python -m src.cli` will issue these queries, collect
unique domains and attempt RSS feed discovery for each domain. Discovered feeds
are saved to `yacht_osint/data/cache/discovered_feeds.json`.
