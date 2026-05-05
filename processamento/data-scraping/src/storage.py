import json
from pathlib import Path


def append_jsonl(path: Path, records: list[dict]):
    """Append records to a JSONL file."""
    with open(path, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    """Read all records from a JSONL file."""
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def count_lines(path: Path) -> int:
    """Count lines in a file."""
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def load_processed_urls(data_dir: Path) -> set[str]:
    """Load URLs already extracted into articles.jsonl."""
    articles_path = data_dir / "articles.jsonl"
    urls = set()
    for rec in read_jsonl(articles_path):
        if "url" in rec:
            urls.add(rec["url"])
    return urls


def load_errored_urls(data_dir: Path) -> set[str]:
    """Load URLs that previously failed (from quality.jsonl)."""
    quality_path = data_dir / "quality.jsonl"
    urls = set()
    for rec in read_jsonl(quality_path):
        if "url" in rec:
            urls.add(rec["url"])
    return urls


def purge_quality_urls(data_dir: Path, urls_to_remove: set[str]) -> int:
    """Remove records from quality.jsonl for the given URLs.

    Used before --retry so that only the latest attempt's result is kept.
    Returns the number of records removed.
    """
    quality_path = data_dir / "quality.jsonl"
    if not quality_path.exists():
        return 0
    records = read_jsonl(quality_path)
    kept = [r for r in records if r.get("url") not in urls_to_remove]
    removed = len(records) - len(kept)
    if removed:
        quality_path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept),
            encoding="utf-8",
        )
    return removed


def load_state(data_dir: Path) -> dict:
    """Load pipeline state checkpoint."""
    state_path = data_dir / "state.json"
    if state_path.exists():
        with open(state_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(data_dir: Path, state: dict):
    """Save pipeline state checkpoint."""
    state_path = data_dir / "state.json"
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
