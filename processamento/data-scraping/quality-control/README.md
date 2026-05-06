# Quality Control Dashboard

Web interface for inspecting scraping status, article quality, and error patterns across all sites.

## Run

```bash
cd processamento/data-scraping
python3 quality-control/qc_server.py
```

Opens at **http://localhost:8066**. Change port with `QC_PORT=9000 python3 quality-control/qc_server.py`.

No extra dependencies — uses the stdlib `http.server` and reads directly from the `data/` directory.

## What it shows

- **Index** — all sites sortable by articles, errors, OK%, phase. Filter by domain, phase (complete/fetching/tasks/discovery/pending), or handler type (custom/base).
- **Site detail** — click any domain to see field completeness, failure reasons, year distribution, text length stats, URL prefix map, sample articles, and automated recommendations (e.g. "custom handler likely needed").
- **Search** — on the detail page, search articles and errors by URL or title. Links to archived pages on arquivo.pt / Wayback Machine.
