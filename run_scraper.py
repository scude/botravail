from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run job scrapers and export JSON files")
    parser.add_argument("--source", default="apec", choices=["apec"], help="Source scraper to run")
    parser.add_argument("--url", default=None, help="Override scraper URL")
    parser.add_argument("--max-results", type=int, default=20, help="Max job offers to scrape")
    parser.add_argument("--headed", action="store_true", help="Launch browser in non-headless mode")
    parser.add_argument("--output-dir", default="outputs/json", help="Directory where JSON output is stored")
    parser.add_argument("--output-file", default=None, help="Optional explicit JSON output file path")
    parser.add_argument("--save-raw", action="store_true", help="Store raw HTML for each scraped offer")
    parser.add_argument("--raw-dir", default="outputs/raw", help="Directory where raw HTML files are stored")
    return parser


async def main() -> None:
    args = build_parser().parse_args()

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    if args.save_raw:
        Path(args.raw_dir).mkdir(parents=True, exist_ok=True)

    if args.source == "apec":
        from scrapers.apec import ApecScraper

        scraper = ApecScraper(url=args.url, save_raw=args.save_raw, raw_dir=args.raw_dir)
    else:
        raise ValueError(f"Unsupported source: {args.source}")

    offers = await scraper.scrape_jobs(max_results=args.max_results, headless=not args.headed)
    payload = [asdict(offer) for offer in offers]

    if args.output_file:
        output_path = Path(args.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_path = Path(args.output_dir) / f"{args.source}_{timestamp}.json"

    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\nSaved JSON to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
