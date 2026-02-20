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
