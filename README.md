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
