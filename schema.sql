-- ============================================================
-- botravail PostgreSQL schema
--
-- This schema defines the source of truth for job postings:
--   1) jobs: canonical deduplicated job records
--   2) job_sources: one-to-many mapping of external sources per job
--   3) job_scores: latest scoring payload per job
--   4) crawl_runs: traceability and statistics for crawler executions
--
-- Deduplication V1 is handled via jobs.content_hash with a UNIQUE constraint.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    company text,
    location text,
    remote_type text NOT NULL DEFAULT 'unknown',
    description_clean text NOT NULL,
    content_hash text NOT NULL,
    canonical_url text,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT jobs_remote_type_check CHECK (remote_type IN ('full_remote', 'hybrid', 'on_site', 'unknown')),
    CONSTRAINT jobs_content_hash_unique UNIQUE (content_hash)
);

CREATE INDEX IF NOT EXISTS idx_jobs_last_seen_at_desc ON jobs (last_seen_at DESC);

CREATE TABLE IF NOT EXISTS job_sources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id uuid NOT NULL,
    source_name text NOT NULL,
    source_url text NOT NULL,
    raw_path text,
    source_posted_at timestamptz,
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT job_sources_job_id_fkey
        FOREIGN KEY (job_id)
        REFERENCES jobs (id)
        ON DELETE CASCADE,
    CONSTRAINT job_sources_source_name_source_url_unique UNIQUE (source_name, source_url)
);

CREATE INDEX IF NOT EXISTS idx_job_sources_job_id ON job_sources (job_id);
CREATE INDEX IF NOT EXISTS idx_job_sources_source_name ON job_sources (source_name);

CREATE TABLE IF NOT EXISTS job_scores (
    job_id uuid PRIMARY KEY,
    score_total integer NOT NULL,
    score_breakdown jsonb NOT NULL,
    scored_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT job_scores_job_id_fkey
        FOREIGN KEY (job_id)
        REFERENCES jobs (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_job_scores_score_total_desc ON job_scores (score_total DESC);

CREATE TABLE IF NOT EXISTS crawl_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status text NOT NULL DEFAULT 'running',
    stats jsonb NOT NULL DEFAULT '{}'::jsonb,
    error text,
    CONSTRAINT crawl_runs_status_check CHECK (status IN ('running', 'success', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_crawl_runs_source_name_started_at_desc
    ON crawl_runs (source_name, started_at DESC);

CREATE OR REPLACE FUNCTION set_updated_at_timestamp()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_jobs_set_updated_at ON jobs;
CREATE TRIGGER trg_jobs_set_updated_at
BEFORE UPDATE ON jobs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at_timestamp();
