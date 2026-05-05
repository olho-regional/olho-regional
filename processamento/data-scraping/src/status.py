from collections import Counter
from pathlib import Path
import csv

from rich.console import Console
from rich.table import Table

from .stats import compute_stats
from .storage import count_lines, load_state, read_jsonl
from .utils import parse_jornais_csv, _BASE_DIR

console = Console()


def show_status(config: dict, site: str | None = None):
    """Show collection status for all sites or a specific site."""
    output_dir = Path(config.get("output_dir", "data"))
    sites = parse_jornais_csv()

    if site:
        # Detailed status for one site
        _show_site_detail(output_dir, site)
        return

    rows = _gather_status_rows(output_dir, sites)
    _print_status_table(rows, sites, output_dir)
    _write_status_csv(rows)


def _gather_status_rows(output_dir: Path, sites: list[dict]) -> list[dict]:
    """Gather status data for all sites."""
    rows = []
    for site_row in sites:
        url = site_row.get("url", "")
        domain = url.replace("https://", "").replace("http://", "").rstrip("/")
        if domain.startswith("www."):
            domain = domain[4:]

        data_dir = output_dir / domain
        if not data_dir.exists():
            rows.append({"domain": domain, "disc": "", "articles": 0,
                         "tasks_live": 0, "tasks_arquivo": 0, "tasks_wayback": 0,
                         "errors": 0, "ok_pct": 0.0, "exists": False})
            continue

        state = load_state(data_dir)

        disc_parts = []
        disc_parts.append("C" if state.get("arquivo_cdx_done") else "")
        disc_parts.append("W" if state.get("wayback_cdx_done") else "")
        disc_parts.append("S" if state.get("sitemap_done") else "")
        disc_str = "".join(disc_parts)

        articles_count = count_lines(data_dir / "articles.jsonl")
        task_counts = _count_by_source(data_dir / "tasks.jsonl")
        errors_count = count_lines(data_dir / "quality.jsonl")
        total = articles_count + errors_count
        ok_pct = (articles_count / total * 100) if total > 0 else 0.0

        # Determine phase
        has_tasks = (data_dir / "tasks.jsonl").exists() and count_lines(data_dir / "tasks.jsonl") > 0
        total_tasks_count = sum(task_counts.values())
        if articles_count > 0 and total_tasks_count > 0 and total >= total_tasks_count:
            phase = "complete"
        elif articles_count > 0:
            phase = "fetching"
        elif has_tasks:
            phase = "tasks"
        elif state.get("arquivo_cdx_done") or state.get("wayback_cdx_done") or state.get("sitemap_done"):
            phase = "discovery"
        else:
            phase = "pending"

        rows.append({
            "domain": domain,
            "disc": disc_str,
            "articles": articles_count,
            "tasks_live": task_counts.get("live", 0),
            "tasks_arquivo": task_counts.get("arquivo", 0),
            "tasks_wayback": task_counts.get("wayback", 0),
            "errors": errors_count,
            "ok_pct": ok_pct,
            "exists": True,
            "sparkline": _year_sparkline(data_dir / "articles.jsonl"),
            "phase": phase,
        })
    return rows


def _print_status_table(rows: list[dict], sites: list[dict], output_dir: Path):
    """Print the rich status table."""
    table = Table(title="Collection Status", expand=False, width=110)
    table.add_column("Site", style="bold", no_wrap=True, max_width=28)
    table.add_column("Disc", justify="center", no_wrap=True)
    table.add_column("Done", justify="right", no_wrap=True)
    table.add_column("Years", no_wrap=True, max_width=18)
    table.add_column("Tasks L/A/W", justify="center", no_wrap=True)
    table.add_column("Err", justify="right", no_wrap=True)
    table.add_column("OK%", justify="right", no_wrap=True)

    total_articles = 0
    for r in rows:
        display_name = r["domain"][:28]
        if not r["exists"]:
            table.add_row(display_name, "···", "-", "", "-", "-", "-")
            continue

        disc_display = r.get("disc", "").ljust(3).replace(" ", "·") if r.get("disc") else "···"
        articles_str = f"{r['articles']:,}" if r["articles"] > 0 else "-"
        total_tasks = r["tasks_live"] + r["tasks_arquivo"] + r["tasks_wayback"]
        if total_tasks > 0:
            task_str = f"{r['tasks_live']}/{r['tasks_arquivo']}/{r['tasks_wayback']}"
            if total_tasks < 1000:
                task_str = f"[yellow]{task_str}[/yellow]"
        else:
            task_str = "-"
        errors_str = f"{r['errors']:,}" if r["errors"] > 0 else "-"
        ok_str = f"{r['ok_pct']:.0f}%" if (r["articles"] + r["errors"]) > 0 else "-"

        total_articles += r["articles"]
        table.add_row(display_name, disc_display, articles_str, r.get("sparkline", ""), task_str, errors_str, ok_str)

    # Phase counts
    phase_counts = Counter(r.get("phase", "no data") for r in rows)
    no_data = sum(1 for r in rows if not r["exists"])
    phase_counts["no data"] = no_data

    collected = sum(1 for r in rows if r["exists"] and r["articles"] > 0)
    console.print(table)
    console.print(
        f"\nTotal: {collected}/{len(rows)} sites | {total_articles:,} articles\n"
        f"Phases: "
        f"[green]{phase_counts.get('complete', 0)}[/green] complete, "
        f"[cyan]{phase_counts.get('fetching', 0)}[/cyan] fetching, "
        f"[cyan]{phase_counts.get('tasks', 0)}[/cyan] tasks ready, "
        f"[yellow]{phase_counts.get('discovery', 0)}[/yellow] discovery, "
        f"[yellow]{phase_counts.get('pending', 0)}[/yellow] pending, "
        f"[dim]{no_data}[/dim] no data\n"
        "CDX: [bold]C[/bold]=arquivo [bold]W[/bold]=wayback [bold]S[/bold]=sitemap  "
        "Tasks: [bold]L[/bold]ive/[bold]A[/bold]rquivo/[bold]W[/bold]ayback"
    )


def _write_status_csv(rows: list[dict]):
    """Write status data to status-jornais.csv next to jornais.csv."""
    csv_path = _BASE_DIR / "status-jornais.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["domain", "discovery", "articles", "tasks_live", "tasks_arquivo",
                         "tasks_wayback", "tasks_total", "errors", "ok_pct"])
        for r in rows:
            total_tasks = r["tasks_live"] + r["tasks_arquivo"] + r["tasks_wayback"]
            writer.writerow([
                r["domain"],
                r["disc"],
                r["articles"],
                r["tasks_live"],
                r["tasks_arquivo"],
                r["tasks_wayback"],
                total_tasks,
                r["errors"],
                f"{r['ok_pct']:.1f}" if (r["articles"] + r["errors"]) > 0 else "",
            ])
    console.print(f"[dim]Wrote {csv_path}[/dim]")


def _show_site_detail(output_dir: Path, domain: str):
    """Show detailed stats for a single site."""
    data_dir = output_dir / domain
    if not data_dir.exists():
        console.print(f"[red]No data for {domain}[/red]")
        return

    articles = read_jsonl(data_dir / "articles.jsonl")
    quality = read_jsonl(data_dir / "quality.jsonl")
    state = load_state(data_dir)

    stats = compute_stats(articles, quality, state, domain)
    from .stats import print_stats
    print_stats(stats)


def _domain_from_site(site_row: dict) -> str:
    url = site_row.get("url", "")
    domain = url.replace("https://", "").replace("http://", "").rstrip("/")
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _human_count(n: int) -> str:
    if n >= 1000:
        return f"{n // 1000}k"
    return str(n)


def _count_by_source(path: Path) -> dict[str, int]:
    """Count articles by source without loading all into memory."""
    counts: dict[str, int] = Counter()
    if not path.exists():
        return counts
    import json
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    counts[json.loads(line).get("source", "unknown")] += 1
                except (json.JSONDecodeError, KeyError):
                    pass
    return counts


_SPARK_CHARS = " ▁▂▃▄▅▆▇█"


def _year_sparkline(articles_path: Path) -> str:
    """Build a sparkline string showing article count per year."""
    if not articles_path.exists():
        return ""
    import json
    year_counts: dict[int, int] = Counter()
    with open(articles_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                date = json.loads(line).get("date", "")
                if date and len(date) >= 4:
                    y = int(date[:4])
                    if 1990 <= y <= 2030:
                        year_counts[y] += 1
            except (json.JSONDecodeError, ValueError):
                pass
    if not year_counts:
        return ""
    min_y, max_y = min(year_counts), max(year_counts)
    span = max_y - min_y + 1
    max_chars = 14  # leave room for labels

    if span <= max_chars:
        # One char per year
        buckets = [year_counts.get(y, 0) for y in range(min_y, max_y + 1)]
    else:
        # Group into ~max_chars buckets
        step = max(2, (span + max_chars - 1) // max_chars)
        buckets = []
        for start in range(min_y, max_y + 1, step):
            total = sum(year_counts.get(y, 0) for y in range(start, min(start + step, max_y + 1)))
            buckets.append(total)

    max_count = max(buckets) if buckets else 1
    parts = []
    for c in buckets:
        idx = round(c / max_count * 8) if max_count > 0 else 0
        parts.append(_SPARK_CHARS[idx])

    return f"{str(min_y)[2:]}{''.join(parts)}{str(max_y)[2:]}"


def diagnose_site(config: dict, domain: str):
    """Comprehensive diagnostic report for a single site."""
    import statistics
    from collections import Counter
    from urllib.parse import urlparse

    from .sites.registry import get_handler
    from .storage import load_processed_urls

    output_dir = Path(config.get("output_dir", "data"))
    data_dir = output_dir / domain

    console.print(f"\n[bold]{'═' * 60}[/bold]")
    console.print(f"[bold]  Diagnostics for {domain}[/bold]")
    console.print(f"[bold]{'═' * 60}[/bold]\n")

    # ── Handler info ──
    handler = get_handler(domain)
    handler_name = handler.NAME
    is_custom = handler_name != "base"
    cdx_prefixes = getattr(handler, "CDX_PREFIXES", [])
    console.print(f"[bold]Handler:[/bold] {handler_name} {'[green](custom)[/green]' if is_custom else '[yellow](generic base)[/yellow]'}")
    if cdx_prefixes:
        console.print(f"  CDX_PREFIXES: {len(cdx_prefixes)} defined")
        for p in cdx_prefixes[:6]:
            console.print(f"    {p}")
        if len(cdx_prefixes) > 6:
            console.print(f"    ... and {len(cdx_prefixes) - 6} more")
    else:
        console.print(f"  CDX_PREFIXES: [dim]none (domain-wide or auto-prefix)[/dim]")

    # ── Data directory ──
    if not data_dir.exists():
        console.print(f"\n[red]No data directory found at {data_dir}[/red]")
        console.print(f"[dim]Run discovery first: python collect.py --phase cdx --site {domain}[/dim]")
        return

    console.print(f"\n[bold]Data directory:[/bold] {data_dir}")
    files = sorted(data_dir.iterdir())
    for f in files:
        size = f.stat().st_size
        if size > 1024 * 1024:
            size_str = f"{size / 1024 / 1024:.1f} MB"
        elif size > 1024:
            size_str = f"{size / 1024:.0f} KB"
        else:
            size_str = f"{size} B"
        lines = count_lines(f) if f.suffix == ".jsonl" else ""
        lines_str = f"  ({lines:,} records)" if lines else ""
        console.print(f"  {f.name:30s} {size_str:>10s}{lines_str}")

    # ── State ──
    state = load_state(data_dir)
    console.print(f"\n[bold]Pipeline phase:[/bold]", end=" ")

    arquivo_done = state.get("arquivo_cdx_done", False)
    wayback_done = state.get("wayback_cdx_done", False)
    sitemap_done = state.get("sitemap_done", False)
    has_tasks = (data_dir / "tasks.jsonl").exists()
    has_articles = (data_dir / "articles.jsonl").exists() and count_lines(data_dir / "articles.jsonl") > 0

    if has_articles:
        total_tasks = state.get("total_unique_articles", 0)
        done_count = count_lines(data_dir / "articles.jsonl") + count_lines(data_dir / "quality.jsonl")
        if total_tasks > 0 and done_count >= total_tasks:
            console.print("[green]COMPLETE[/green] (all tasks fetched)")
        else:
            console.print(f"[cyan]FETCHING[/cyan] ({done_count:,}/{total_tasks:,} processed)")
    elif has_tasks:
        console.print("[cyan]TASKS READY[/cyan] (dedup done, not yet fetched)")
    elif arquivo_done or wayback_done or sitemap_done:
        console.print("[yellow]DISCOVERY DONE[/yellow] (tasks not yet built)")
    else:
        console.print("[red]NOT STARTED[/red]")

    # ── Discovery details ──
    console.print(f"\n[bold]Discovery:[/bold]")
    console.print(f"  Arquivo CDX:  {'[green]done[/green]' if arquivo_done else '[red]not done[/red]'}"
                  f"  scanned={state.get('arquivo_cdx_count', 0):,}  saved={state.get('arquivo_cdx_saved', 0):,}")
    console.print(f"  Wayback CDX:  {'[green]done[/green]' if wayback_done else '[red]not done[/red]'}"
                  f"  scanned={state.get('wayback_cdx_count', 0):,}  saved={state.get('wayback_cdx_saved', 0):,}")
    console.print(f"  Sitemaps:     {'[green]done[/green]' if sitemap_done else '[red]not done[/red]'}"
                  f"  urls={state.get('sitemap_count', 0):,}")

    # ── Oldest CDX ──
    oldest = state.get("oldest_cdx", {})
    if oldest:
        console.print(f"\n[bold]Oldest captures:[/bold]")
        for src in ("arquivo", "wayback"):
            rec = oldest.get(src)
            if rec:
                ts = rec.get("timestamp", "")
                date_str = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}" if len(ts) >= 8 else ts
                console.print(f"  {src:8s}: {date_str}  {rec.get('url', '')[:70]}")
            else:
                console.print(f"  {src:8s}: [dim]not found[/dim]")

    # ── URL prefix map ──
    prefix_map = state.get("url_prefix_map", {})
    if prefix_map:
        console.print(f"\n[bold]URL prefix map[/bold] ({sum(prefix_map.values()):,} articles across {len(prefix_map)} segments):")
        max_count = max(prefix_map.values()) if prefix_map else 1
        for seg, count in sorted(prefix_map.items(), key=lambda x: -x[1])[:15]:
            bar = "█" * min(count * 30 // max(1, max_count), 30)
            console.print(f"  {seg:25s} {count:>6,}  {bar}")
        if len(prefix_map) > 15:
            console.print(f"  [dim]... and {len(prefix_map) - 15} more segments[/dim]")

    # ── Tasks breakdown ──
    tasks_path = data_dir / "tasks.jsonl"
    if tasks_path.exists():
        task_counts = _count_by_source(tasks_path)
        total_tasks = sum(task_counts.values())
        console.print(f"\n[bold]Tasks:[/bold] {total_tasks:,} total")
        for src in ("live", "arquivo", "wayback"):
            c = task_counts.get(src, 0)
            pct = c / total_tasks * 100 if total_tasks > 0 else 0
            console.print(f"  {src:8s}: {c:>8,}  ({pct:.1f}%)")

    # ── Articles analysis ──
    articles_path = data_dir / "articles.jsonl"
    articles = read_jsonl(articles_path)
    if articles:
        console.print(f"\n[bold]Articles:[/bold] {len(articles):,}")

        # By source
        src_counts = Counter(a.get("source", "?") for a in articles)
        for src in ("live", "arquivo", "wayback"):
            c = src_counts.get(src, 0)
            if c > 0:
                console.print(f"  {src:8s}: {c:>8,}")

        # Date range and timeline
        dates = sorted(a.get("date", "") for a in articles if a.get("date"))
        if dates:
            console.print(f"  Date range: {dates[0]} → {dates[-1]}")

            # Year histogram with sample titles
            import random
            year_counts = Counter(d[:4] for d in dates if len(d) >= 4)
            # Group articles by year for sampling
            by_year: dict[str, list[dict]] = {}
            for a in articles:
                y = (a.get("date") or "")[:4]
                if y and len(y) == 4:
                    by_year.setdefault(y, []).append(a)
            if year_counts:
                max_year_count = max(year_counts.values())
                console.print(f"\n[bold]Articles by year:[/bold]")
                for year in sorted(year_counts):
                    cnt = year_counts[year]
                    bar = "█" * max(1, cnt * 40 // max(1, max_year_count))
                    console.print(f"  {year}  {cnt:>6,}  {bar}")
                    # Show 2 random sample titles
                    pool = by_year.get(year, [])
                    samples = random.sample(pool, min(2, len(pool)))
                    for s in samples:
                        title = s.get("title", "(no title)")[:72]
                        console.print(f"           [dim]{title}[/dim]")

        # Field completeness
        console.print(f"\n[bold]Field completeness:[/bold]")
        for field in ("title", "date", "author", "agency", "categories", "section"):
            present = sum(1 for a in articles if a.get(field))
            pct = present / len(articles) * 100
            color = "green" if pct > 80 else ("yellow" if pct > 50 else "red")
            console.print(f"  {field:12s}: [{color}]{pct:5.1f}%[/{color}]  ({present:,}/{len(articles):,})")

        # Text length stats
        lengths = [a.get("text_length", 0) for a in articles]
        if lengths:
            lengths_sorted = sorted(lengths)
            short = sum(1 for l in lengths if l < 200)
            console.print(f"\n[bold]Text length:[/bold]")
            console.print(f"  median={statistics.median(lengths):.0f}  "
                         f"p10={lengths_sorted[len(lengths) // 10]:.0f}  "
                         f"p90={lengths_sorted[len(lengths) * 9 // 10]:.0f}")
            if short > 0:
                console.print(f"  [yellow]⚠ {short:,} articles ({short / len(articles) * 100:.1f}%) have <200 chars[/yellow]")

        # Extractor used
        extractors = Counter(a.get("extractor", "?") for a in articles)
        if len(extractors) > 1 or list(extractors.keys()) != ["base"]:
            console.print(f"\n[bold]Extractors used:[/bold]")
            for ext, cnt in extractors.most_common():
                console.print(f"  {ext}: {cnt:,}")

    # ── Error analysis ──
    quality_path = data_dir / "quality.jsonl"
    errors = read_jsonl(quality_path)
    if errors:
        console.print(f"\n[bold]Errors:[/bold] {len(errors):,}")
        reasons = Counter(e.get("reason", "unknown") for e in errors)
        for reason, cnt in reasons.most_common(10):
            pct = cnt / len(errors) * 100
            console.print(f"  {reason:30s} {cnt:>6,}  ({pct:.1f}%)")

        # Error sources
        err_sources = Counter(e.get("source", "?") for e in errors)
        if len(err_sources) > 1:
            console.print(f"  By source:")
            for src, cnt in err_sources.most_common():
                console.print(f"    {src}: {cnt:,}")

        # Sample error URLs
        top_reason = reasons.most_common(1)[0][0] if reasons else None
        if top_reason:
            samples = [e for e in errors if e.get("reason") == top_reason][:3]
            console.print(f"\n  Sample '{top_reason}' URLs:")
            for e in samples:
                console.print(f"    {e.get('url', '')}")

    # ── Success rate ──
    total_processed = len(articles) + len(errors)
    if total_processed > 0:
        ok_pct = len(articles) / total_processed * 100
        color = "green" if ok_pct > 85 else ("yellow" if ok_pct > 65 else "red")
        console.print(f"\n[bold]Success rate:[/bold] [{color}]{ok_pct:.1f}%[/{color}] ({len(articles):,}/{total_processed:,})")

    # ── Recommendations ──
    recs = []
    if not is_custom and total_processed > 50:
        if total_processed > 0 and len(articles) / total_processed < 0.70:
            recs.append("Low success rate — a custom handler is likely needed")
        for field in ("title", "date", "author"):
            present = sum(1 for a in articles if a.get(field))
            if articles and present / len(articles) < 0.60:
                recs.append(f"'{field}' extraction is poor — custom handler may help")
    if not cdx_prefixes and not prefix_map and wayback_done:
        recs.append("No URL prefix map — re-run discovery to generate it")
    if is_custom and not cdx_prefixes and prefix_map:
        recs.append("Custom handler has no CDX_PREFIXES — consider adding based on prefix map above")
    if errors:
        timeout_pct = Counter(e.get("reason") for e in errors).get("timeout", 0) / len(errors) * 100
        if timeout_pct > 30:
            recs.append(f"High timeout rate ({timeout_pct:.0f}%) — consider increasing fetch timeout or retry")
    if articles:
        short = sum(1 for a in articles if a.get("text_length", 0) < 100)
        if short / len(articles) > 0.10:
            recs.append(f"{short / len(articles) * 100:.0f}% of articles have <100 chars — extractor may need tuning")

    if recs:
        console.print(f"\n[bold yellow]Recommendations:[/bold yellow]")
        for r in recs:
            console.print(f"  [yellow]⚠ {r}[/yellow]")

    console.print()
