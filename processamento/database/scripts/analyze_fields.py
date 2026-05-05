"""
Analyze null/empty field percentages across all articles.jsonl files.
Helps decide which fields to include in the database schema.
"""

import json
import os
import argparse
from collections import defaultdict
from pathlib import Path


def analyze_fields(data_path: str) -> None:
    data_dir = Path(data_path)
    if not data_dir.exists():
        print(f"Error: {data_dir} does not exist")
        return

    field_counts = defaultdict(int)  # field -> number of records that have it non-null/non-empty
    field_total = defaultdict(int)   # field -> total records that have the field at all
    total_records = 0
    files_processed = 0

    for site_dir in sorted(data_dir.iterdir()):
        if not site_dir.is_dir():
            continue
        jsonl_file = site_dir / "articles.jsonl"
        if not jsonl_file.exists():
            continue

        files_processed += 1
        with open(jsonl_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                total_records += 1
                for key, value in record.items():
                    field_total[key] += 1
                    if value is not None and value != "" and value != []:
                        field_counts[key] += 1

    if total_records == 0:
        print("No records found.")
        return

    # Print results
    print(f"{'=' * 70}")
    print(f"FIELD ANALYSIS - {total_records:,} articles from {files_processed} sites")
    print(f"{'=' * 70}")
    print(f"{'Field':<20s} {'Present':>10s} {'Non-empty':>10s} {'% filled':>10s} {'% of total':>10s}")
    print(f"{'-' * 70}")

    all_fields = sorted(field_total.keys(), key=lambda k: field_counts.get(k, 0), reverse=True)
    for field in all_fields:
        present = field_total[field]
        filled = field_counts[field]
        pct_of_present = 100 * filled / present if present > 0 else 0
        pct_of_total = 100 * filled / total_records
        print(f"{field:<20s} {present:>10,} {filled:>10,} {pct_of_present:>9.1f}% {pct_of_total:>9.1f}%")

    print(f"\n{'=' * 70}")
    print("RECOMMENDATION:")
    print(f"{'=' * 70}")
    for field in all_fields:
        filled = field_counts[field]
        pct = 100 * filled / total_records
        if pct >= 90:
            status = "INCLUDE"
        elif pct >= 50:
            status = "CONSIDER"
        elif pct >= 10:
            status = "OPTIONAL"
        else:
            status = "SKIP"
        print(f"  {status:<10s} {field:<20s} ({pct:.1f}% filled)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze field coverage in articles.jsonl files")
    parser.add_argument(
        "data_path",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent.parent / "data-scraping" / "data"),
        help="Path to the data directory containing site folders with articles.jsonl",
    )
    args = parser.parse_args()
    analyze_fields(args.data_path)
