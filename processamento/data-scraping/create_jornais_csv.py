#!/usr/bin/env python3
"""
Create jornais.csv from two sources:

1. 'jornais regionais - oficial.csv' (ERC curated list)
   Filters: INCLUIR == TRUE, URL not empty

2. 'jornais regionais - publicacoes-portuguesas.csv' (supplementary list)
   Filters: URL not empty, SUPORTE in (Online, Papel/Online),
            ÂMBITO == Regional, CONTEÚDO == Informação Geral,
            IN_OFICIAL == FALSE

Deduplicates by normalized URL (oficial takes precedence).

Output columns:
  nome, proprietario, estado, suporte, data_inscricao, url,
  municipio, periodicidade, data_situacao, regiao, erc
"""

import csv
from pathlib import Path
from collections import Counter

INPUT_OFICIAL = Path(__file__).parent / "jornais regionais - oficial.csv"
INPUT_PP = Path(__file__).parent / "jornais regionais - publicacoes-portuguesas.csv"
OUTPUT = Path(__file__).parent / "jornais.csv"

OUT_COLS = ["nome", "proprietario", "estado", "suporte", "data_inscricao",
            "url", "municipio", "periodicidade", "data_situacao", "regiao", "erc"]


def norm_url(u):
    """Normalize URL for deduplication."""
    return (u or "").strip().lower().replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")


def load_oficial(path):
    """Load and filter the ERC oficial CSV."""
    with open(path, newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    kept = []
    stats = {"total": len(all_rows), "no_url": 0, "not_included": 0}

    for row in all_rows:
        url = (row.get("URL") or "").strip()
        incluir = (row.get("INCLUIR") or "").strip().upper()

        if not url:
            stats["no_url"] += 1
        if incluir != "TRUE":
            stats["not_included"] += 1

        if url and incluir == "TRUE":
            kept.append({
                "nome": (row.get("TÍTULO") or "").strip(),
                "proprietario": (row.get("PROPRIETÁRIO") or "").strip(),
                "estado": (row.get("ESTADO") or "").strip(),
                "suporte": (row.get("SUPORTE") or "").strip(),
                "data_inscricao": (row.get("DATA DE INSCRIÇÃO") or "").strip(),
                "url": url,
                "municipio": (row.get("Município") or "").strip(),
                "periodicidade": (row.get("PERIODICIDADE") or "").strip(),
                "data_situacao": (row.get("DATA DA SITUAÇÃO") or "").strip(),
                "regiao": (row.get("DISTRITO SEDE REDAÇÃO") or "").strip(),
                "erc": (row.get("SITE_ERC") or "").strip(),
            })

    return kept, stats


def load_publicacoes(path):
    """Load and filter the publicacoes-portuguesas CSV."""
    url_col = "Endereço (URL) do Website - online na Web"

    with open(path, newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    kept = []
    stats = {"total": len(all_rows), "filtered": 0}

    for row in all_rows:
        url = (row.get(url_col) or "").strip()
        suporte = (row.get("SUPORTE") or "").strip()
        ambito = (row.get("ÂMBITO") or "").strip()
        conteudo = (row.get("CONTEÚDO") or "").strip()
        in_oficial = (row.get("IN_OFICIAL") or "").strip()

        if not url or url == "_":
            stats["filtered"] += 1
            continue
        if suporte not in ("Online", "Papel/Online"):
            stats["filtered"] += 1
            continue
        if ambito != "Regional":
            stats["filtered"] += 1
            continue
        if conteudo != "Informação Geral":
            stats["filtered"] += 1
            continue
        if in_oficial != "FALSE":
            stats["filtered"] += 1
            continue

        kept.append({
            "nome": (row.get("Título") or "").strip(),
            "proprietario": "",
            "estado": (row.get("ESTADO") or "").strip(),
            "suporte": suporte,
            "data_inscricao": "",
            "url": url,
            "municipio": (row.get("CONCELHO") or "").strip(),
            "periodicidade": (row.get("PERIODICIDADE") or "").strip(),
            "data_situacao": "",
            "regiao": (row.get("DISTRITO") or "").strip(),
            "erc": (row.get("ERC_URL") or "").strip().strip('"'),
        })

    return kept, stats


def main():
    # Load both sources
    oficial_rows, oficial_stats = load_oficial(INPUT_OFICIAL)
    pp_rows, pp_stats = load_publicacoes(INPUT_PP)

    # Deduplicate: oficial takes precedence
    seen_urls = set()
    merged = []
    pp_dupes = 0

    for row in oficial_rows:
        key = norm_url(row["url"])
        seen_urls.add(key)
        merged.append(row)

    for row in pp_rows:
        key = norm_url(row["url"])
        if key in seen_urls:
            pp_dupes += 1
            continue
        seen_urls.add(key)
        merged.append(row)

    # Write output
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLS)
        writer.writeheader()
        for row in merged:
            writer.writerow(row)

    # Stats
    print(f"{'─' * 50}")
    print(f"Source 1: {INPUT_OFICIAL.name}")
    print(f"  Total rows:            {oficial_stats['total']:>6}")
    print(f"  Kept:                  {len(oficial_rows):>6}")
    print(f"{'─' * 50}")
    print(f"Source 2: {INPUT_PP.name}")
    print(f"  Total rows:            {pp_stats['total']:>6}")
    print(f"  After filters:         {len(pp_rows):>6}")
    print(f"  Duplicates (skipped):  {pp_dupes:>6}")
    print(f"  New additions:         {len(pp_rows) - pp_dupes:>6}")
    print(f"{'─' * 50}")
    print(f"Output: {OUTPUT.name}")
    print(f"  Total merged:          {len(merged):>6}")
    print()

    # Breakdowns
    estados = Counter(r["estado"] for r in merged)
    suportes = Counter(r["suporte"] for r in merged)
    distritos = Counter(r["regiao"] for r in merged)

    print("By estado:")
    for k, v in estados.most_common():
        print(f"  {k or '(vazio)':30s} {v:>5}")

    print("\nBy suporte:")
    for k, v in suportes.most_common():
        print(f"  {k or '(vazio)':30s} {v:>5}")

    print("\nBy regiao (top 10):")
    for k, v in distritos.most_common(10):
        print(f"  {k or '(vazio)':30s} {v:>5}")
    if len(distritos) > 10:
        print(f"  ... and {len(distritos) - 10} more regions")


if __name__ == "__main__":
    main()
