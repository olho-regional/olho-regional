"""
Count total articles that would be included in the database,
without per-newspaper limits. Respects exclusions (domains, date cutoffs, removals).

Usage:
    python count_articles.py [--data PATH] [--removals PATH]
"""

import argparse
import json
import sys
from pathlib import Path

from insert_data import (
    DEFAULT_DATA_PATH,
    DEFAULT_REMOVALS_JSONL,
    DOMAIN_DATE_CUTOFFS,
    EXCLUDED_DOMAINS,
    load_removal_ids,
)

SCRIPT_DIR = Path(__file__).resolve().parent


def count_articles(data_path: Path, removal_ids: set) -> None:
    site_dirs = sorted(d for d in data_path.iterdir() if d.is_dir())

    total = 0
    total_skipped = 0
    per_site: list[tuple[str, int]] = []

    for site_dir in site_dirs:
        jsonl_file = site_dir / "articles.jsonl"
        if not jsonl_file.exists():
            continue

        folder_domain = site_dir.name

        if folder_domain in EXCLUDED_DOMAINS or folder_domain.replace("www.", "") in EXCLUDED_DOMAINS:
            continue

        site_count = 0
        site_skipped = 0

        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    site_skipped += 1
                    continue

                url = record.get("url", "")
                article_id = record.get("id", "")
                if not url or not article_id:
                    site_skipped += 1
                    continue

                if article_id in removal_ids:
                    site_skipped += 1
                    continue

                cutoff_rule = DOMAIN_DATE_CUTOFFS.get(folder_domain) or DOMAIN_DATE_CUTOFFS.get(
                    folder_domain.replace("www.", "")
                )
                if cutoff_rule:
                    cutoff_date, source_match = cutoff_rule
                    art_date = record.get("date", "")
                    archive_url = record.get("archive_url", "") or ""
                    if art_date and art_date > cutoff_date:
                        if source_match is None or source_match in archive_url:
                            site_skipped += 1
                            continue

                site_count += 1

        total += site_count
        total_skipped += site_skipped
        per_site.append((folder_domain, site_count))
        print(f"  {folder_domain}: {site_count:,} articles", end="\r")

    print(f"\n{'=' * 50}")
    print(f"Total articles: {total:,}")
    print(f"Total skipped:  {total_skipped:,}")
    print(f"Sites with articles: {len(per_site)}")

    # Top 20 sites by article count
    per_site.sort(key=lambda x: x[1], reverse=True)
    print(f"\nTop 20 sites:")
    for domain, count in per_site[:20]:
        print(f"  {domain:40s} {count:>8,}")


def main():
    parser = argparse.ArgumentParser(description="Count total includable articles")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH, help="Path to data directory")
    parser.add_argument("--removals", type=Path, default=DEFAULT_REMOVALS_JSONL, help="Path to removals file")
    args = parser.parse_args()

    if not args.data.exists():
        print(f"Error: data path does not exist: {args.data}")
        sys.exit(1)

    print("Loading removal IDs...")
    removal_ids = load_removal_ids(args.removals) if args.removals.exists() else set()

    print(f"\nCounting articles in: {args.data}")
    count_articles(args.data, removal_ids)


if __name__ == "__main__":
    main()
