from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

from .db import ingest_candidates
from .models import JobCandidate
from .normalize import normalize_offer

LOGGER = logging.getLogger(__name__)

INVALID_ESCAPE_RE = re.compile(r'\\(?!["\\/bfnrtu])')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Normalize scraped job JSON files and ingest into Postgres")
    parser.add_argument(
        "--input",
        required=True,
        help="Input path: JSON file, directory containing JSON files, or glob (e.g. outputs/json/*.json)",
    )
    parser.add_argument("--source", required=True, help="Logical source name (e.g. apec)")
    return parser


def _parse_json_text(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        LOGGER.warning("Invalid JSON in %s (%s). Trying lenient escape repair.", path, exc)

    repaired_text = INVALID_ESCAPE_RE.sub(r"\\\\", text)
    return json.loads(repaired_text)


def _load_file(path: Path, source_name: str) -> tuple[list[JobCandidate], int]:
    try:
        payload = _parse_json_text(path)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        LOGGER.error("Skipping unreadable JSON file %s: %s", path, exc)
        return [], 1

    records = payload if isinstance(payload, list) else [payload]
    candidates: list[JobCandidate] = []
    invalid_items = 0
    for record in records:
        if not isinstance(record, dict):
            LOGGER.warning("Skipping non-object item in %s", path)
            invalid_items += 1
            continue
        candidates.append(normalize_offer(record, source_name=source_name, raw_path=str(path)))
    return candidates, invalid_items


def resolve_input_files(raw_input: str) -> list[Path]:
    input_path = Path(raw_input)

    if input_path.exists() and input_path.is_file() and input_path.suffix.lower() == ".json":
        return [input_path]

    if input_path.exists() and input_path.is_dir():
        return sorted(input_path.glob("*.json"))

    glob_matches = sorted(Path().glob(raw_input))
    if glob_matches:
        return [path for path in glob_matches if path.is_file() and path.suffix.lower() == ".json"]

    fallback_json_dir = Path("outputs/json")
    fallback_hint = ""
    if fallback_json_dir.exists() and fallback_json_dir.is_dir():
        known_files = sorted(fallback_json_dir.glob("*.json"))
        if known_files:
            fallback_hint = f" Did you mean one of: {', '.join(str(path) for path in known_files[:3])}?"

    raise SystemExit(
        f"Input not found or unsupported: {raw_input}. "
        "Use a JSON file, a directory, or a glob pattern like outputs/json/*.json."
        f"{fallback_hint}"
    )


def load_candidates(input_files: list[Path], source_name: str) -> tuple[list[JobCandidate], int]:
    candidates: list[JobCandidate] = []
    parse_errors = 0
    for json_file in input_files:
        LOGGER.info("Reading %s", json_file)
        loaded, file_errors = _load_file(json_file, source_name=source_name)
        candidates.extend(loaded)
        parse_errors += file_errors
    return candidates, parse_errors


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    args = build_parser().parse_args()

    input_files = resolve_input_files(args.input)
    if not input_files:
        raise SystemExit(f"No JSON files found from input: {args.input}")

    candidates, parse_errors = load_candidates(input_files=input_files, source_name=args.source)
    stats = ingest_candidates(candidates)
    total_errors = stats.errors + parse_errors

    LOGGER.info(
        "Ingestion complete | read=%s inserted=%s merged=%s errors=%s",
        stats.read,
        stats.inserted,
        stats.merged,
        total_errors,
    )


if __name__ == "__main__":
    main()
