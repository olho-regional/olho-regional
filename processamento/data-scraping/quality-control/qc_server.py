#!/usr/bin/env python3
"""Quality control dashboard for arquivo-26 scraping project.

Run: python3 quality-control/qc_server.py
Opens at http://localhost:8066
"""

import csv
import hashlib
import json
import mimetypes
import os
import statistics
import urllib.parse
from collections import Counter
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
JORNAIS_CSV = BASE_DIR / "jornais.csv"
PORT = int(os.environ.get("QC_PORT", "8066"))


# ── Data helpers ──────────────────────────────────────────────────────────────

def read_jsonl(path: Path, limit: int = 0) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
                if limit and len(records) >= limit:
                    break
    return records


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def fast_count_lines(path: Path) -> int:
    """Fast line count using wc -l (for large files)."""
    if not path.exists():
        return 0
    import subprocess
    r = subprocess.run(["wc", "-l", str(path)], capture_output=True, text=True)
    if r.returncode == 0:
        return int(r.stdout.strip().split()[0])
    return 0


def _file_size(path: Path) -> int:
    """File size in bytes, 0 if missing."""
    return path.stat().st_size if path.exists() else 0


def _count_task_sources(path: Path) -> tuple[int, int, int, int]:
    """Count tasks by source. Returns (total, live, arquivo, wayback)."""
    if not path.exists():
        return 0, 0, 0, 0

    live = arq = wb = total = 0
    with open(path, "rb") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            total += 1
            if b'"live"' in line:
                live += 1
            elif b'"arquivo"' in line:
                arq += 1
            elif b'"wayback"' in line:
                wb += 1

    return total, live, arq, wb


def load_state(data_dir: Path) -> dict:
    p = data_dir / "state.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def parse_jornais() -> list[dict]:
    rows = []
    with open(JORNAIS_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def domain_from_url(url: str) -> str:
    d = url.replace("https://", "").replace("http://", "").rstrip("/")
    if d.startswith("www."):
        d = d[4:]
    return d


def get_all_data_dirs() -> list[Path]:
    """Find all directories containing state.json under DATA_DIR."""
    dirs = []
    for p in DATA_DIR.rglob("state.json"):
        dirs.append(p.parent)
    return sorted(dirs)


def domain_key(data_dir: Path) -> str:
    """Get domain key relative to DATA_DIR."""
    return str(data_dir.relative_to(DATA_DIR))


def _get_custom_domains() -> set[str]:
    """Parse custom handler files to find which domains have custom extractors."""
    import re
    sites_dir = BASE_DIR / "src" / "sites"
    custom_domains = set()
    for pyfile in sites_dir.glob("*.py"):
        if pyfile.name in ("__init__.py", "base.py", "registry.py"):
            continue
        try:
            text = pyfile.read_text()
            m = re.search(r'DOMAINS\s*=\s*\[([^\]]+)\]', text)
            if m:
                for d in re.findall(r'"([^"]+)"', m.group(1)):
                    cd = d.lower()
                    if cd.startswith("www."):
                        cd = cd[4:]
                    custom_domains.add(cd)
        except Exception:
            pass
    return custom_domains


_sites_cache: tuple[float, list[dict]] | None = None


def gather_sites() -> list[dict]:
    """Gather status for all sites. Cached for 30 seconds."""
    global _sites_cache
    import time
    now = time.time()
    if _sites_cache and (now - _sites_cache[0]) < 30:
        return _sites_cache[1]

    jornais = {domain_from_url(r.get("url", "")): r for r in parse_jornais()}
    custom_domains = _get_custom_domains()
    sites = []
    for ddir in get_all_data_dirs():
        dk = domain_key(ddir)
        state = load_state(ddir)

        art_path = ddir / "articles.jsonl"
        err_path = ddir / "quality.jsonl"
        task_path = ddir / "tasks.jsonl"

        n_articles = fast_count_lines(art_path)
        n_errors = fast_count_lines(err_path)
        n_tasks, tasks_live, tasks_arquivo, tasks_wayback = _count_task_sources(task_path)

        total = n_articles + n_errors
        ok_pct = (n_articles / total * 100) if total > 0 else 0

        disc = ""
        if state.get("arquivo_cdx_done"):
            disc += "C"
        if state.get("wayback_cdx_done"):
            disc += "W"
        if state.get("sitemap_done"):
            disc += "S"

        # Phase
        if n_articles > 0 and n_tasks > 0 and total >= n_tasks:
            phase = "complete"
        elif n_articles > 0:
            phase = "fetching"
        elif n_tasks > 0:
            phase = "tasks"
        elif disc:
            phase = "discovery"
        else:
            phase = "pending"

        base_domain = dk.split("/")[0] if "/" in dk else dk
        jornal = jornais.get(base_domain, {})

        # Logo info
        logo_file = state.get("logo_file", "")
        logo_wrong = state.get("logo_wrong", False)
        has_logo = bool(logo_file and (ddir / logo_file).exists() and not logo_wrong)

        review_state = state.get("review_state", "TODO")

        sites.append({
            "domain": dk,
            "name": jornal.get("nome", dk),
            "regiao": jornal.get("regiao", ""),
            "disc": disc,
            "articles": n_articles,
            "errors": n_errors,
            "tasks": n_tasks,
            "tasks_live": tasks_live,
            "tasks_arquivo": tasks_arquivo,
            "tasks_wayback": tasks_wayback,
            "ok_pct": ok_pct,
            "phase": phase,
            "has_custom": base_domain in custom_domains,
            "has_logo": has_logo,
            "logo_wrong": logo_wrong,
            "review": review_state,
        })

    _sites_cache = (now, sites)
    return sites


def site_detail(dk: str) -> dict:
    """Detailed analysis for one site."""
    ddir = DATA_DIR / dk
    state = load_state(ddir)
    articles = read_jsonl(ddir / "articles.jsonl")
    quality = read_jsonl(ddir / "quality.jsonl")
    tasks = read_jsonl(ddir / "tasks.jsonl")

    # Failure reasons
    reasons = Counter(q.get("reason", "unknown") for q in quality)

    # Field completeness
    fields = {}
    n = len(articles) or 1
    for field in ("title", "date", "author", "agency", "section"):
        present = sum(1 for a in articles if a.get(field))
        fields[field] = round(present / n * 100, 1)

    # Text length stats
    lengths = [int(a.get("text_length", 0)) for a in articles]
    length_stats = {}
    if lengths:
        ls = sorted(lengths)
        length_stats = {
            "median": int(statistics.median(ls)),
            "p10": ls[max(0, len(ls) // 10)],
            "p90": ls[min(len(ls) - 1, len(ls) * 9 // 10)],
            "short": sum(1 for l in ls if l < 100),
        }

    # Year distribution
    year_counts = Counter()
    for a in articles:
        d = a.get("date", "")
        if d and len(d) >= 4:
            try:
                y = int(d[:4])
                if 1990 <= y <= 2030:
                    year_counts[y] += 1
            except ValueError:
                pass

    # Source distribution
    source_counts = Counter(a.get("source", "?") for a in articles)

    # Extractor distribution
    extractor_counts = Counter(a.get("extractor", "?") for a in articles)

    # Sample articles (newest first by date)
    sorted_articles = sorted(articles, key=lambda a: a.get("date", "") or "", reverse=True)
    samples = []
    for a in sorted_articles[:20]:
        text = a.get("text", "")
        samples.append({
            "url": a.get("url", ""),
            "title": a.get("title", ""),
            "date": a.get("date", ""),
            "author": a.get("author", ""),
            "agency": a.get("agency", ""),
            "source": a.get("source", ""),
            "text_length": a.get("text_length", 0),
            "text_preview": text[:150] if text else "",
            "archive_url": a.get("archive_url", ""),
            "extractor": a.get("extractor", ""),
        })

    # URL prefix map from state
    prefix_map = state.get("url_prefix_map", {})

    # Recommendations
    recs = []
    total = len(articles) + len(quality)
    if total > 0:
        pct = len(articles) / total * 100
        if pct < 70:
            recs.append(f"Low success rate ({pct:.0f}%) — custom handler likely needed")
    for f, p in fields.items():
        if f == "agency":
            continue
        if p < 60:
            recs.append(f"'{f}' extraction only {p:.0f}% — check extractor")
    if length_stats.get("short", 0) > len(articles) * 0.2:
        recs.append(f"{length_stats['short']} articles with <100 chars — possible extraction issues")

    # Logo info
    logo_file = state.get("logo_file", "")
    logo_wrong = state.get("logo_wrong", False)
    has_logo = bool(logo_file and (ddir / logo_file).exists() and not logo_wrong)

    review_state = state.get("review_state", "TODO")

    return {
        "domain": dk,
        "state": state,
        "articles_count": len(articles),
        "errors_count": len(quality),
        "tasks_count": len(tasks),
        "tasks_live": sum(1 for t in tasks if t.get("source") == "live"),
        "tasks_arquivo": sum(1 for t in tasks if t.get("source") == "arquivo"),
        "tasks_wayback": sum(1 for t in tasks if t.get("source") == "wayback"),
        "failure_reasons": dict(reasons.most_common(10)),
        "field_completeness": fields,
        "text_length": length_stats,
        "year_distribution": dict(sorted(year_counts.items())),
        "source_counts": dict(source_counts),
        "extractor_counts": dict(extractor_counts),
        "samples": samples,
        "prefix_map": prefix_map,
        "recommendations": recs,
        "has_logo": has_logo,
        "logo_wrong": logo_wrong,
        "review": review_state,
    }


def search_articles(dk: str, query: str, limit: int = 50) -> list[dict]:
    """Search articles for a site by URL or title substring."""
    ddir = DATA_DIR / dk
    q = query.lower()
    results = []
    for path_name in ("articles.jsonl", "quality.jsonl"):
        p = ddir / path_name
        if not p.exists():
            continue
        kind = "article" if "articles" in path_name else "error"
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                haystack = (rec.get("url", "") + " " + rec.get("title", "")).lower()
                if q in haystack:
                    results.append({
                        "kind": kind,
                        "url": rec.get("url", ""),
                        "title": rec.get("title", ""),
                        "date": rec.get("date", ""),
                        "source": rec.get("source", ""),
                        "text_length": rec.get("text_length", 0),
                        "reason": rec.get("reason", ""),
                        "archive_url": rec.get("archive_url", ""),
                    })
                    if len(results) >= limit:
                        return results
    return results


def search_all_sites(query: str, limit: int = 100) -> list[dict]:
    """Search articles across ALL sites."""
    q = query.lower()
    results = []
    for ddir in get_all_data_dirs():
        dk = domain_key(ddir)
        for path_name in ("articles.jsonl",):
            p = ddir / path_name
            if not p.exists():
                continue
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    haystack = (rec.get("url", "") + " " + rec.get("title", "") + " " + rec.get("text", "")[:200]).lower()
                    if q in haystack:
                        results.append({
                            "domain": dk,
                            "url": rec.get("url", ""),
                            "title": rec.get("title", ""),
                            "date": rec.get("date", ""),
                            "source": rec.get("source", ""),
                            "text_length": rec.get("text_length", 0),
                            "archive_url": rec.get("archive_url", ""),
                        })
                        if len(results) >= limit:
                            return results
    return results


def quality_analysis(dk: str) -> dict:
    """Per-site quality analysis: duplicate detection, content patterns."""
    ddir = DATA_DIR / dk
    articles = read_jsonl(ddir / "articles.jsonl")
    if not articles:
        return {"has_data": False}

    # Duplicate text detection via text hash
    text_hashes: dict[str, list[dict]] = {}
    text_samples: dict[str, tuple[str, int]] = {}  # hash -> (text_preview, full_length)
    title_counts: Counter = Counter()
    empty_texts = 0
    very_short = 0  # < 50 chars

    for a in articles:
        text = a.get("text", "")
        title = a.get("title", "")
        tlen = a.get("text_length", 0) or len(text)

        if not text and tlen == 0:
            empty_texts += 1
            continue
        if tlen < 50:
            very_short += 1

        # Hash first 500 chars of text for duplicate detection
        text_sample = text[:500] if text else ""
        if text_sample:
            th = hashlib.md5(text_sample.encode("utf-8", errors="ignore")).hexdigest()[:12]
            if th not in text_hashes:
                text_hashes[th] = []
                text_samples[th] = (text[:300], tlen)
            text_hashes[th].append({"url": a.get("url", ""), "title": title, "date": a.get("date", "")})

        if title:
            title_counts[title] += 1

    # Find duplicate groups (same text appearing 3+ times)
    dup_groups = []
    total_duplicates = 0
    for th, group in sorted(text_hashes.items(), key=lambda x: -len(x[1])):
        if len(group) < 3:
            break
        total_duplicates += len(group) - 1
        text_preview, text_len = text_samples.get(th, ("", 0))
        dup_groups.append({
            "count": len(group),
            "sample_title": group[0]["title"],
            "sample_url": group[0]["url"],
            "text_preview": text_preview,
            "text_length": text_len,
            "examples": group[:5],
        })
        if len(dup_groups) >= 10:
            break

    # Duplicate titles (different text but same title, 3+)
    dup_titles = [(t, c) for t, c in title_counts.most_common(10) if c >= 3]

    # Content uniformity: check if many articles have very similar length
    lengths = [a.get("text_length", 0) or len(a.get("text", "")) for a in articles]
    length_mode = Counter(lengths).most_common(1)
    same_length_count = length_mode[0][1] if length_mode else 0
    same_length_pct = (same_length_count / len(articles) * 100) if articles else 0

    # Alerts
    alerts = []
    if total_duplicates > len(articles) * 0.1:
        alerts.append(f"High duplicate rate: {total_duplicates} duplicate articles ({total_duplicates/len(articles)*100:.0f}%)")
    if empty_texts > len(articles) * 0.05:
        alerts.append(f"{empty_texts} articles with empty text ({empty_texts/len(articles)*100:.0f}%)")
    if very_short > len(articles) * 0.15:
        alerts.append(f"{very_short} articles with very short text <50 chars ({very_short/len(articles)*100:.0f}%)")
    if same_length_pct > 20 and same_length_count > 10:
        alerts.append(f"{same_length_count} articles have identical text length ({length_mode[0][0]} chars) — possible template/boilerplate extraction")
    if dup_titles and dup_titles[0][1] > len(articles) * 0.05:
        alerts.append(f"Most repeated title appears {dup_titles[0][1]} times: \"{dup_titles[0][0][:60]}\"")

    return {
        "has_data": True,
        "total_articles": len(articles),
        "empty_texts": empty_texts,
        "very_short": very_short,
        "total_duplicates": total_duplicates,
        "dup_groups": dup_groups,
        "dup_titles": dup_titles,
        "same_length_count": same_length_count,
        "same_length_value": length_mode[0][0] if length_mode else 0,
        "alerts": alerts,
    }


# ── HTML templates ────────────────────────────────────────────────────────────

def h(text) -> str:
    """HTML escape."""
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


STYLE = """
:root { --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #e6edf3;
  --muted: #8b949e; --accent: #58a6ff; --green: #3fb950; --yellow: #d29922;
  --red: #f85149; --orange: #db6d28; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font: 14px/1.5 -apple-system, sans-serif; padding: 16px; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
table { border-collapse: collapse; width: 100%; }
th, td { padding: 6px 10px; text-align: left; border-bottom: 1px solid var(--border); white-space: nowrap; }
th { background: var(--card); position: sticky; top: 0; z-index: 1; font-weight: 600; cursor: pointer; user-select: none; }
th:hover { color: var(--accent); }
tr:hover { background: rgba(88,166,255,.06); }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
.stat-num { font-size: 28px; font-weight: 700; }
.stat-label { color: var(--muted); font-size: 12px; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.badge-complete { background: rgba(63,185,80,.15); color: var(--green); }
.badge-fetching { background: rgba(88,166,255,.15); color: var(--accent); }
.badge-tasks { background: rgba(210,153,34,.15); color: var(--yellow); }
.badge-discovery { background: rgba(219,109,40,.15); color: var(--orange); }
.badge-pending { background: rgba(139,148,158,.15); color: var(--muted); }
.badge-custom { background: rgba(210,153,34,.15); color: var(--yellow); }
.badge-base { background: rgba(139,148,158,.1); color: var(--muted); }
.bar { height: 6px; border-radius: 3px; background: var(--border); overflow: hidden; min-width: 60px; }
.bar-fill { height: 100%; border-radius: 3px; }
.filter-bar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.filter-bar input, .filter-bar select { background: var(--card); color: var(--text); border: 1px solid var(--border);
  border-radius: 6px; padding: 6px 10px; font-size: 14px; }
.filter-bar input { width: 220px; }
h1 { font-size: 22px; margin-bottom: 4px; }
h2 { font-size: 18px; margin-bottom: 12px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.rec { background: rgba(210,153,34,.1); border-left: 3px solid var(--yellow); padding: 8px 12px; margin: 4px 0; border-radius: 4px; }
.truncate { max-width: 300px; overflow: hidden; text-overflow: ellipsis; }
.year-chart { display: flex; align-items: flex-end; gap: 2px; height: 60px; }
.year-bar { background: var(--accent); border-radius: 2px 2px 0 0; min-width: 8px; position: relative; }
.year-bar:hover::after { content: attr(title); position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%);
  background: var(--card); border: 1px solid var(--border); padding: 2px 6px; border-radius: 4px; font-size: 11px; white-space: nowrap; }
.search-box { margin: 16px 0; display: flex; gap: 8px; }
.search-box input { flex: 1; background: var(--card); color: var(--text); border: 1px solid var(--border);
  border-radius: 6px; padding: 8px 12px; font-size: 14px; }
.search-box button { background: var(--accent); color: #fff; border: none; border-radius: 6px; padding: 8px 16px;
  cursor: pointer; font-weight: 600; }
.tag { display: inline-block; margin: 2px; padding: 1px 6px; border-radius: 4px; background: var(--border); font-size: 12px; }
code { background: var(--border); padding: 1px 4px; border-radius: 3px; font-size: 13px; }
.logo-sm { width: 20px; height: 20px; object-fit: contain; border-radius: 3px; vertical-align: middle; }
.logo-lg { width: 64px; height: 64px; object-fit: contain; border-radius: 8px; background: var(--border); padding: 4px; }
.logo-placeholder { width: 20px; height: 20px; display: inline-block; background: var(--border); border-radius: 3px; vertical-align: middle; }
.btn-wrong-logo { background: var(--red); color: #fff; border: none; border-radius: 6px; padding: 4px 10px;
  cursor: pointer; font-size: 12px; font-weight: 600; margin-left: 8px; }
.btn-wrong-logo:hover { opacity: 0.8; }
.nav-tabs { display: flex; gap: 4px; margin-bottom: 16px; }
.nav-tab { padding: 8px 16px; border-radius: 6px 6px 0 0; background: var(--card); color: var(--muted); border: 1px solid var(--border);
  border-bottom: none; cursor: pointer; font-weight: 600; text-decoration: none; }
.nav-tab:hover { color: var(--text); text-decoration: none; }
.nav-tab.active { background: var(--bg); color: var(--accent); border-bottom: 2px solid var(--accent); }
.alert-box { background: rgba(248,81,73,.1); border-left: 3px solid var(--red); padding: 8px 12px; margin: 4px 0; border-radius: 4px; }
.dup-group { background: rgba(210,153,34,.05); border: 1px solid var(--border); border-radius: 6px; padding: 10px; margin: 6px 0; }
.badge-TODO { background: rgba(139,148,158,.15); color: var(--muted); }
.badge-GOOD { background: rgba(63,185,80,.15); color: var(--green); }
.badge-BAD { background: rgba(248,81,73,.15); color: var(--red); }
.review-bar { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; }
.btn-review { border: none; border-radius: 6px; padding: 10px 24px; cursor: pointer; font-size: 15px; font-weight: 700; }
.btn-review-good { background: var(--green); color: #fff; }
.btn-review-good:hover { opacity: 0.85; }
.btn-review-bad { background: var(--red); color: #fff; }
.btn-review-bad:hover { opacity: 0.85; }
.btn-review-todo { background: var(--border); color: var(--text); }
.btn-review-todo:hover { opacity: 0.85; }
.text-preview { max-width: 350px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; color: var(--muted); cursor: help; }
"""

JS_TABLE_SORT = """
document.querySelectorAll('th[data-sort]').forEach(th => {
  th.addEventListener('click', () => {
    const table = th.closest('table');
    const tbody = table.querySelector('tbody');
    const idx = Array.from(th.parentNode.children).indexOf(th);
    const type = th.dataset.sort;
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const dir = th.dataset.dir === 'asc' ? 'desc' : 'asc';
    th.parentNode.querySelectorAll('th').forEach(t => delete t.dataset.dir);
    th.dataset.dir = dir;
    rows.sort((a, b) => {
      let va = a.children[idx]?.dataset.v ?? a.children[idx]?.textContent ?? '';
      let vb = b.children[idx]?.dataset.v ?? b.children[idx]?.textContent ?? '';
      if (type === 'num') { va = parseFloat(va) || 0; vb = parseFloat(vb) || 0; }
      else { va = va.toLowerCase(); vb = vb.toLowerCase(); }
      return dir === 'asc' ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
    });
    rows.forEach(r => tbody.appendChild(r));
  });
});
"""

JS_FILTER = """
const filterInput = document.getElementById('filter');
const phaseSelect = document.getElementById('phase-filter');
const customSelect = document.getElementById('custom-filter');
const reviewSelect = document.getElementById('review-filter');
function applyFilters() {
  const q = filterInput.value.toLowerCase();
  const ph = phaseSelect.value;
  const cu = customSelect.value;
  const rv = reviewSelect.value;
  document.querySelectorAll('tbody tr').forEach(r => {
    const domain = (r.children[0]?.textContent || '').toLowerCase();
    const phase = r.dataset.phase || '';
    const custom = r.dataset.custom || '';
    const review = r.dataset.review || '';
    const matchText = !q || domain.includes(q);
    const matchPhase = !ph || phase === ph;
    const matchCustom = !cu || (cu === 'custom' ? custom === '1' : custom === '0');
    const matchReview = !rv || review === rv;
    r.style.display = (matchText && matchPhase && matchCustom && matchReview) ? '' : 'none';
  });
}
filterInput.addEventListener('input', applyFilters);
phaseSelect.addEventListener('change', applyFilters);
customSelect.addEventListener('change', applyFilters);
reviewSelect.addEventListener('change', applyFilters);
"""


def render_index(sites: list[dict]) -> str:
    # Summary stats
    total = len(sites)
    with_articles = sum(1 for s in sites if s["articles"] > 0)
    total_articles = sum(s["articles"] for s in sites)
    total_errors = sum(s["errors"] for s in sites)
    phases = Counter(s["phase"] for s in sites)
    reviews = Counter(s.get("review", "TODO") for s in sites)

    rows_html = []
    for s in sites:
        pclass = f"badge-{s['phase']}"
        ok_bar_color = "var(--green)" if s["ok_pct"] >= 80 else "var(--yellow)" if s["ok_pct"] >= 50 else "var(--red)"
        ok_bar = f'<div class="bar"><div class="bar-fill" style="width:{s["ok_pct"]:.0f}%;background:{ok_bar_color}"></div></div>' if (s["articles"] + s["errors"]) > 0 else '<span style="color:var(--muted)">—</span>'
        custom_badge = '<span class="badge badge-custom">custom</span>' if s["has_custom"] else '<span class="badge badge-base">base</span>'

        tasks_str = f'{s["tasks"]:,}' if s["tasks"] > 0 else "—"
        if s["tasks"] > 0:
            tl, ta, tw = s["tasks_live"], s["tasks_arquivo"], s["tasks_wayback"]
            tasks_title = f"L:{tl:,} A:{ta:,} W:{tw:,}"
            # Show progress if fetching
            if s["phase"] == "fetching":
                done = s["articles"] + s["errors"]
                pct = done / s["tasks"] * 100 if s["tasks"] else 0
                tasks_str = f'<span title="{tasks_title}">{done:,}/{s["tasks"]:,} ({pct:.0f}%)</span>'
            else:
                tasks_str = f'<span title="{tasks_title}">{s["tasks"]:,}</span>'

        review = s.get("review", "TODO")
        review_badge = f'<span class="badge badge-{review}">{review}</span>'

        encoded_domain = urllib.parse.quote(s["domain"], safe="")
        logo_html = f'<img class="logo-sm" src="/logo?d={encoded_domain}" alt="" loading="lazy">' if s["has_logo"] else '<span class="logo-placeholder"></span>'
        rows_html.append(
            f'<tr data-phase="{h(s["phase"])}" data-custom="{"1" if s["has_custom"] else "0"}" data-review="{h(review)}">'
            f'<td>{logo_html} <a href="/site?d={encoded_domain}">{h(s["domain"])}</a></td>'
            f'<td>{h(s["name"])}</td>'
            f'<td><code>{h(s["disc"] or "···")}</code></td>'
            f'<td><span class="badge {pclass}">{h(s["phase"])}</span></td>'
            f'<td data-v="{s["articles"]}">{s["articles"]:,}</td>'
            f'<td data-v="{s["errors"]}">{s["errors"]:,}</td>'
            f'<td data-v="{s["ok_pct"]:.1f}">{ok_bar}</td>'
            f'<td>{tasks_str}</td>'
            f'<td>{custom_badge}</td>'
            f'<td>{review_badge}</td>'
            f'</tr>'
        )

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>QC Dashboard</title>
<style>{STYLE}</style></head><body>
<div class="header"><h1>📰 Arquivo-26 Quality Control</h1>
<span style="color:var(--muted)">{total} sites · {with_articles} with articles · {total_articles:,} articles total</span></div>

<div class="nav-tabs">
  <a class="nav-tab active" href="/">Sites</a>
  <a class="nav-tab" href="/search">Search All</a>
</div>

<div class="grid" style="margin-bottom:16px">
  <div class="card"><div class="stat-num" style="color:var(--green)">{phases.get("complete",0)}</div><div class="stat-label">Complete</div></div>
  <div class="card"><div class="stat-num" style="color:var(--accent)">{phases.get("fetching",0)}</div><div class="stat-label">Fetching</div></div>
  <div class="card"><div class="stat-num" style="color:var(--yellow)">{phases.get("tasks",0)}</div><div class="stat-label">Tasks Ready</div></div>
  <div class="card"><div class="stat-num" style="color:var(--orange)">{phases.get("discovery",0)}</div><div class="stat-label">Discovery</div></div>
  <div class="card"><div class="stat-num" style="color:var(--muted)">{phases.get("pending",0)}</div><div class="stat-label">Pending</div></div>
  <div class="card"><div class="stat-num" style="color:var(--red)">{total_errors:,}</div><div class="stat-label">Total Errors</div></div>
  <div class="card"><div class="stat-num" style="color:var(--green)">{reviews.get("GOOD",0)}</div><div class="stat-label">Reviewed GOOD</div></div>
  <div class="card"><div class="stat-num" style="color:var(--red)">{reviews.get("BAD",0)}</div><div class="stat-label">Reviewed BAD</div></div>
  <div class="card"><div class="stat-num" style="color:var(--muted)">{reviews.get("TODO",0)}</div><div class="stat-label">TODO</div></div>
</div>

<div class="filter-bar">
  <input id="filter" placeholder="Filter by domain..." autofocus>
  <select id="phase-filter"><option value="">All phases</option>
    <option value="complete">Complete</option><option value="fetching">Fetching</option>
    <option value="tasks">Tasks</option><option value="discovery">Discovery</option>
    <option value="pending">Pending</option></select>
  <select id="custom-filter"><option value="">All handlers</option>
    <option value="custom">Custom only</option><option value="base">Base only</option></select>
  <select id="review-filter"><option value="">All reviews</option>
    <option value="TODO">TODO</option><option value="GOOD">GOOD</option><option value="BAD">BAD</option></select>
</div>

<table>
<thead><tr>
  <th data-sort="text">Domain</th><th data-sort="text">Name</th><th data-sort="text">Disc</th>
  <th data-sort="text">Phase</th><th data-sort="num">Articles</th><th data-sort="num">Errors</th>
  <th data-sort="num">OK%</th><th data-sort="num">Tasks</th><th data-sort="text">Handler</th><th data-sort="text">Review</th>
</tr></thead>
<tbody>{"".join(rows_html)}</tbody>
</table>

<script>{JS_TABLE_SORT}{JS_FILTER}</script>
</body></html>"""


def render_site(detail: dict) -> str:
    dk = detail["domain"]
    encoded = urllib.parse.quote(dk, safe="")
    state = detail["state"]

    # Year chart
    yd = detail["year_distribution"]
    year_chart = ""
    if yd:
        max_count = max(yd.values())
        bars = []
        for y, c in sorted(yd.items()):
            pct = (c / max_count * 100) if max_count > 0 else 0
            bars.append(f'<div class="year-bar" style="width:12px;height:{max(2,pct)}%" title="{y}: {c:,}"></div>')
        min_y = min(yd.keys())
        max_y = max(yd.keys())
        year_chart = f'<div class="card"><h2>Articles by Year ({min_y}–{max_y})</h2><div class="year-chart">{"".join(bars)}</div></div>'

    # Failure reasons
    reasons_html = ""
    if detail["failure_reasons"]:
        items = "".join(f'<tr><td>{h(r)}</td><td>{c:,}</td></tr>' for r, c in detail["failure_reasons"].items())
        reasons_html = f'<div class="card"><h2>Failure Reasons</h2><table><thead><tr><th>Reason</th><th>Count</th></tr></thead><tbody>{items}</tbody></table></div>'

    # Field completeness
    fields_html = ""
    if detail["field_completeness"]:
        items = ""
        for f, p in detail["field_completeness"].items():
            color = "var(--green)" if p >= 80 else "var(--yellow)" if p >= 50 else "var(--red)"
            items += f'<tr><td>{h(f)}</td><td><div class="bar" style="min-width:120px"><div class="bar-fill" style="width:{p}%;background:{color}"></div></div></td><td>{p:.1f}%</td></tr>'
        fields_html = f'<div class="card"><h2>Field Completeness</h2><table><tbody>{items}</tbody></table></div>'

    # Recs
    recs_html = ""
    if detail["recommendations"]:
        recs_html = '<div class="card"><h2>Recommendations</h2>' + "".join(f'<div class="rec">{h(r)}</div>' for r in detail["recommendations"]) + "</div>"

    # Source / extractor
    src_html = " ".join(f'<span class="tag">{h(s)}: {c}</span>' for s, c in detail["source_counts"].items())
    ext_html = " ".join(f'<span class="tag">{h(e)}: {c}</span>' for e, c in detail["extractor_counts"].items())

    # Text length
    tl = detail["text_length"]
    tl_html = ""
    if tl:
        tl_html = f'<div class="card"><h2>Text Length</h2><div class="grid"><div><div class="stat-num">{tl["median"]}</div><div class="stat-label">Median</div></div><div><div class="stat-num">{tl["p10"]}</div><div class="stat-label">P10</div></div><div><div class="stat-num">{tl["p90"]}</div><div class="stat-label">P90</div></div><div><div class="stat-num" style="color:var(--red)">{tl.get("short",0)}</div><div class="stat-label">&lt;100 chars</div></div></div></div>'

    # URL prefix map
    prefix_html = ""
    pm = detail["prefix_map"]
    if pm:
        items = "".join(f'<tr><td><code>{h(k)}</code></td><td>{v:,}</td></tr>' for k, v in sorted(pm.items(), key=lambda x: -x[1])[:15])
        prefix_html = f'<div class="card"><h2>URL Prefixes (from discovery)</h2><table><thead><tr><th>Prefix</th><th>Count</th></tr></thead><tbody>{items}</tbody></table></div>'

    # Sample articles
    sample_rows = ""
    for a in detail["samples"]:
        archive_link = ""
        if a.get("archive_url"):
            viewer_url = a["archive_url"].replace("/id_/", "/")
            archive_link = f' <a href="{h(viewer_url)}" target="_blank" title="View archived page">🗄️</a>'
        text_prev = h(a.get("text_preview", ""))
        full_title = h(a.get("text_preview", ""))
        author_str = h(a.get("author", ""))
        agency_str = h(a.get("agency", ""))
        sample_rows += f'<tr><td class="truncate"><a href="{h(a["url"])}" target="_blank">{h(a["title"] or a["url"][:60])}</a>{archive_link}</td><td>{h(a["date"])}</td><td>{h(a["source"])}</td><td>{a["text_length"]}</td><td>{author_str}</td><td>{agency_str}</td><td class="text-preview" title="{full_title}">{text_prev}</td></tr>'
    samples_html = f'<div class="card"><h2>Recent Articles (sample)</h2><table><thead><tr><th>Title</th><th>Date</th><th>Source</th><th>Length</th><th>Author</th><th>Agency</th><th>Text</th></tr></thead><tbody>{sample_rows}</tbody></table></div>' if sample_rows else ""

    # State info
    state_items = ""
    for k in ("arquivo_cdx_done", "wayback_cdx_done", "sitemap_done", "arquivo_cdx_count", "wayback_cdx_count", "sitemap_count", "total_unique_articles"):
        if k in state:
            state_items += f"<tr><td><code>{h(k)}</code></td><td>{h(state[k])}</td></tr>"

    oldest = state.get("oldest_cdx", {})
    oldest_html = ""
    if oldest:
        for src, info in oldest.items():
            ts = info.get("timestamp", "")
            if len(ts) >= 8:
                date_str = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
            else:
                date_str = ts
            oldest_html += f'<span class="tag">{h(src)}: {date_str}</span> '

    total = detail["articles_count"] + detail["errors_count"]
    ok_pct = (detail["articles_count"] / total * 100) if total > 0 else 0

    # Logo HTML
    logo_header = ""
    if detail["has_logo"]:
        logo_header = f'<img class="logo-lg" src="/logo?d={encoded}" alt="logo">'
        logo_header += f'<button class="btn-wrong-logo" onclick="markWrongLogo(\'{encoded}\')">Wrong logo</button>'
    elif detail["logo_wrong"]:
        logo_header = '<span style="color:var(--muted);font-size:12px">Logo marked as wrong</span>'

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>QC: {h(dk)}</title>
<style>{STYLE}</style></head><body>
<div class="header"><div style="display:flex;align-items:center;gap:12px"><a href="/">← Back</a>{logo_header}<h1>{h(dk)}</h1></div></div>

<div class="grid">
  <div class="card"><div class="stat-num">{detail["articles_count"]:,}</div><div class="stat-label">Articles</div></div>
  <div class="card"><div class="stat-num" style="color:var(--red)">{detail["errors_count"]:,}</div><div class="stat-label">Errors</div></div>
  <div class="card"><div class="stat-num">{ok_pct:.0f}%</div><div class="stat-label">Success Rate</div></div>
  <div class="card"><div class="stat-num">{detail["tasks_count"]:,}</div><div class="stat-label">Tasks</div>
    <div style="font-size:11px;color:var(--muted);margin-top:4px">L:{detail["tasks_live"]:,} &middot; A:{detail["tasks_arquivo"]:,} &middot; W:{detail["tasks_wayback"]:,}</div></div>
</div>

{recs_html}

<div class="card"><h2>Sources & Extractors</h2><div>Sources: {src_html}</div><div style="margin-top:6px">Extractors: {ext_html}</div>
{f'<div style="margin-top:6px">Oldest captures: {oldest_html}</div>' if oldest_html else ''}</div>

<div class="card"><h2>State</h2><table><tbody>{state_items}</tbody></table></div>

{tl_html}
{fields_html}
{year_chart}
{reasons_html}
{prefix_html}

<div class="card" id="review-section">
<h2>Review</h2>
<div class="review-bar">
  <span style="color:var(--muted)">Current: <span class="badge badge-{h(detail['review'])}">{h(detail['review'])}</span></span>
  <button class="btn-review btn-review-good" onclick="setReview('GOOD')">MARK AS GOOD</button>
  <button class="btn-review btn-review-bad" onclick="setReview('BAD')">MARK AS BAD</button>
  <button class="btn-review btn-review-todo" onclick="setReview('TODO')">Reset to TODO</button>
</div>
</div>

<div class="card"><h2>Search Articles & Errors</h2>
<div class="search-box">
  <input id="sq" placeholder="Search by URL or title..." onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
</div>
<div id="search-results"></div>
</div>

{samples_html}

<div class="card" id="quality-analysis">
<h2>Quality Analysis</h2>
<div id="qa-content"><button onclick="loadQA()" style="background:var(--accent);color:#fff;border:none;border-radius:6px;padding:8px 16px;cursor:pointer;font-weight:600">Load Analysis</button></div>
</div>

<script>
function markWrongLogo(domain) {{
  if (!confirm('Mark this logo as wrong? It will be deleted.')) return;
  fetch('/api/mark-wrong-logo', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{domain:domain}}) }})
    .then(r => r.json())
    .then(data => {{ if(data.ok) location.reload(); else alert(data.error || 'Failed'); }});
}}
function setReview(state) {{
  fetch('/api/set-review', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{domain:'{encoded}', review: state}}) }})
    .then(r => r.json())
    .then(data => {{
      if (!data.ok) {{ alert(data.error || 'Failed'); return; }}
      if (data.next_todo) {{
        window.location.href = '/site?d=' + encodeURIComponent(data.next_todo);
      }} else {{
        window.location.href = '/';
      }}
    }});
}}
function loadQA() {{
  document.getElementById('qa-content').innerHTML = '<p style="color:var(--muted)">Analyzing...</p>';
  fetch('/api/quality?d={encoded}')
    .then(r => r.json())
    .then(data => {{
      const el = document.getElementById('qa-content');
      if (!data.has_data) {{ el.innerHTML = '<p style="color:var(--muted)">No articles to analyze</p>'; return; }}
      let html = '';
      if (data.alerts && data.alerts.length) {{
        html += data.alerts.map(a => '<div class="alert-box">' + a + '</div>').join('');
      }} else {{
        html += '<p style="color:var(--green)">No quality issues detected</p>';
      }}
      html += '<div class="grid" style="margin-top:12px">';
      html += '<div><div class="stat-num">' + data.total_duplicates + '</div><div class="stat-label">Duplicate Articles</div></div>';
      html += '<div><div class="stat-num">' + data.empty_texts + '</div><div class="stat-label">Empty Texts</div></div>';
      html += '<div><div class="stat-num">' + data.very_short + '</div><div class="stat-label">Very Short (&lt;50)</div></div>';
      html += '</div>';
      if (data.dup_groups && data.dup_groups.length) {{
        html += '<h3 style="margin-top:16px;margin-bottom:8px">Duplicate Text Groups</h3>';
        data.dup_groups.forEach(g => {{
          html += '<div class="dup-group"><strong>' + g.count + '× same text</strong> (' + g.text_length + ' chars): ' + (g.sample_title || g.sample_url).substring(0,80);
          if (g.text_preview) {{
            const escaped = g.text_preview.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
            html += '<div style="margin-top:6px;padding:8px;background:var(--bg);border-radius:4px;font-size:12px;color:var(--text);white-space:pre-wrap;max-height:120px;overflow-y:auto;border:1px solid var(--border)">' + escaped + '</div>';
          }}
          html += '<div style="margin-top:4px;font-size:12px;color:var(--muted)">';
          g.examples.forEach(e => {{ html += '<div>' + (e.date || '') + ' — <a href="' + e.url + '" target="_blank">' + (e.title || e.url).substring(0,60) + '</a></div>'; }});
          html += '</div></div>';
        }});
      }}
      if (data.dup_titles && data.dup_titles.length) {{
        html += '<h3 style="margin-top:16px;margin-bottom:8px">Repeated Titles</h3><table><thead><tr><th>Title</th><th>Count</th></tr></thead><tbody>';
        data.dup_titles.forEach(d => {{ html += '<tr><td>' + d[0].substring(0,80) + '</td><td>' + d[1] + '</td></tr>'; }});
        html += '</tbody></table>';
      }}
      el.innerHTML = html;
    }});
}}
function doSearch() {{
  const q = document.getElementById('sq').value;
  if (!q) return;
  fetch('/api/search?d={encoded}&q=' + encodeURIComponent(q))
    .then(r => r.json())
    .then(data => {{
      const el = document.getElementById('search-results');
      if (!data.length) {{ el.innerHTML = '<p style="color:var(--muted)">No results</p>'; return; }}
      let html = '<table><thead><tr><th>Type</th><th>URL</th><th>Date</th><th>Source</th><th>Length</th><th>Reason</th></tr></thead><tbody>';
      data.forEach(r => {{
        const color = r.kind === 'error' ? 'var(--red)' : '';
        const archiveLink = r.archive_url ? ` <a href="${{r.archive_url.replace('/id_/', '/')}}" target="_blank">🗄️</a>` : '';
        html += `<tr style="color:${{color}}"><td>${{r.kind}}</td><td class="truncate"><a href="${{r.url}}" target="_blank">${{(r.title || r.url).substring(0,60)}}</a>${{archiveLink}}</td><td>${{r.date||''}}</td><td>${{r.source||''}}</td><td>${{r.text_length||''}}</td><td>${{r.reason||''}}</td></tr>`;
      }});
      html += '</tbody></table>';
      el.innerHTML = html;
    }});
}}
{JS_TABLE_SORT}
</script>
</body></html>"""


# ── HTTP Server ───────────────────────────────────────────────────────────────

def render_search_page() -> str:
    """Render the cross-site search page."""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>QC: Search All Sites</title>
<style>{STYLE}</style></head><body>
<div class="header"><h1>📰 Arquivo-26 Quality Control</h1></div>

<div class="nav-tabs">
  <a class="nav-tab" href="/">Sites</a>
  <a class="nav-tab active" href="/search">Search All</a>
</div>

<div class="card">
<h2>Search Across All Sites</h2>
<div class="search-box">
  <input id="gsq" placeholder="Search by URL, title, or text snippet..." autofocus onkeydown="if(event.key==='Enter')globalSearch()">
  <button onclick="globalSearch()">Search</button>
</div>
<p style="color:var(--muted);font-size:12px;margin-top:6px">Searches articles across all sites. Max 100 results.</p>
<div id="gs-results"></div>
</div>

<script>
function globalSearch() {{
  const q = document.getElementById('gsq').value.trim();
  if (!q) return;
  document.getElementById('gs-results').innerHTML = '<p style="color:var(--muted)">Searching…</p>';
  fetch('/api/search-all?q=' + encodeURIComponent(q))
    .then(r => r.json())
    .then(data => {{
      const el = document.getElementById('gs-results');
      if (!data.length) {{ el.innerHTML = '<p style="color:var(--muted)">No results</p>'; return; }}
      let html = '<p style="color:var(--muted);margin:8px 0">' + data.length + ' results</p>';
      html += '<table><thead><tr><th>Site</th><th>Title</th><th>Date</th><th>Source</th><th>Length</th></tr></thead><tbody>';
      data.forEach(r => {{
        const archiveLink = r.archive_url ? ' <a href="' + r.archive_url.replace('/id_/', '/') + '" target="_blank">🗄️</a>' : '';
        const siteLink = '/site?d=' + encodeURIComponent(r.domain);
        html += '<tr><td><a href="' + siteLink + '">' + r.domain + '</a></td><td class="truncate"><a href="' + r.url + '" target="_blank">' + ((r.title || r.url).substring(0,60)) + '</a>' + archiveLink + '</td><td>' + (r.date||'') + '</td><td>' + (r.source||'') + '</td><td>' + (r.text_length||'') + '</td></tr>';
      }});
      html += '</tbody></table>';
      el.innerHTML = html;
    }});
}}
</script>
</body></html>"""


def serve_logo(dk: str) -> tuple[bytes, str] | None:
    """Return (data, content_type) for a site's logo, or None."""
    ddir = DATA_DIR / dk
    state = load_state(ddir)
    if state.get("logo_wrong"):
        return None
    logo_file = state.get("logo_file", "")
    if not logo_file:
        return None
    logo_path = ddir / logo_file
    if not logo_path.exists():
        return None
    ct, _ = mimetypes.guess_type(logo_path.name)
    return logo_path.read_bytes(), ct or "image/png"


def mark_wrong_logo(dk: str) -> dict:
    """Mark a logo as wrong: delete file, set flag in state.json."""
    ddir = DATA_DIR / dk
    # Validate path
    target = ddir.resolve()
    if not str(target).startswith(str(DATA_DIR.resolve())):
        return {"ok": False, "error": "Invalid domain"}
    state_path = ddir / "state.json"
    if not state_path.exists():
        return {"ok": False, "error": "No state.json"}
    state = json.loads(state_path.read_text(encoding="utf-8"))
    logo_file = state.get("logo_file", "")
    if logo_file:
        logo_path = ddir / logo_file
        if logo_path.exists():
            logo_path.unlink()
    state["logo_wrong"] = True
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    # Clear cache so index refreshes
    global _sites_cache
    _sites_cache = None
    return {"ok": True}


def set_review_state(dk: str, review: str) -> dict:
    """Set review state (TODO/GOOD/BAD) and return next TODO domain."""
    ddir = DATA_DIR / dk
    target = ddir.resolve()
    if not str(target).startswith(str(DATA_DIR.resolve())):
        return {"ok": False, "error": "Invalid domain"}
    state_path = ddir / "state.json"
    if not state_path.exists():
        return {"ok": False, "error": "No state.json"}
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["review_state"] = review
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    # Clear cache
    global _sites_cache
    _sites_cache = None
    # Find next TODO site (sorted same as index: complete first, then by articles desc)
    sites = gather_sites()
    phase_order = {"complete": 0, "fetching": 1, "tasks": 2, "discovery": 3, "pending": 4}
    sites.sort(key=lambda s: (phase_order.get(s["phase"], 9), -s["articles"]))
    next_todo = None
    found_current = False
    for s in sites:
        if s["domain"] == dk:
            found_current = True
            continue
        if found_current and s.get("review", "TODO") == "TODO":
            next_todo = s["domain"]
            break
    # If we didn't find one after current, wrap around from the start
    if not next_todo:
        for s in sites:
            if s["domain"] == dk:
                break
            if s.get("review", "TODO") == "TODO":
                next_todo = s["domain"]
                break
    return {"ok": True, "next_todo": next_todo}


class QCHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        try:
            if path == "/" or path == "":
                sites = gather_sites()
                # Sort: complete first, then by articles desc
                phase_order = {"complete": 0, "fetching": 1, "tasks": 2, "discovery": 3, "pending": 4}
                sites.sort(key=lambda s: (phase_order.get(s["phase"], 9), -s["articles"]))
                self._html(render_index(sites))

            elif path == "/site":
                dk = params.get("d", [""])[0]
                if not dk:
                    self._redirect("/")
                    return
                # Validate the domain key points to real directory
                target = (DATA_DIR / dk).resolve()
                if not str(target).startswith(str(DATA_DIR.resolve())):
                    self._error(403, "Forbidden")
                    return
                if not target.is_dir():
                    self._error(404, f"No data for {dk}")
                    return
                detail = site_detail(dk)
                self._html(render_site(detail))

            elif path == "/search":
                self._html(render_search_page())

            elif path == "/logo":
                dk = params.get("d", [""])[0]
                if not dk:
                    self._error(404, "No domain")
                    return
                target = (DATA_DIR / dk).resolve()
                if not str(target).startswith(str(DATA_DIR.resolve())):
                    self._error(403, "Forbidden")
                    return
                result = serve_logo(dk)
                if result:
                    data, ct = result
                    self.send_response(200)
                    self.send_header("Content-Type", ct)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "public, max-age=3600")
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self._error(404, "No logo")

            elif path == "/api/search":
                dk = params.get("d", [""])[0]
                q = params.get("q", [""])[0]
                if not dk or not q:
                    self._json([])
                    return
                target = (DATA_DIR / dk).resolve()
                if not str(target).startswith(str(DATA_DIR.resolve())):
                    self._json([])
                    return
                results = search_articles(dk, q)
                self._json(results)

            elif path == "/api/search-all":
                q = params.get("q", [""])[0]
                if not q:
                    self._json([])
                    return
                results = search_all_sites(q)
                self._json(results)

            elif path == "/api/quality":
                dk = params.get("d", [""])[0]
                if not dk:
                    self._json({"has_data": False})
                    return
                target = (DATA_DIR / dk).resolve()
                if not str(target).startswith(str(DATA_DIR.resolve())):
                    self._json({"has_data": False})
                    return
                result = quality_analysis(dk)
                self._json(result)

            else:
                self._error(404, "Not found")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self._error(500, str(e))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length else b""

            if path == "/api/mark-wrong-logo":
                data = json.loads(body) if body else {}
                dk = data.get("domain", "")
                if not dk:
                    self._json({"ok": False, "error": "No domain"})
                    return
                dk = urllib.parse.unquote(dk)
                result = mark_wrong_logo(dk)
                self._json(result)
            elif path == "/api/set-review":
                data = json.loads(body) if body else {}
                dk = data.get("domain", "")
                review = data.get("review", "")
                if not dk or review not in ("TODO", "GOOD", "BAD"):
                    self._json({"ok": False, "error": "Invalid params"})
                    return
                dk = urllib.parse.unquote(dk)
                result = set_review_state(dk, review)
                self._json(result)
            else:
                self._error(404, "Not found")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._error(500, str(e))

    def _html(self, content: str):
        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, url: str):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def _error(self, code: int, msg: str):
        data = f"<h1>{code}</h1><p>{h(msg)}</p>".encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass  # Silence request logs


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), QCHandler)
    print(f"QC Dashboard running at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
        server.server_close()
