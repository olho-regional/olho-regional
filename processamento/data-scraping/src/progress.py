import time
import threading

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, ProgressColumn, SpinnerColumn, TextColumn
from rich.text import Text

console = Console()

# Shared progress instance for parallel mode — only one Rich Live display allowed
_shared_progress: Progress | None = None
_shared_lock = threading.Lock()
_shared_refcount = 0


class _SourceColumn(ProgressColumn):
    """Column that shows live/arquivo/wayback task percentages."""

    def render(self, task):
        src = task.fields.get("sources", "")
        return Text(src, style="dim")


class _ETAColumn(ProgressColumn):
    """ETA based on wall-clock elapsed / progress ratio. Immune to batch bursts."""

    def render(self, task):
        eta = task.fields.get("eta", "-:--:--")
        return Text(eta, style="cyan")


def _get_shared_progress() -> Progress:
    """Get or create the shared Progress instance."""
    global _shared_progress, _shared_refcount
    with _shared_lock:
        if _shared_progress is None:
            _shared_progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.fields[domain]}"),
                BarColumn(bar_width=30),
                MofNCompleteColumn(),
                TextColumn("| {task.fields[errors]} err"),
                _SourceColumn(),
                TextColumn("| {task.fields[speed]}"),
                _ETAColumn(),
                console=console,
            )
            _shared_progress.start()
        _shared_refcount += 1
        return _shared_progress


def _release_shared_progress():
    """Release a reference to the shared Progress instance."""
    global _shared_progress, _shared_refcount
    with _shared_lock:
        _shared_refcount -= 1
        if _shared_refcount <= 0 and _shared_progress is not None:
            _shared_progress.stop()
            _shared_progress = None
            _shared_refcount = 0


class ProgressTracker:
    """Live progress dashboard using rich. Safe for parallel use."""

    def __init__(self, domain: str, total: int,
                 live_count: int = 0, arquivo_count: int = 0, wayback_count: int = 0):
        self.domain = domain
        self.total = total
        self.success = 0
        self.errors = 0
        self.start_time = None
        self.progress = None
        self.task_id = None
        # Per-source totals (for display)
        self.live_total = live_count
        self.arquivo_total = arquivo_count
        self.wayback_total = wayback_count

    def _sources_str(self) -> str:
        """Build compact source breakdown string."""
        parts = []
        if self.live_total:
            pct = self.live_total * 100 // self.total if self.total else 0
            parts.append(f"L{pct}%")
        if self.arquivo_total:
            pct = self.arquivo_total * 100 // self.total if self.total else 0
            parts.append(f"A{pct}%")
        if self.wayback_total:
            pct = self.wayback_total * 100 // self.total if self.total else 0
            parts.append(f"W{pct}%")
        return " ".join(parts)

    def start(self):
        self.start_time = time.time()
        self.progress = _get_shared_progress()
        self.task_id = self.progress.add_task(
            "Fetching",
            total=self.total,
            domain=self.domain,
            errors="0",
            speed="--",
            sources=self._sources_str(),
            eta="-:--:--",
        )

    @staticmethod
    def _fmt_eta(seconds: float) -> str:
        if seconds < 0:
            return "-:--:--"
        h, rem = divmod(int(seconds), 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def update(self, success: bool = False, error: bool = False):
        if success:
            self.success += 1
        if error:
            self.errors += 1

        elapsed = time.time() - self.start_time if self.start_time else 1
        done = self.success + self.errors
        speed = done / elapsed if elapsed > 0 else 0
        remaining = self.total - done
        eta_secs = remaining / speed if speed > 0 else 0

        self.progress.update(
            self.task_id,
            advance=1,
            errors=str(self.errors),
            speed=f"~{speed:.1f}/s",
            eta=self._fmt_eta(eta_secs),
        )

    def finish(self):
        if self.task_id is not None:
            # Ensure bar shows complete
            done = self.success + self.errors
            remaining = self.total - done
            if remaining > 0:
                self.progress.update(self.task_id, advance=remaining)
            self.progress.remove_task(self.task_id)
        _release_shared_progress()
        elapsed = time.time() - self.start_time if self.start_time else 0
        console.print(
            f"\n[bold green]Done:[/] {self.domain} — "
            f"{self.success} articles, {self.errors} errors "
            f"in {elapsed:.0f}s"
        )
