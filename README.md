# botravail

An AI-powered job intelligence system that ingests and unifies job postings from heterogeneous sources, applies semantic retrieval and profile-based matching, and leverages contextual language models to generate personalized fit analysis and opportunity prioritization.

## Python dependencies

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install project dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Install Playwright browsers (required for scraping):
   ```bash
   python -m playwright install chromium
   ```

## Scraper architecture

The project is organized to make adding new sources simple:

- `scrapers/base.py`: shared `JobOffer` model + abstract scraper interface.
- `scrapers/your_scrapper.py`: Your implementation.
- `run_scraper.py`: unified CLI entrypoint (`--source ...`).


To add another source, create a new scraper class in `scrapers/` implementing `BaseJobScraper`, then wire it in `run_scraper.py`.

## APEC scraper

The APEC scraper accepts the cookie banner, extracts result links, then opens each offer detail page and returns structured fields.

Run it with the unified CLI:
```bash
python run_scraper.py --source apec --max-results 20
```

Or backward-compatible command:
```bash
python apec_scraper.py --max-results 20
```

Optional arguments:
- `--url`: override the default APEC search URL.
- `--headed`: run Chromium in visible mode.
- `--output-dir`: folder used to store JSON outputs (default: `outputs/json`).
- `--output-file`: explicit JSON output file path.
- `--save-raw`: store raw HTML page for each scraped offer.
- `--raw-dir`: folder used for raw HTML files (default: `outputs/raw`).

JSON output fields: `title`, `url`, `company`, `location`, `contract_type`, `salary`, `publication_date`, `description`.

## PostgreSQL setup (Ubuntu)

1. Update apt and install PostgreSQL:
   ```bash
   sudo apt update
   sudo apt install -y postgresql postgresql-contrib
   ```
2. Start and enable the service:
   ```bash
   sudo systemctl enable --now postgresql
   ```
3. Create a database and user (replace placeholders):
   ```bash
   sudo -u postgres psql -c "CREATE USER botravail_user WITH PASSWORD 'change_me';"
   sudo -u postgres psql -c "CREATE DATABASE botravail OWNER botravail_user;"
   ```
4. Apply the project schema:
   ```bash
   psql "postgresql://botravail_user:change_me@localhost:5432/botravail" -f schema.sql
   ```

The schema is idempotent and can be reapplied safely.

## Migrations

For an existing database, apply SQL migrations in order:

```bash
psql "postgresql://botravail_user:change_me@localhost:5432/botravail" -f migrations/001_add_salary_columns_to_jobs.sql
```

Migration naming uses an incremental prefix (`001_`, `002_`, ...).

`001_add_salary_columns_to_jobs.sql` adds `jobs.salary_min_eur` and `jobs.salary_max_eur` without requiring a full reset.

## Ingestion pipeline

The ingestion CLI reads JSON input(s), normalizes records into a canonical `JobCandidate`, enriches fields, and writes idempotently into PostgreSQL (`jobs` + `job_sources`). Salary ranges are persisted both on `jobs.salary_min_eur` / `jobs.salary_max_eur` and inside `job_scores.score_breakdown`.

Run:
```bash
python -m jobs.ingest --input outputs/json/apec_20260220_162234.json --source apec
# or
python -m jobs.ingest --input outputs/json --source apec
```

Environment variable required:
- `DATABASE_URL` (example: `postgresql://botravail_user:change_me@localhost:5432/botravail`)

You can bootstrap local env vars from the provided template:
```bash
cp .env.example .env
```
`jobs.ingest` automatically loads `.env` (via `python-dotenv`), so exporting `DATABASE_URL` manually is optional.

Normalization/enrichment includes:
- description cleanup (boilerplate removal + whitespace normalization)
- salary min/max extraction in EUR
- remote type detection (`full_remote` / `hybrid` / `onsite`)
- publication date parsing from text like `Publiée le 17/02/2026`
- technology extraction from synonym mapping
- `english_required` detection from language keywords
- `canonical_hash = sha256(title + company + description_clean)`
- tolerant JSON loader repairs common invalid escape sequences from scraped text before parsing
