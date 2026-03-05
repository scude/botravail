from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class JobCandidate:
    title: str
    company: str | None
    location: str | None
    description_clean: str
    canonical_hash: str
    source_url: str
    source_name: str
    source_posted_at: datetime | None
    raw_path: str
    salary_min_eur: int | None
    salary_max_eur: int | None
    remote_type: str
    technologies: list[str]
    english_required: bool | None
