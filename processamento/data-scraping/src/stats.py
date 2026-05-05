import statistics
from collections import Counter

from rich.console import Console
from rich.table import Table

console = Console()


def compute_stats(articles: list[dict], quality: list[dict], state: dict, domain: str) -> dict:
    """Compute run statistics from articles and quality records."""
    total_fetched = len(articles) + len(quality)
    success_count = len(articles)
    error_count = len(quality)
    success_pct = (success_count / total_fetched * 100) if total_fetched > 0 else 0

    # Failure reasons
    reasons = Counter(q.get("reason", "unknown") for q in quality)

    # Field completeness
    fields = {}
    for field in ("title", "date", "author", "agency"):
        present = sum(1 for a in articles if a.get(field))
        fields[field] = (present / success_count * 100) if success_count > 0 else 0

    # Text length stats
    lengths = [a.get("text_length", 0) for a in articles]
    length_stats = {}
    if lengths:
        lengths_sorted = sorted(lengths)
        length_stats = {
            "median": statistics.median(lengths),
            "p10": lengths_sorted[max(0, len(lengths) // 10)],
            "p90": lengths_sorted[min(len(lengths) - 1, len(lengths) * 9 // 10)],
        }

    # Recommendations
    recommendations = []
    if success_pct < 70:
        recommendations.append("Low extraction success rate — a custom handler is likely needed")
    for field, pct in fields.items():
        if field == "agency":
            continue
        if pct < 60:
            recommendations.append(f"'{field}' extraction rate is low ({pct:.0f}%) — consider custom handler")

    return {
        "domain": domain,
        "arquivo_cdx_count": state.get("arquivo_cdx_count", 0),
        "wayback_cdx_count": state.get("wayback_cdx_count", 0),
        "sitemap_count": state.get("sitemap_count", 0),
        "total_fetched": total_fetched,
        "success_count": success_count,
        "error_count": error_count,
        "success_pct": success_pct,
        "failure_reasons": dict(reasons.most_common(10)),
        "field_completeness": fields,
        "text_length": length_stats,
        "recommendations": recommendations,
    }


def print_stats(stats: dict):
    """Print run statistics to the console."""
    console.print(f"\n[bold]=== Run Statistics ===[/bold]")
    console.print(f"Site: [bold]{stats['domain']}[/bold]")

    console.print(f"  Discovery:")
    console.print(f"    arquivo CDX:   {stats['arquivo_cdx_count']:>8,} records")
    console.print(f"    wayback CDX:   {stats['wayback_cdx_count']:>8,} records")
    console.print(f"    live sitemaps: {stats['sitemap_count']:>8,} URLs")

    console.print(f"  Fetched this run: {stats['total_fetched']:,}")
    console.print(
        f"  Extraction success: {stats['success_count']:,} ({stats['success_pct']:.1f}%)"
    )
    console.print(f"  Extraction failed:  {stats['error_count']:,}")

    if stats["failure_reasons"]:
        for reason, count in stats["failure_reasons"].items():
            console.print(f"    - {reason}: {count:,}")

    console.print(f"  Field completeness:")
    for field, pct in stats["field_completeness"].items():
        console.print(f"    - {field}: {pct:.1f}%")

    if stats["text_length"]:
        tl = stats["text_length"]
        console.print(
            f"  Text length: median={tl['median']:.0f} | "
            f"p10={tl['p10']:.0f} | p90={tl['p90']:.0f}"
        )

    for rec in stats.get("recommendations", []):
        console.print(f"  [yellow]⚠ {rec}[/yellow]")
