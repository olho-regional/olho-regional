#!/usr/bin/env python3
"""Reset data for sites with new custom handlers.

Three reset levels:
  A) PREFER_ARCHIVE sites — need full CDX re-scan (source reassignment)
  B) URL filter sites — need CDX re-scan (to filter URLs during discovery)
  C) Custom extract sites — only need quality purge (re-extract same tasks)
  D) Flat-permalink sites — need full CDX re-scan (different URL patterns)

Usage:
  python3 reset_handlers.py --dry-run     # Preview what will be changed
  python3 reset_handlers.py               # Apply changes
  python3 reset_handlers.py --group A     # Only reset group A sites
"""
import argparse
import json
import sys
from pathlib import Path

DATA_DIR = Path("data")

# Group A: PREFER_ARCHIVE — need CDX re-scan because tasks have wrong source
GROUP_A = {
    "beira.pt": "PREFER_ARCHIVE + URL filter (etiquetas/diretorio)",
    "airinformacao.pt": "PREFER_ARCHIVE (live returns HTTP 415)",
    "terrasdegaia.pt": "PREFER_ARCHIVE (live returns HTTP 508)",
    "correiodecaria.com": "PREFER_ARCHIVE (live returns HTTP 415)",
    "ecodevagos.pt": "PREFER_ARCHIVE (live returns HTTP 508)",
}

# Group B: URL filtering — need CDX re-scan to apply new is_article_url
GROUP_B = {
    "correiodoribatejo.pt": "Filter /etiqueta/, /categoria/",
    "mediotejo.net": "Filter /hashtags/, /joomsport_match/, /category/",
    "rodaviva.pt": "Filter /xsitev2p/, /application/, /filemanager/",
    "jornaldabeira.net": "Filter /category/, /edicao/, /revistas/",
}

# Group C: Custom extract — just purge quality.jsonl, keep tasks intact
GROUP_C = {
    "pinhaldigital.com": "Custom Joomla table extract + paginaton filter",
}

# Group D: Flat-permalink — need full CDX re-scan (new URL patterns)
GROUP_D = {
    "torresvedrasweb.pt": "Flat permalink: accept 1-seg, reject 2-seg attachment",
    "azoresacores.com": "Flat permalink + zero-width space cleanup",
    "diarioatual.com": "Flat permalink: reject gallery attachment pages",
    "barcelosnahora.pt": "Flat permalink: reject attachment pages",
    "folhadetondela.pt": "Flat permalink: reject attachment pages",
    "miraonline.pt": "Flat permalink: reject attachment pages",
}


def reset_site_cdx(site_dir: Path, dry_run: bool) -> dict:
    """Full reset: delete tasks + quality, reset CDX state."""
    actions = []
    state_path = site_dir / "state.json"

    # Delete tasks.jsonl
    tasks_path = site_dir / "tasks.jsonl"
    if tasks_path.exists():
        actions.append(f"  DELETE {tasks_path.name} ({tasks_path.stat().st_size:,} bytes)")
        if not dry_run:
            tasks_path.unlink()

    # Delete quality.jsonl
    quality_path = site_dir / "quality.jsonl"
    if quality_path.exists():
        actions.append(f"  DELETE {quality_path.name} ({quality_path.stat().st_size:,} bytes)")
        if not dry_run:
            quality_path.unlink()

    # Reset CDX state flags (force re-scan)
    if state_path.exists():
        state = json.loads(state_path.read_text())
        for key in ("wayback_cdx_done", "arquivo_cdx_done", "sitemap_done"):
            if state.get(key):
                state[key] = False
                actions.append(f"  RESET {key} = false")
        if not dry_run:
            state_path.write_text(json.dumps(state, indent=2))

    return {"actions": actions}


def reset_site_quality(site_dir: Path, dry_run: bool) -> dict:
    """Soft reset: delete quality only, keep tasks (for custom extract fixes)."""
    actions = []

    quality_path = site_dir / "quality.jsonl"
    if quality_path.exists():
        actions.append(f"  DELETE {quality_path.name} ({quality_path.stat().st_size:,} bytes)")
        if not dry_run:
            quality_path.unlink()

    # Also delete articles.jsonl since extraction changed
    articles_path = site_dir / "articles.jsonl"
    if articles_path.exists():
        actions.append(f"  DELETE {articles_path.name} ({articles_path.stat().st_size:,} bytes)")
        if not dry_run:
            articles_path.unlink()

    return {"actions": actions}


def main():
    parser = argparse.ArgumentParser(description="Reset data for sites with new handlers")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--group", choices=["A", "B", "C", "D", "all"], default="all",
                        help="Which group of sites to reset")
    args = parser.parse_args()

    groups = {
        "A": (GROUP_A, reset_site_cdx, "PREFER_ARCHIVE (CDX re-scan)"),
        "B": (GROUP_B, reset_site_cdx, "URL filter (CDX re-scan)"),
        "C": (GROUP_C, reset_site_quality, "Custom extract (quality purge)"),
        "D": (GROUP_D, reset_site_cdx, "Flat permalink (CDX re-scan)"),
    }

    if args.group == "all":
        selected = list(groups.items())
    else:
        selected = [(args.group, groups[args.group])]

    if args.dry_run:
        print("=== DRY RUN — no changes will be made ===\n")

    total_sites = 0
    for group_name, (sites, reset_fn, description) in selected:
        print(f"Group {group_name}: {description}")
        print("-" * 60)
        for domain, reason in sites.items():
            site_dir = DATA_DIR / domain
            if not site_dir.exists():
                print(f"  {domain}: SKIP (no data directory)")
                continue

            result = reset_fn(site_dir, args.dry_run)
            print(f"  {domain}: {reason}")
            for action in result["actions"]:
                print(action)
            total_sites += 1
        print()

    verb = "would be" if args.dry_run else "were"
    print(f"{total_sites} sites {verb} reset.")

    if args.dry_run:
        print("\nTo apply changes, run without --dry-run:")
        print("  python3 reset_handlers.py")
    else:
        print("\nTo re-run affected sites:")
        print("  # Group C (custom extract) — just retry:")
        print("  python3 collect.py pinhaldigital.com")
        print()
        print("  # Groups A/B/D (CDX re-scan) — run per site:")
        for group_name in ("A", "B", "D"):
            sites_dict = groups[group_name][0]
            for domain in sites_dict:
                print(f"  python3 collect.py {domain}")


if __name__ == "__main__":
    main()
