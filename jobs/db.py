from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

import psycopg
from dotenv import find_dotenv, load_dotenv

from .models import JobCandidate

LOGGER = logging.getLogger(__name__)


@dataclass
class IngestStats:
    read: int = 0
    inserted: int = 0
    merged: int = 0
    errors: int = 0


def get_connection() -> psycopg.Connection:
    # Load .env from current working directory (and parents) if present.
    load_dotenv(find_dotenv(usecwd=True), override=False)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is required (set it in your shell or in a .env file at project root)"
        )
    return psycopg.connect(database_url)


def upsert_job(conn: psycopg.Connection, candidate: JobCandidate) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO jobs (
                title,
                company,
                location,
                remote_type,
                description_clean,
                content_hash,
                canonical_url,
                last_seen_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (content_hash)
            DO UPDATE SET
                title = EXCLUDED.title,
                company = EXCLUDED.company,
                location = EXCLUDED.location,
                remote_type = EXCLUDED.remote_type,
                description_clean = EXCLUDED.description_clean,
                canonical_url = EXCLUDED.canonical_url,
                last_seen_at = now()
            RETURNING id, (xmax = 0) AS inserted
            """,
            (
                candidate.title,
                candidate.company,
                candidate.location,
                "on_site" if candidate.remote_type == "onsite" else candidate.remote_type,
                candidate.description_clean,
                candidate.canonical_hash,
                candidate.source_url,
            ),
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("Upsert jobs query did not return a row")
        job_id, inserted = row

        cur.execute(
            """
            INSERT INTO job_sources (
                job_id,
                source_name,
                source_url,
                raw_path,
                source_posted_at,
                last_seen_at
            )
            VALUES (%s, %s, %s, %s, %s, now())
            ON CONFLICT (source_name, source_url)
            DO UPDATE SET
                job_id = EXCLUDED.job_id,
                raw_path = EXCLUDED.raw_path,
                source_posted_at = EXCLUDED.source_posted_at,
                last_seen_at = now()
            """,
            (
                job_id,
                candidate.source_name,
                candidate.source_url,
                candidate.raw_path,
                candidate.source_posted_at,
            ),
        )

        cur.execute(
            """
            INSERT INTO job_scores (job_id, score_total, score_breakdown, scored_at)
            VALUES (%s, 0, %s::jsonb, now())
            ON CONFLICT (job_id)
            DO NOTHING
            """,
            (
                job_id,
                json.dumps(
                    {
                        "salary_min_eur": candidate.salary_min_eur,
                        "salary_max_eur": candidate.salary_max_eur,
                        "technologies": candidate.technologies,
                        "english_required": candidate.english_required,
                    },
                    ensure_ascii=False,
                ),
            ),
        )

    return bool(inserted)


def ingest_candidates(candidates: list[JobCandidate]) -> IngestStats:
    stats = IngestStats(read=len(candidates))
    with get_connection() as conn:
        for candidate in candidates:
            try:
                inserted = upsert_job(conn, candidate)
                if inserted:
                    stats.inserted += 1
                else:
                    stats.merged += 1
            except Exception:
                LOGGER.exception("Failed to ingest offer from %s", candidate.raw_path)
                stats.errors += 1
        conn.commit()
    return stats
