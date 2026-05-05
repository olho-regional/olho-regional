"""
Find all data folders whose domain can't be matched to a jornal in jornais.json.
Writes a CSV with: folder_domain, article_count, sample_url, sample_title, suggested_jornal, suggested_url, similarity.

Usage:
    python find_unmatched.py [--data PATH] [--jornais PATH] [--output PATH]
"""

import argparse
import csv
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

from insert_data import (
    DEFAULT_DATA_PATH,
    DEFAULT_JORNAIS_JSON,
    DOMAIN_MERGES,
    EXCLUDED_DOMAINS,
    build_domain_lookup,
    resolve_jornal_id,
)

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = SCRIPT_DIR / "unmatched_domains.csv"


def _normalize_domain(d: str) -> str:
    """Strip www., protocol, trailing slash for comparison."""
    return d.lower().replace("www.", "").replace("https://", "").replace("http://", "").rstrip("/")


def fuzzy_match(domain: str, jornais: list[dict]) -> tuple[str, str, float]:
    """Find the best fuzzy match for a domain among jornais. Returns (nome, url, score)."""
    norm = _normalize_domain(domain)
    best_score = 0.0
    best_nome = ""
    best_url = ""

    for j in jornais:
        url_raw = (j.get("url") or "").strip()
        if not url_raw:
            continue
        jornal_domain = _normalize_domain(url_raw)
        score = SequenceMatcher(None, norm, jornal_domain).ratio()
        if score > best_score:
            best_score = score
            best_nome = j.get("nome", "")
            best_url = url_raw

    return best_nome, best_url, round(best_score, 3)


def find_unmatched(data_path: Path, jornais_json: Path, output_path: Path) -> None:
    # Build domain lookup from jornais.json (without needing a DB)
    with open(jornais_json, "r", encoding="utf-8") as f:
        jornais = json.load(f)

    domain_to_id = {}
    for i, j in enumerate(jornais, start=1):
        url_raw = (j.get("url") or "").strip()
        domain = url_raw.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
        if domain:
            domain_to_id[domain] = i

    lookup = build_domain_lookup(domain_to_id)

    site_dirs = sorted(d for d in data_path.iterdir() if d.is_dir())
    results = []

    for site_dir in site_dirs:
        jsonl_file = site_dir / "articles.jsonl"
        if not jsonl_file.exists():
            continue

        folder_domain = site_dir.name

        # Skip excluded domains (these are intentionally excluded, not "unmatched")
        if folder_domain in EXCLUDED_DOMAINS or folder_domain.replace("www.", "") in EXCLUDED_DOMAINS:
            continue

        # Check if this folder's domain resolves
        jornal_id = resolve_jornal_id(folder_domain, lookup)
        if jornal_id is not None:
            continue

        # Count articles and grab a sample
        count = 0
        sample_url = ""
        sample_title = ""
        with open(jsonl_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("url") and record.get("id"):
                    count += 1
                    if count == 1:
                        sample_url = record.get("url", "")
                        sample_title = record.get("title", "")

        if count == 0:
            continue

        suggested_nome, suggested_url, similarity = fuzzy_match(folder_domain, jornais)

        results.append({
            "folder_domain": folder_domain,
            "article_count": count,
            "sample_url": sample_url,
            "sample_title": sample_title,
            "suggested_jornal": suggested_nome,
            "suggested_url": suggested_url,
            "similarity": similarity,
        })
        print(f"  Unmatched: {folder_domain} ({count:,} articles)", end="\r")

    results.sort(key=lambda r: r["article_count"], reverse=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["folder_domain", "article_count", "suggested_jornal", "suggested_url", "similarity", "sample_url", "sample_title"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{'=' * 50}")
    print(f"Unmatched domains: {len(results)}")
    total_articles = sum(r["article_count"] for r in results)
    print(f"Total articles in unmatched: {total_articles:,}")
    print(f"Written to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Find data folders with no matching jornal")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH, help="Path to data directory")
    parser.add_argument("--jornais", type=Path, default=DEFAULT_JORNAIS_JSON, help="Path to jornais.json")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output CSV path")
    args = parser.parse_args()

    if not args.data.exists():
        print(f"Error: data path does not exist: {args.data}")
        sys.exit(1)
    if not args.jornais.exists():
        print(f"Error: jornais.json not found: {args.jornais}")
        sys.exit(1)

    print(f"Scanning data folders in: {args.data}")
    print(f"Using jornais from: {args.jornais}")
    find_unmatched(args.data, args.jornais, args.output)


if __name__ == "__main__":
    main()
