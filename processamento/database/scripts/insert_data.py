"""
Insert scraped news data into a SQLite database.

Creates two tables:
  - jornais: newspaper metadata from jornais.csv
  - noticias: articles from articles.jsonl files, with FK to jornais

Usage:
    python insert_data.py [--data PATH] [--db PATH] [--jornais PATH]
"""

import argparse
import json
import sys
from pathlib import Path

import sqlite_utils

BATCH_SIZE = 50_000
MAX_ARTICLES_PER_SITE = 5_000
LABELS_BATCH_SIZE = 100_000
TOPICS_THRESHOLD = 0.03

# Domains to exclude entirely (bad content, not real news, etc.)
EXCLUDED_DOMAINS = [
    "jornaldealcochete.com",
]

# Domain merges: map a folder domain to an existing jornal's domain.
# Use this when a data folder contains articles that belong to a known jornal
# but the folder name doesn't match automatically.
# Format: "folder_domain" -> "jornal_domain" (as it appears in jornais.json url field, without www./https://)
DOMAIN_MERGES = {
    # "jm-madeira.pt": "jm-madeira.pt",  # example: folder → jornal domain
}

# Per-domain date cutoffs: exclude articles after this date from the given source.
# Format: domain -> (cutoff_date, source_substring_in_archive_url or None for all sources)
# Articles with date > cutoff AND matching source will be skipped.
DOMAIN_DATE_CUTOFFS = {
    "www.jornaldamaia.pt": ("2021-02-12", "web.archive.org"),  # adult content after this date from wayback
    "www.benaventedigital.pt": ("2017-12-01", None),  # all sources
}

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_PATH = SCRIPT_DIR.parent.parent / "data-scraping" / "data"
DEFAULT_DB_PATH = SCRIPT_DIR.parent / "olho-regional.db"
DEFAULT_JORNAIS_JSON = SCRIPT_DIR.parent / "jornais.json"
DEFAULT_GEO_DATA_JSON = SCRIPT_DIR.parent / "geo_data.json"
DEFAULT_TOPICS_JSONL = SCRIPT_DIR.parent.parent / "topic-detection" / "articles_topics.jsonl"
DEFAULT_REMOVALS_JSONL = SCRIPT_DIR.parent.parent / "news-quality" / "output" / "articles_to_remove.jsonl"
DEFAULT_QUOTES_JSONL = SCRIPT_DIR.parent.parent / "gender-analysis" / "output" / "quotes_with_gender.jsonl"
DEFAULT_ENTITIES_JSONL = SCRIPT_DIR.parent.parent / "entity-detection" / "output" / "entities.jsonl"

ENTITIES_MIN_COUNT = 10  # Only include entities that appear at least this many times
ENTITIES_BATCH_SIZE = 100_000
ENTITY_TYPES_INCLUDED = {"PER", "ORG"}

# Labels to include. Add/remove topics here to control what goes into the DB.
INCLUDED_LABELS = [
    "Agricultura",
    "Alterações climáticas",
    "Animais de Companhia",
    "Aviação",
    "Ciências",
    "Cultura e Entretenimento",
    "Desporto",
    "Economia",
    "Educação",
    "Época Balnear",
    "Geo política",
    "Incêndios",
    "Indústria",
    "Justiça e Crime",
    "Lifestyle",
    "Meteorologia",
    "Migrações",
    "Óbitos",
    "Opinião",
    "Pesca",
    "Política",
    "Reciclagem",
    "Saúde",
    "Segurança Rodoviária",
    "Sociedade",
    "Tecnologia",
    "Trabalho",
    "Turismo",
]

# Minimum hash prefix length for article IDs.
# 3.5M articles, 16^8 = 4.3 billion combinations → collision-free.
ID_LENGTH = 8


def shorten_id(full_hash: str) -> str:
    """Truncate the existing article hash to ID_LENGTH chars."""
    return full_hash[:ID_LENGTH]


def confirm_db_recreation(db_path: Path) -> bool:
    """Ask user to confirm database recreation if it already exists."""
    if not db_path.exists():
        return True
    print(f"\n⚠️  Database already exists: {db_path}")
    print(f"   Size: {db_path.stat().st_size / 1024 / 1024:.1f} MB")
    response = input("   Recreate from scratch? This will DELETE all existing data. [y/N] ")
    return response.strip().lower() in ("y", "yes")


def create_geo_tables(db: sqlite_utils.Database, geo_data_json: Path) -> None:
    """
    Create distritos and municipios tables from geo_data.json.
    Uses INE codigoine as primary keys for hierarchical filtering.
    """
    for table in ("jornais_municipios", "jornais_distritos", "municipios", "distritos"):
        if table in db.table_names():
            db[table].drop()

    with open(geo_data_json, "r", encoding="utf-8") as f:
        geo_data = json.load(f)

    db.execute("""
        CREATE TABLE distritos (
            codigoine TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            regiao TEXT NOT NULL
        )
    """)
    db["distritos"].insert_all(geo_data["distritos"], pk="codigoine")
    print(f"  Created distritos table: {len(geo_data['distritos']):,} records")

    db.execute("""
        CREATE TABLE municipios (
            codigoine TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            distrito_codigoine TEXT NOT NULL REFERENCES distritos(codigoine)
        )
    """)
    db["municipios"].insert_all(geo_data["municipios"], pk="codigoine")
    print(f"  Created municipios table: {len(geo_data['municipios']):,} records")


def create_jornais_table(db: sqlite_utils.Database, jornais_json: Path) -> dict:
    """
    Create jornais table + junction tables from jornais.json.
    Returns a mapping of domain -> jornal_id.
    """
    for table in ("jornais_municipios", "jornais_distritos", "jornais"):
        if table in db.table_names():
            db[table].drop()

    with open(jornais_json, "r", encoding="utf-8") as f:
        jornais = json.load(f)

    records = []
    domain_to_id = {}
    distrito_links = []
    municipio_links = []

    for i, j in enumerate(jornais, start=1):
        url_raw = (j.get("url") or "").strip()
        domain = url_raw.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")

        record = {
            "id": i,
            "nome": j.get("nome") or None,
            "proprietario": j.get("proprietario") or None,
            "estado": j.get("estado") or None,
            "suporte": j.get("suporte") or None,
            "data_inscricao": j.get("data_inscricao") or None,
            "url": url_raw or None,
            "periodicidade": j.get("periodicidade") or None,
            "data_situacao": j.get("data_situacao") or None,
            "erc_url": (j.get("erc") or "").strip('"') or None,
        }
        records.append(record)
        if domain:
            domain_to_id[domain] = i

        for dc in j.get("distrito_codes", []):
            distrito_links.append({"jornal_id": i, "distrito_codigoine": dc})
        for mc in j.get("municipio_codes", []):
            municipio_links.append({"jornal_id": i, "municipio_codigoine": mc})

    db["jornais"].insert_all(records, pk="id")
    print(f"  Created jornais table: {len(records):,} records")

    db.execute("""
        CREATE TABLE jornais_distritos (
            jornal_id INTEGER NOT NULL REFERENCES jornais(id),
            distrito_codigoine TEXT NOT NULL REFERENCES distritos(codigoine),
            PRIMARY KEY (jornal_id, distrito_codigoine)
        )
    """)
    if distrito_links:
        db["jornais_distritos"].insert_all(distrito_links)
    print(f"  Created jornais_distritos table: {len(distrito_links):,} links")

    db.execute("""
        CREATE TABLE jornais_municipios (
            jornal_id INTEGER NOT NULL REFERENCES jornais(id),
            municipio_codigoine TEXT NOT NULL REFERENCES municipios(codigoine),
            PRIMARY KEY (jornal_id, municipio_codigoine)
        )
    """)
    if municipio_links:
        db["jornais_municipios"].insert_all(municipio_links)
    print(f"  Created jornais_municipios table: {len(municipio_links):,} links")

    return domain_to_id


def _domain_variants(domain: str) -> list[str]:
    """Generate plausible domain variants for fuzzy matching."""
    d = domain.lower().rstrip("/")
    variants = [d]

    # Strip path components (e.g. "audiencia.pt/jornal-audiencia-grande-porto" → "audiencia.pt")
    base = d.split("/")[0]
    if base != d and "." in base:
        variants.append(base)

    for v in list(variants):
        # TLD swaps: .com ↔ .pt
        if v.endswith(".com"):
            variants.append(v[:-4] + ".pt")
        elif v.endswith(".pt"):
            variants.append(v[:-3] + ".com")

        # Blogspot TLD: .blogspot.com ↔ .blogspot.pt
        if ".blogspot.com" in v:
            variants.append(v.replace(".blogspot.com", ".blogspot.pt"))
        elif ".blogspot.pt" in v:
            variants.append(v.replace(".blogspot.pt", ".blogspot.com"))

        # sapo.pt subdomain: X.sapo.pt ↔ X.pt / X.com
        if ".sapo.pt" in v:
            variants.append(v.replace(".sapo.pt", ".pt"))
            variants.append(v.replace(".sapo.pt", ".com"))
        elif v.count(".") == 1:
            # e.g. "canalalentejo.pt" → "canalalentejo.sapo.pt"
            name, _tld = v.rsplit(".", 1)
            variants.append(f"{name}.sapo.pt")

        # .com.pt → .pt and vice versa
        if v.endswith(".com.pt"):
            variants.append(v[:-7] + ".pt")

    return variants


def build_domain_lookup(domain_to_id: dict) -> dict:
    """
    Build a flexible domain lookup that handles variations.
    The articles use 'domain' field which may not exactly match jornais URLs.
    Generates variants for TLD swaps, blogspot, sapo.pt subdomains, and paths.
    """
    lookup = {}
    for domain, jornal_id in domain_to_id.items():
        for variant in _domain_variants(domain):
            # Don't overwrite if a more specific match already exists
            if variant not in lookup:
                lookup[variant] = jornal_id
    return lookup


def resolve_jornal_id(domain: str, lookup: dict) -> int | None:
    """Try to match an article's domain to a jornal_id."""
    if not domain:
        return None
    d = domain.lower().rstrip("/")

    # Check explicit merges first
    merged = DOMAIN_MERGES.get(d) or DOMAIN_MERGES.get(d.replace("www.", ""))
    if merged:
        d = merged

    if d in lookup:
        return lookup[d]
    # Try without www.
    if d.startswith("www."):
        bare = d[4:]
        if bare in lookup:
            return lookup[bare]
    else:
        www = f"www.{d}"
        if www in lookup:
            return lookup[www]
    return None




def load_removal_ids(removals_path: Path) -> set:
    """Load article IDs to exclude from the news-quality removal list."""
    if not removals_path.exists():
        return set()
    ids = set()
    with open(removals_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                aid = record.get("id", "")
                if aid:
                    ids.add(aid)
            except json.JSONDecodeError:
                continue
    print(f"  Loaded {len(ids):,} article IDs to exclude (news-quality)")
    return ids


def insert_articles(db: sqlite_utils.Database, data_path: Path, domain_lookup: dict, removal_ids: set) -> None:
    """Insert articles from all articles.jsonl files into noticias table."""
    if "noticias" in db.table_names():
        db["noticias"].drop()

    db.execute("""
        CREATE TABLE noticias (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT,
            text TEXT,
            date TEXT,
            author TEXT,
            archive_url TEXT,
            jornal_id INTEGER REFERENCES jornais(id)
        )
    """)

    # Speed: disable journaling and sync during bulk import (safe — we recreate from scratch)
    db.execute("PRAGMA journal_mode=OFF")
    db.execute("PRAGMA synchronous=OFF")

    total_inserted = 0
    total_skipped = 0
    unmatched_domains = set()

    site_dirs = sorted(d for d in data_path.iterdir() if d.is_dir())

    with db.conn:
        # Single transaction for all inserts
        for site_dir in site_dirs:
            jsonl_file = site_dir / "articles.jsonl"
            if not jsonl_file.exists():
                continue

            # Resolve domain once per folder
            folder_domain = site_dir.name

            # Skip excluded domains
            if folder_domain in EXCLUDED_DOMAINS or folder_domain.replace("www.", "") in EXCLUDED_DOMAINS:
                continue

            folder_jornal_id = resolve_jornal_id(folder_domain, domain_lookup)

            batch = []
            site_count = 0
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    if site_count >= MAX_ARTICLES_PER_SITE:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        total_skipped += 1
                        continue

                    url = record.get("url", "")
                    article_id = record.get("id", "")
                    if not url or not article_id:
                        total_skipped += 1
                        continue

                    # Skip articles flagged for removal (don't count towards site limit)
                    if article_id in removal_ids:
                        total_skipped += 1
                        continue

                    # Apply per-domain date cutoffs
                    cutoff_rule = DOMAIN_DATE_CUTOFFS.get(folder_domain) or DOMAIN_DATE_CUTOFFS.get(folder_domain.replace("www.", ""))
                    if cutoff_rule:
                        cutoff_date, source_match = cutoff_rule
                        art_date = record.get("date", "")
                        archive_url = record.get("archive_url", "") or ""
                        if art_date and art_date > cutoff_date:
                            if source_match is None or source_match in archive_url:
                                total_skipped += 1
                                continue

                    # Use per-folder resolution; fall back to per-record if needed
                    jornal_id = folder_jornal_id
                    if jornal_id is None:
                        domain = record.get("domain", "")
                        jornal_id = resolve_jornal_id(domain, domain_lookup)
                    if jornal_id is None:
                        domain = record.get("domain", folder_domain)
                        if domain:
                            unmatched_domains.add(domain)
                        total_skipped += 1
                        continue

                    # Merge subtitle into text
                    subtitle = record.get("subtitle") or ""
                    body = record.get("text") or ""
                    if subtitle and body:
                        text = f"{subtitle}\n\n{body}"
                    else:
                        text = subtitle or body or None

                    # Prefer agency over author
                    author = record.get("agency") or record.get("author") or None

                    article = {
                        "id": shorten_id(article_id),
                        "url": url,
                        "title": record.get("title") or None,
                        "text": text,
                        "date": record.get("date") or None,
                        "author": author,
                        "archive_url": record.get("archive_url") or None,
                        "jornal_id": jornal_id,
                    }
                    batch.append(article)
                    site_count += 1

                    if len(batch) >= BATCH_SIZE:
                        db["noticias"].insert_all(batch, replace=True)
                        total_inserted += len(batch)
                        batch = []

            if batch:
                db["noticias"].insert_all(batch, replace=True)
                total_inserted += len(batch)
                batch = []

            print(f"  {site_dir.name}: {total_inserted:,} total", end="\r")

    print(f"\n  Created noticias table: {total_inserted:,} articles inserted, {total_skipped:,} skipped")

    if unmatched_domains:
        print(f"  ⚠️  {len(unmatched_domains)} domains could not be matched to jornais:")
        for d in sorted(unmatched_domains)[:20]:
            print(f"     - {d}")
        if len(unmatched_domains) > 20:
            print(f"     ... and {len(unmatched_domains) - 20} more")


def insert_labels(db: sqlite_utils.Database, topics_jsonl: Path) -> None:
    """
    Create labels + noticias_labels tables from articles_topics.jsonl.
    Only includes topics listed in INCLUDED_LABELS.
    """
    if "noticias_labels" in db.table_names():
        db["noticias_labels"].drop()
    if "labels" in db.table_names():
        db["labels"].drop()

    # Create labels table with included topics
    db.execute("""
        CREATE TABLE labels (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            name TEXT NOT NULL
        )
    """)

    label_name_to_id = {}
    for i, name in enumerate(INCLUDED_LABELS, start=1):
        db.execute("INSERT INTO labels (id, type, name) VALUES (?, ?, ?)", [i, "topic", name])
        label_name_to_id[name] = i

    print(f"  Created labels table: {len(label_name_to_id)} labels")

    # Create junction table
    db.execute("""
        CREATE TABLE noticias_labels (
            noticia_id TEXT NOT NULL REFERENCES noticias(id),
            label_id INTEGER NOT NULL REFERENCES labels(id),
            PRIMARY KEY (noticia_id, label_id)
        )
    """)

    # Get set of existing noticia IDs for FK validation
    existing_ids = set(row[0] for row in db.execute("SELECT id FROM noticias").fetchall())
    print(f"  Validating against {len(existing_ids):,} existing noticias")

    # Read topics JSONL and insert matching records
    total_inserted = 0
    total_skipped = 0
    batch = []
    ids_to_remove = set()  # Articles classified under REMOVER_* topics

    with open(topics_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                total_skipped += 1
                continue

            topic = record.get("topic", "")
            score = record.get("topic_score", 0)
            full_id = record.get("id", "")
            noticia_id = shorten_id(full_id)

            # Mark articles with bad-content topics for removal
            if topic.startswith("REMOVER_NOTICIAS_COM_TOPICO") and (score or 0) >= TOPICS_THRESHOLD:
                if noticia_id in existing_ids:
                    ids_to_remove.add(noticia_id)
                continue

            if topic not in label_name_to_id:
                total_skipped += 1
                continue

            if score is None or score < TOPICS_THRESHOLD:
                total_skipped += 1
                continue

            if noticia_id not in existing_ids:
                total_skipped += 1
                continue

            batch.append({
                "noticia_id": noticia_id,
                "label_id": label_name_to_id[topic],
            })

            if len(batch) >= LABELS_BATCH_SIZE:
                db["noticias_labels"].insert_all(batch, replace=True)
                total_inserted += len(batch)
                batch = []
                print(f"  Inserted {total_inserted:,} label links...", end="\r")

    if batch:
        db["noticias_labels"].insert_all(batch, replace=True)
        total_inserted += len(batch)

    print(f"\n  Created noticias_labels table: {total_inserted:,} links, {total_skipped:,} skipped")

    # Remove articles classified as bad content (cookie banners, boilerplate, etc.)
    if ids_to_remove:
        # Remove any label links first
        for i in range(0, len(ids_to_remove), BATCH_SIZE):
            chunk = list(ids_to_remove)[i:i + BATCH_SIZE]
            placeholders = ",".join("?" * len(chunk))
            db.execute(f"DELETE FROM noticias_labels WHERE noticia_id IN ({placeholders})", chunk)
        # Remove the articles
        for i in range(0, len(ids_to_remove), BATCH_SIZE):
            chunk = list(ids_to_remove)[i:i + BATCH_SIZE]
            placeholders = ",".join("?" * len(chunk))
            db.execute(f"DELETE FROM noticias WHERE id IN ({placeholders})", chunk)
        print(f"  Removed {len(ids_to_remove):,} articles with REMOVER_NOTICIAS_COM_TOPICO classification")


def insert_quotes(db: sqlite_utils.Database, quotes_jsonl: Path) -> None:
    """
    Create quotes table from quotes_with_gender.jsonl.
    Each row = one quoted speaker in an article, with inferred gender.
    """
    import re

    if "quotes" in db.table_names():
        db["quotes"].drop()

    db.execute("""
        CREATE TABLE quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            noticia_id TEXT NOT NULL REFERENCES noticias(id),
            speaker TEXT NOT NULL,
            gender TEXT NOT NULL
        )
    """)

    existing_ids = set(row[0] for row in db.execute("SELECT id FROM noticias").fetchall())
    print(f"  Validating against {len(existing_ids):,} existing noticias")

    _ws_re = re.compile(r'[\s\u200b\u00a0]+')

    def normalize_speaker(name: str) -> str:
        """Collapse whitespace, strip, title-case."""
        return _ws_re.sub(' ', name).strip()

    total_inserted = 0
    total_skipped = 0
    batch = []

    with open(quotes_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                total_skipped += 1
                continue

            full_id = record.get("article_id", "")
            noticia_id = shorten_id(full_id)
            gender = record.get("gender", "")
            speaker = normalize_speaker(record.get("speaker", ""))

            if not speaker or gender not in ("M", "F"):
                total_skipped += 1
                continue

            if noticia_id not in existing_ids:
                total_skipped += 1
                continue

            batch.append({
                "noticia_id": noticia_id,
                "speaker": speaker,
                "gender": gender,
            })

            if len(batch) >= BATCH_SIZE:
                db["quotes"].insert_all(batch)
                total_inserted += len(batch)
                batch = []
                print(f"  Inserted {total_inserted:,} quotes...", end="\r")

    if batch:
        db["quotes"].insert_all(batch)
        total_inserted += len(batch)

    print(f"\n  Created quotes table: {total_inserted:,} quotes, {total_skipped:,} skipped")


def insert_entities(db: sqlite_utils.Database, entities_jsonl: Path) -> None:
    """
    Create entities + noticias_entities tables from entities.jsonl.
    Single pass: reads file once, keeps only entities from in-DB articles,
    filters to those appearing in >= ENTITIES_MIN_COUNT distinct articles,
    then inserts from memory.
    """
    import re

    for table in ("noticias_entities", "entities"):
        if table in db.table_names():
            db[table].drop()

    _ws_re = re.compile(r'[\s\u200b\u00a0]+')

    def normalize_name(name: str) -> str:
        return _ws_re.sub(' ', name).strip()

    # Load existing article IDs so we only count entities in articles that are in the DB
    existing_ids = set(row[0] for row in db.execute("SELECT id FROM noticias").fetchall())
    print(f"  Filtering against {len(existing_ids):,} existing noticias")

    # Single pass: count distinct in-DB articles per entity
    print("  Scanning entities (single pass, filtering to in-DB articles)...")
    entity_articles: dict[tuple[str, str], set[str]] = {}  # (name, type) -> set of article IDs
    total_lines = 0
    with open(entities_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            total_lines += 1
            if total_lines % 5_000_000 == 0:
                print(f"    Scanned {total_lines:,} lines...", end="\r")
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            etype = record.get("entity_type", "")
            if etype not in ENTITY_TYPES_INCLUDED:
                continue
            full_id = record.get("article_id", "")
            noticia_id = shorten_id(full_id)
            if noticia_id not in existing_ids:
                continue
            name = normalize_name(record.get("entity_name", ""))
            if not name:
                continue
            key = (name, etype)
            if key not in entity_articles:
                entity_articles[key] = set()
            entity_articles[key].add(noticia_id)

    # Filter to entities appearing in enough distinct articles
    qualified = {k: v for k, v in entity_articles.items() if len(v) >= ENTITIES_MIN_COUNT}
    del entity_articles  # free memory
    print(f"\n  Done: {len(qualified):,} entities with >= {ENTITIES_MIN_COUNT} distinct articles")

    # Build entity ID mapping and insert entities table
    entity_to_id: dict[tuple[str, str], int] = {}
    entity_records = []
    for i, (name, etype) in enumerate(sorted(qualified), start=1):
        entity_to_id[(name, etype)] = i
        entity_records.append({"id": i, "name": name, "entity_type": etype})

    db.execute("""
        CREATE TABLE entities (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            entity_type TEXT NOT NULL
        )
    """)
    for i in range(0, len(entity_records), ENTITIES_BATCH_SIZE):
        db["entities"].insert_all(entity_records[i:i + ENTITIES_BATCH_SIZE])
    print(f"  Created entities table: {len(entity_records):,} entities")

    db.execute("""
        CREATE TABLE noticias_entities (
            noticia_id TEXT NOT NULL REFERENCES noticias(id),
            entity_id INTEGER NOT NULL REFERENCES entities(id),
            PRIMARY KEY (noticia_id, entity_id)
        )
    """)

    # Insert junction rows directly from the in-memory data (no second file pass)
    print("  Inserting article-entity links from memory...")
    total_inserted = 0
    batch = []
    for key, article_ids in qualified.items():
        entity_id = entity_to_id[key]
        for noticia_id in article_ids:
            batch.append({"noticia_id": noticia_id, "entity_id": entity_id})
            if len(batch) >= ENTITIES_BATCH_SIZE:
                db["noticias_entities"].insert_all(batch)
                total_inserted += len(batch)
                batch = []
                print(f"  Inserted {total_inserted:,} links...", end="\r")

    if batch:
        db["noticias_entities"].insert_all(batch)
        total_inserted += len(batch)

    print(f"\n  Created noticias_entities table: {total_inserted:,} links")


def create_summary_tables(db: sqlite_utils.Database) -> None:
    """
    Create pre-aggregated summary tables for fast facet queries.
    These replace expensive GROUP BY scans over the full noticias table.

    Tables created:
      - stats_year_jornal: article count per (year, jornal_id)
      - stats_year_label: article count per (year, jornal_id, label_id)
      - stats_year_gender: quote count per (year, jornal_id, gender)
      - stats_date_jornal: article count per (date, jornal_id) for calendar heatmap
    """
    for table in ("stats_year_jornal", "stats_year_label", "stats_year_gender", "stats_date_jornal"):
        if table in db.table_names():
            db[table].drop()

    # stats_year_jornal: core fact table for counts, yearCounts, jornalCounts, distritoCounts
    db.execute("""
        CREATE TABLE stats_year_jornal (
            year TEXT NOT NULL,
            jornal_id INTEGER NOT NULL REFERENCES jornais(id),
            count INTEGER NOT NULL,
            PRIMARY KEY (year, jornal_id)
        )
    """)
    db.execute("""
        INSERT INTO stats_year_jornal (year, jornal_id, count)
        SELECT substr(date, 1, 4) as year, jornal_id, count(*) as count
        FROM noticias
        WHERE date IS NOT NULL AND length(date) >= 4 AND jornal_id IS NOT NULL
          AND substr(date, 1, 4) GLOB '[0-9][0-9][0-9][0-9]'
        GROUP BY year, jornal_id
    """)
    row_count = db.execute("SELECT count(*) FROM stats_year_jornal").fetchone()[0]
    print(f"  stats_year_jornal: {row_count:,} rows")

    # stats_year_label: for labelCounts facet
    db.execute("""
        CREATE TABLE stats_year_label (
            year TEXT NOT NULL,
            jornal_id INTEGER NOT NULL REFERENCES jornais(id),
            label_id INTEGER NOT NULL REFERENCES labels(id),
            count INTEGER NOT NULL,
            PRIMARY KEY (year, jornal_id, label_id)
        )
    """)
    db.execute("""
        INSERT INTO stats_year_label (year, jornal_id, label_id, count)
        SELECT substr(n.date, 1, 4) as year, n.jornal_id, nl.label_id, count(*) as count
        FROM noticias n
        JOIN noticias_labels nl ON nl.noticia_id = n.id
        WHERE n.date IS NOT NULL AND length(n.date) >= 4 AND n.jornal_id IS NOT NULL
          AND substr(n.date, 1, 4) GLOB '[0-9][0-9][0-9][0-9]'
        GROUP BY year, n.jornal_id, nl.label_id
    """)
    row_count = db.execute("SELECT count(*) FROM stats_year_label").fetchone()[0]
    print(f"  stats_year_label: {row_count:,} rows")

    # stats_year_gender: for genderByYear facet
    db.execute("""
        CREATE TABLE stats_year_gender (
            year TEXT NOT NULL,
            jornal_id INTEGER NOT NULL REFERENCES jornais(id),
            gender TEXT NOT NULL,
            count INTEGER NOT NULL,
            PRIMARY KEY (year, jornal_id, gender)
        )
    """)
    db.execute("""
        INSERT INTO stats_year_gender (year, jornal_id, gender, count)
        SELECT substr(n.date, 1, 4) as year, n.jornal_id, q.gender, count(*) as count
        FROM noticias n
        JOIN quotes q ON q.noticia_id = n.id
        WHERE n.date IS NOT NULL AND length(n.date) >= 4 AND n.jornal_id IS NOT NULL
          AND substr(n.date, 1, 4) GLOB '[0-9][0-9][0-9][0-9]'
        GROUP BY year, n.jornal_id, q.gender
    """)
    row_count = db.execute("SELECT count(*) FROM stats_year_gender").fetchone()[0]
    print(f"  stats_year_gender: {row_count:,} rows")

    # stats_date_jornal: for calendar heatmap (daily counts)
    db.execute("""
        CREATE TABLE stats_date_jornal (
            date TEXT NOT NULL,
            jornal_id INTEGER NOT NULL REFERENCES jornais(id),
            count INTEGER NOT NULL,
            PRIMARY KEY (date, jornal_id)
        )
    """)
    db.execute("""
        INSERT INTO stats_date_jornal (date, jornal_id, count)
        SELECT substr(date, 1, 10) as d, jornal_id, count(*) as count
        FROM noticias
        WHERE date IS NOT NULL AND length(date) >= 10 AND jornal_id IS NOT NULL
          AND substr(date, 1, 4) GLOB '[0-9][0-9][0-9][0-9]'
        GROUP BY d, jornal_id
    """)
    row_count = db.execute("SELECT count(*) FROM stats_date_jornal").fetchone()[0]
    print(f"  stats_date_jornal: {row_count:,} rows")

    # Indexes for fast filtering
    db.execute("CREATE INDEX IF NOT EXISTS idx_stats_yj_year ON stats_year_jornal(year)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_stats_yj_jornal ON stats_year_jornal(jornal_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_stats_yl_year ON stats_year_label(year)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_stats_yl_jornal ON stats_year_label(jornal_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_stats_yl_label ON stats_year_label(label_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_stats_yg_year ON stats_year_gender(year)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_stats_yg_jornal ON stats_year_gender(jornal_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_stats_dj_date ON stats_date_jornal(date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_stats_dj_jornal ON stats_date_jornal(jornal_id)")


def main():
    parser = argparse.ArgumentParser(description="Build SQLite database from scraped news data")
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=f"Path to data directory (default: {DEFAULT_DATA_PATH})",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Output database path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--jornais",
        type=Path,
        default=DEFAULT_JORNAIS_JSON,
        help=f"Path to jornais.json (default: {DEFAULT_JORNAIS_JSON})",
    )
    parser.add_argument(
        "--geo",
        type=Path,
        default=DEFAULT_GEO_DATA_JSON,
        help=f"Path to geo_data.json (default: {DEFAULT_GEO_DATA_JSON})",
    )
    parser.add_argument(
        "--topics",
        type=Path,
        default=DEFAULT_TOPICS_JSONL,
        help=f"Path to articles_topics.jsonl (default: {DEFAULT_TOPICS_JSONL})",
    )
    parser.add_argument(
        "--removals",
        type=Path,
        default=DEFAULT_REMOVALS_JSONL,
        help=f"Path to articles_to_remove.jsonl (default: {DEFAULT_REMOVALS_JSONL})",
    )
    parser.add_argument(
        "--quotes",
        type=Path,
        default=DEFAULT_QUOTES_JSONL,
        help=f"Path to quotes_with_gender.jsonl (default: {DEFAULT_QUOTES_JSONL})",
    )
    parser.add_argument(
        "--entities",
        type=Path,
        default=DEFAULT_ENTITIES_JSONL,
        help=f"Path to entities.jsonl (default: {DEFAULT_ENTITIES_JSONL})",
    )
    args = parser.parse_args()

    if not args.data.exists():
        print(f"Error: data path does not exist: {args.data}")
        sys.exit(1)
    if not args.jornais.exists():
        print(f"Error: jornais.json not found: {args.jornais}")
        sys.exit(1)
    if not args.geo.exists():
        print(f"Error: geo_data.json not found: {args.geo}")
        sys.exit(1)

    if not confirm_db_recreation(args.db):
        print("Aborted.")
        sys.exit(0)

    if args.db.exists():
        args.db.unlink()

    print(f"\nCreating database: {args.db}")
    db = sqlite_utils.Database(args.db)

    # 1. Create geo tables (distritos + municipios)
    print("\n[1/7] Creating geo tables...")
    create_geo_tables(db, args.geo)

    # 2. Create jornais table + junction tables
    print("\n[2/7] Creating jornais table...")
    domain_to_id = create_jornais_table(db, args.jornais)
    domain_lookup = build_domain_lookup(domain_to_id)

    # 3. Insert articles
    print("\n[3/7] Inserting articles...")
    removal_ids = load_removal_ids(args.removals)
    insert_articles(db, args.data, domain_lookup, removal_ids)

    # 4. Insert labels (topics)
    print("\n[4/7] Inserting labels...")
    if args.topics.exists():
        insert_labels(db, args.topics)
    else:
        print(f"  ⚠️  Topics file not found: {args.topics}, skipping labels")

    # 5. Insert quotes (gender analysis)
    print("\n[5/7] Inserting quotes...")
    if args.quotes.exists():
        insert_quotes(db, args.quotes)
    else:
        print(f"  ⚠️  Quotes file not found: {args.quotes}, skipping quotes")

    # 6. Insert entities (NER — PER/ORG only, min count >= 5)
    print("\n[6/7] Inserting entities...")
    if args.entities.exists():
        insert_entities(db, args.entities)
    else:
        print(f"  ⚠️  Entities file not found: {args.entities}, skipping entities")

    # 7. Create summary tables (pre-aggregated for fast facet queries)
    print("\n[7/7] Creating summary tables...")
    create_summary_tables(db)

    # Add indexes
    print("\nCreating indexes...")
    db.execute("CREATE INDEX IF NOT EXISTS idx_noticias_jornal ON noticias(jornal_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_noticias_date ON noticias(date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_noticias_date_jornal ON noticias(date, jornal_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_noticias_author ON noticias(author)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_noticias_labels_label ON noticias_labels(label_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_noticias_labels_noticia ON noticias_labels(noticia_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_jornais_distritos_distrito ON jornais_distritos(distrito_codigoine)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_jornais_municipios_municipio ON jornais_municipios(municipio_codigoine)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_municipios_distrito ON municipios(distrito_codigoine)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_quotes_noticia ON quotes(noticia_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_quotes_gender ON quotes(gender)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_quotes_speaker_gender ON quotes(speaker, gender)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_entities_name_type ON entities(name, entity_type)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_noticias_entities_entity ON noticias_entities(entity_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_noticias_entities_noticia ON noticias_entities(noticia_id)")

    # FTS5 full-text search index on title + text
    print("Creating FTS index on noticias (title, text)...")
    db["noticias"].enable_fts(["title", "text"], fts_version="fts5", create_triggers=True)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"Done! Database: {args.db}")
    print(f"  Size: {args.db.stat().st_size / 1024 / 1024 / 1024:.1f} GB")
    print(f"  distritos: {db['distritos'].count:,} rows")
    print(f"  municipios: {db['municipios'].count:,} rows")
    print(f"  jornais: {db['jornais'].count:,} rows")
    print(f"  jornais_distritos: {db['jornais_distritos'].count:,} rows")
    print(f"  jornais_municipios: {db['jornais_municipios'].count:,} rows")
    print(f"  noticias: {db['noticias'].count:,} rows")
    print(f"  labels: {db['labels'].count:,} rows")
    print(f"  noticias_labels: {db['noticias_labels'].count:,} rows")
    if "quotes" in db.table_names():
        print(f"  quotes: {db['quotes'].count:,} rows")
    if "entities" in db.table_names():
        print(f"  entities: {db['entities'].count:,} rows")
    if "noticias_entities" in db.table_names():
        print(f"  noticias_entities: {db['noticias_entities'].count:,} rows")
    if "stats_year_jornal" in db.table_names():
        print(f"  stats_year_jornal: {db['stats_year_jornal'].count:,} rows")
        print(f"  stats_year_label: {db['stats_year_label'].count:,} rows")
        print(f"  stats_year_gender: {db['stats_year_gender'].count:,} rows")
        print(f"  stats_date_jornal: {db['stats_date_jornal'].count:,} rows")


if __name__ == "__main__":
    main()