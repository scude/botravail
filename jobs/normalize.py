from __future__ import annotations

import hashlib
import re
from datetime import datetime

from .models import JobCandidate

REMOTE_KEYWORDS = {
    "full_remote": [
        "full remote",
        "télétravail total",
        "teletravail total",
        "100% remote",
        "entièrement à distance",
    ],
    "hybrid": [
        "hybride",
        "hybrid",
        "télétravail partiel",
        "teletravail partiel",
        "2 jours de télétravail",
        "3 jours de télétravail",
    ],
}

TECH_SYNONYMS = {
    "kubernetes": ["k8s", "kubernetes"],
    "react": ["react.js", "reactjs", "react"],
    "typescript": ["typescript", "ts"],
    "javascript": ["javascript", "js"],
    "python": ["python"],
    "aws": ["amazon web services", "aws"],
    "gcp": ["google cloud", "gcp"],
    "azure": ["microsoft azure", "azure"],
    "docker": ["docker"],
    "terraform": ["terraform"],
    "ansible": ["ansible"],
    "postgresql": ["postgresql", "postgres"],
}

ENGLISH_REQUIRED_PATTERNS = [
    r"anglais requis",
    r"english required",
    r"fluent in english",
    r"english fluency",
    r"fluency",
    r"bilingual english",
]

ENGLISH_NOT_REQUIRED_PATTERNS = [
    r"aucune langue attendue",
    r"english not required",
    r"pas d'?anglais",
]


BOILERPLATE_PATTERNS = [
    r"\binformation\b",
    r"\bstatut du poste\b",
    r"\bsalaire\b",
    r"\bà propos de l'?entreprise\b",
]


SALARY_PATTERN = re.compile(
    r"(?P<min>\d+[\s\u202f]?\d*)\s*(?:-|à|to)\s*(?P<max>\d+[\s\u202f]?\d*)\s*(?P<unit>k|k€|€|euros)?",
    flags=re.IGNORECASE,
)

DATE_PATTERN = re.compile(r"(\d{2}/\d{2}/\d{4})")



def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()



def clean_description(description: str | None) -> str:
    if not description:
        return ""
    cleaned = description
    for pattern in BOILERPLATE_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
    return _normalize_whitespace(cleaned)



def extract_salary_bounds(text: str | None) -> tuple[int | None, int | None]:
    if not text:
        return None, None
    match = SALARY_PATTERN.search(text)
    if not match:
        return None, None

    def parse_amount(raw: str) -> int:
        return int(raw.replace(" ", "").replace("\u202f", ""))

    minimum = parse_amount(match.group("min"))
    maximum = parse_amount(match.group("max"))
    unit = (match.group("unit") or "").lower()
    if "k" in unit:
        minimum *= 1000
        maximum *= 1000
    elif minimum < 1000 and maximum < 1000:
        minimum *= 1000
        maximum *= 1000
    return minimum, maximum



def detect_remote_type(*texts: str | None) -> str:
    haystack = " ".join([t or "" for t in texts]).lower()
    for remote_type, keywords in REMOTE_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return remote_type
    return "onsite"



def parse_publication_date(text: str | None) -> datetime | None:
    if not text:
        return None
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%d/%m/%Y")



def extract_technologies(*texts: str | None) -> list[str]:
    haystack = " ".join([t or "" for t in texts]).lower()
    found: list[str] = []
    for canonical, synonyms in TECH_SYNONYMS.items():
        for synonym in synonyms:
            if re.search(rf"\b{re.escape(synonym)}\b", haystack):
                found.append(canonical)
                break
    return sorted(set(found))



def detect_english_required(*texts: str | None) -> bool | None:
    haystack = " ".join([t or "" for t in texts]).lower()
    if any(re.search(pattern, haystack) for pattern in ENGLISH_NOT_REQUIRED_PATTERNS):
        return False
    if any(re.search(pattern, haystack) for pattern in ENGLISH_REQUIRED_PATTERNS):
        return True
    return None



def compute_canonical_hash(title: str, company: str | None, description_clean: str) -> str:
    canonical_input = f"{title.strip()}|{(company or '').strip()}|{description_clean.strip()}"
    return hashlib.sha256(canonical_input.encode("utf-8")).hexdigest()



def normalize_offer(raw_offer: dict, source_name: str, raw_path: str) -> JobCandidate:
    title = _normalize_whitespace(raw_offer.get("title") or "")
    company = _normalize_whitespace(raw_offer.get("company") or "") or None
    location = _normalize_whitespace(raw_offer.get("location") or "") or None
    description_clean = clean_description(raw_offer.get("description"))
    canonical_hash = compute_canonical_hash(title=title, company=company, description_clean=description_clean)
    publication_date = parse_publication_date(raw_offer.get("publication_date"))

    salary_min_eur, salary_max_eur = extract_salary_bounds(raw_offer.get("salary"))
    remote_type = detect_remote_type(raw_offer.get("title"), raw_offer.get("description"), raw_offer.get("location"))
    technologies = extract_technologies(raw_offer.get("title"), raw_offer.get("description"))
    english_required = detect_english_required(raw_offer.get("title"), raw_offer.get("description"))

    return JobCandidate(
        title=title,
        company=company,
        location=location,
        description_clean=description_clean,
        canonical_hash=canonical_hash,
        source_url=_normalize_whitespace(raw_offer.get("url") or ""),
        source_name=source_name,
        source_posted_at=publication_date,
        raw_path=raw_path,
        salary_min_eur=salary_min_eur,
        salary_max_eur=salary_max_eur,
        remote_type=remote_type,
        technologies=technologies,
        english_required=english_required,
    )
