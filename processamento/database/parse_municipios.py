#!/usr/bin/env python3
"""
Parse and validate município data from jornais.csv against geoapi.pt,
and build a geographic hierarchy (Região → Distrito → Município).

Outputs:
  - geo_data.json   : full geographic hierarchy for the geo table
  - jornais.json    : jornais with validated município IDs for FK references

Reads from:
  - ../data-scraping/jornais.csv (already filtered by create_jornais_csv.py)
  - geoapi.pt API (cached locally)
"""

import csv
import json
import re
import urllib.request
from pathlib import Path
from collections import Counter

SCRIPT_DIR = Path(__file__).parent

# ── Paths ────────────────────────────────────────────────────────────────────
JORNAIS_CSV = SCRIPT_DIR.parent / "data-scraping" / "jornais.csv"
GEO_CACHE = SCRIPT_DIR / "geo_cache.json"
GEO_OUTPUT = SCRIPT_DIR / "geo_data.json"
JORNAIS_OUTPUT = SCRIPT_DIR / "jornais.json"

GEOAPI_BULK_URL = "https://json.geoapi.pt/distritos/municipios"

# ── Distrito → NUTS II Região ────────────────────────────────────────────────
# Includes all 29 distritos/ilhas from geoapi.pt
REGIAO_MAP = {
    "Viana do Castelo": "Norte",
    "Braga": "Norte",
    "Porto": "Norte",
    "Vila Real": "Norte",
    "Bragança": "Norte",
    "Aveiro": "Centro",
    "Viseu": "Centro",
    "Guarda": "Centro",
    "Coimbra": "Centro",
    "Castelo Branco": "Centro",
    "Leiria": "Centro",
    "Lisboa": "Área Metropolitana de Lisboa",
    "Setúbal": "Área Metropolitana de Lisboa",
    "Santarém": "Alentejo",
    "Portalegre": "Alentejo",
    "Évora": "Alentejo",
    "Beja": "Alentejo",
    "Faro": "Algarve",
    # Islands — each ilha is its own distrito
    "Ilha de São Miguel": "Região Autónoma dos Açores",
    "Ilha Terceira": "Região Autónoma dos Açores",
    "Ilha da Graciosa": "Região Autónoma dos Açores",
    "Ilha de São Jorge": "Região Autónoma dos Açores",
    "Ilha do Pico": "Região Autónoma dos Açores",
    "Ilha do Faial": "Região Autónoma dos Açores",
    "Ilha Das Flores": "Região Autónoma dos Açores",
    "Ilha do Corvo": "Região Autónoma dos Açores",
    "Ilha de Santa Maria": "Região Autónoma dos Açores",
    "Ilha da Madeira": "Região Autónoma da Madeira",
    "Ilha de Porto Santo": "Região Autónoma da Madeira",
}

# ── Manual mapper for CSV values → official municipality name ────────────────
# None = skip (region/non-municipality value)
MANUAL_MAP = {
    # Abbreviations / short forms
    "famalicão": "Vila Nova de Famalicão",
    "viana": "Viana do Castelo",
    "condeixa": "Condeixa-a-Nova",
    "constancia": "Constância",
    "albergaria": "Albergaria-a-Velha",
    "amarente": "Amarante",
    "guimar": "Guimarães",
    "s. joão da madeira": "São João da Madeira",
    "v.n. foz côa": "Vila Nova de Foz Côa",
    "castanheira de pera": "Castanheira de Pêra",
    "ourém.": "Ourém",
    "pointe de sor": "Ponte de Sor",
    "tomar\u200b": "Tomar",
    "pinhal novo": "Palmela",
    "lagoa (algarve)": "Lagoa",
    "lagoa (são miguel)": "Lagoa (açores)",
    "benfica": "Lisboa",
    "são domingos de benfica": "Lisboa",
    "carcavelos parede": "Cascais",
    "município lisboa": "Lisboa",

    # Not a municipality or region — skip silently
    "especializada": None,
}

# All Açores island distrito names
_ACORES_ILHAS = [
    "Ilha de São Miguel", "Ilha Terceira", "Ilha da Graciosa",
    "Ilha de São Jorge", "Ilha do Pico", "Ilha do Faial",
    "Ilha Das Flores", "Ilha do Corvo", "Ilha de Santa Maria",
]
_MADEIRA_ILHAS = ["Ilha da Madeira", "Ilha de Porto Santo"]

# ── Region names (from municipio column) → list of distritos ─────────────────
REGION_TO_DISTRITOS = {
    "alentejo": ["Santarém", "Portalegre", "Évora", "Beja"],
    "algarve": ["Faro"],
    "bairrada": ["Aveiro", "Coimbra"],
    "beira alta": ["Viseu", "Guarda"],
    "beiras": ["Castelo Branco", "Coimbra", "Guarda", "Viseu"],
    "cávado": ["Braga"],
    "grande lisboa": ["Lisboa"],
    "madeira": _MADEIRA_ILHAS,
    "minho": ["Braga", "Viana do Castelo"],
    "norte": ["Braga", "Bragança", "Porto", "Viana do Castelo", "Vila Real"],
    "norte?": ["Braga", "Bragança", "Porto", "Viana do Castelo", "Vila Real"],
    "ribatejo": ["Santarém"],
    "sul": ["Beja", "Évora", "Faro", "Portalegre", "Setúbal"],
    "tâmega": ["Porto"],
    "açores": _ACORES_ILHAS,
    "ilha terceira": ["Ilha Terceira"],
    "ilha de porto santo": ["Ilha de Porto Santo"],
    "ilha de são jorge": ["Ilha de São Jorge"],
    "são miguel": ["Ilha de São Miguel"],
    "terceira": ["Ilha Terceira"],
    "madalena": ["Ilha do Pico"],
    "região autónoma da madeira": _MADEIRA_ILHAS,
    "região autónoma dos açores": _ACORES_ILHAS,
    "região centro": ["Aveiro", "Castelo Branco", "Coimbra", "Guarda", "Leiria", "Viseu"],
    "região norte": ["Braga", "Bragança", "Porto", "Viana do Castelo", "Vila Real"],
    "região oeste": ["Leiria", "Lisboa"],
    "região sul": ["Beja", "Évora", "Faro", "Portalegre", "Setúbal"],
    "todas as regiôes do centro": ["Aveiro", "Castelo Branco", "Coimbra", "Guarda", "Leiria", "Viseu"],
    "região do oeste": ["Leiria", "Lisboa"],
    "a região sul": ["Beja", "Évora", "Faro", "Portalegre", "Setúbal"],
    "ilha do faial": ["Ilha do Faial"],
}

# ── Sub-region names → list of municípios (more precise than distrito) ───────
_VALE_DO_SOUSA = [
    "Castelo de Paiva", "Felgueiras", "Lousada",
    "Paços de Ferreira", "Paredes", "Penafiel",
]
_AVE = [
    "Cabeceiras de Basto", "Fafe", "Guimarães", "Mondim de Basto",
    "Póvoa de Lanhoso", "Vieira do Minho", "Vila Nova de Famalicão", "Vizela",
]
_BAIXO_TAMEGA = [
    "Amarante", "Baião", "Celorico de Basto",
    "Cinfães", "Marco de Canaveses", "Resende",
]
_TRAS_OS_MONTES = [
    "Alfândega da Fé", "Bragança", "Macedo de Cavaleiros",
    "Miranda do Douro", "Mirandela", "Mogadouro",
    "Vila Flor", "Vimioso", "Vinhais",
]
_DOURO = [
    "Alijó", "Armamar", "Carrazeda de Ansiães", "Freixo de Espada à Cinta",
    "Lamego", "Mesão Frio", "Moimenta da Beira", "Murça", "Penedono",
    "Peso da Régua", "Sabrosa", "Santa Marta de Penaguião",
    "São João da Pesqueira", "Sernancelhe", "Tabuaço", "Tarouca",
    "Torre de Moncorvo", "Vila Nova de Foz Côa", "Vila Real",
]
_PINHAL_INTERIOR_SUL = ["Oleiros", "Proença-a-Nova", "Sertã", "Vila de Rei"]
_BEIRA_INTERIOR_SUL = [
    "Castelo Branco", "Idanha-a-Nova", "Penamacor", "Vila Velha de Ródão",
]
_COVA_DA_BEIRA = ["Belmonte", "Covilhã", "Fundão"]

REGION_TO_MUNICIPIOS = {
    "regiões do sousa e do ave": _VALE_DO_SOUSA + _AVE,
    "região do baixo tâmega": _BAIXO_TAMEGA,
    "região do vale do sousa": _VALE_DO_SOUSA,
    "sousa": _VALE_DO_SOUSA,
    "trás os montes": _TRAS_OS_MONTES,
    "trás-os-montes": _TRAS_OS_MONTES,
    "território de trás-os-montes": _TRAS_OS_MONTES,
    "douro": _DOURO,
    "alto douro": _DOURO,
    "regiões do pinhal sul": _PINHAL_INTERIOR_SUL,
    "pinhal interior sul": _PINHAL_INTERIOR_SUL,
    "beira interior sul": _BEIRA_INTERIOR_SUL,
    "cova da beira": _COVA_DA_BEIRA,
}

# ── Regiao CSV column ("DISTRITO SEDE REDAÇÃO") → list of distritos ──────────
# These are the actual values in the regiao column of jornais.csv
REGIAO_CSV_TO_DISTRITOS = {
    # Continental distritos map to themselves (only the 18 continental ones)
    **{d: [d] for d in list(REGIAO_MAP)[:18]},
    # Island/RA values from the CSV → specific islands
    "Ilha de São Miguel": ["Ilha de São Miguel"],
    "Ilha Terceira": ["Ilha Terceira"],
    "Ilha do Faial": ["Ilha do Faial"],
    "Ilha da Madeira": ["Ilha da Madeira"],
    "Ilha de São Jorge": ["Ilha de São Jorge"],
    "Ilha do Pico": ["Ilha do Pico"],
    "Ilha de Porto Santo": ["Ilha de Porto Santo"],
    "Região Autónoma dos Açores": _ACORES_ILHAS,
    "Região Autónoma da Madeira": _MADEIRA_ILHAS,
}

SKIP_PREFIXES = [
    "distrito:", "distritos:", "região:", "regiao:",
    "sub-região:", "fregusias:", "região oeste - concelhos da",
]


# ── GeoAPI fetching ─────────────────────────────────────────────────────────

def fetch_geo_hierarchy():
    """
    Fetch the full geographic hierarchy from geoapi.pt bulk endpoint.
    Returns dict with 'distritos' and 'municipios' sub-dicts, keyed by codigoine/lowercase name.
    Cached locally in geo_cache.json.
    """
    if GEO_CACHE.exists():
        with open(GEO_CACHE, encoding="utf-8") as f:
            return json.load(f)

    print("Fetching geographic hierarchy from geoapi.pt ...")
    req = urllib.request.Request(GEOAPI_BULK_URL, headers={"Accept": "application/json"})
    data = json.loads(urllib.request.urlopen(req, timeout=30).read())

    hierarchy = {"distritos": {}, "municipios": {}}
    for entry in data:
        distrito_name = entry["distrito"]
        distrito_code = entry["codigoine"]  # e.g. "08" for Faro
        regiao = REGIAO_MAP.get(distrito_name, distrito_name)

        hierarchy["distritos"][distrito_code] = {
            "nome": distrito_name,
            "codigoine": distrito_code,
            "regiao": regiao,
        }

        for mun in entry.get("municipios", []):
            nome = mun["nome"]
            mun_code = mun["codigoine"]  # e.g. "0801" for Albufeira
            hierarchy["municipios"][nome.lower()] = {
                "nome": nome,
                "codigoine": mun_code,
                "distrito_code": distrito_code,
                "distrito": distrito_name,
                "regiao": regiao,
            }

    with open(GEO_CACHE, "w", encoding="utf-8") as f:
        json.dump(hierarchy, f, ensure_ascii=False, indent=2)
    print(f"  Cached {len(hierarchy['distritos'])} distritos + {len(hierarchy['municipios'])} municipios")
    return hierarchy


# ── Município parsing ────────────────────────────────────────────────────────

def build_lookup(hierarchy):
    """Build case-insensitive lookup: lowercase name → official name."""
    return {k: v["nome"] for k, v in hierarchy["municipios"].items()}


def parse_municipio_field(raw, lookup, warnings):
    """Parse a raw Município cell.

    Returns (municipio_names: list[str], distrito_names: list[str]).
    municipio_names are validated municipality names.
    distrito_names come from region-level entries (via REGION_TO_DISTRITOS).
    """
    if not raw or not raw.strip():
        return [], []

    raw = raw.strip()
    mun_results = []
    dist_results = []

    # Split by pipe, then comma, then newlines, then " e "/" E "
    # But check for known compound names before splitting by "e"
    pipe_parts = [p.strip() for p in raw.split("|") if p.strip()]
    parts = []
    for pp in pipe_parts:
        for cp in pp.split(","):
            cp = cp.strip()
            if not cp:
                continue
            for line in cp.splitlines():
                line = line.strip()
                if not line:
                    continue
                # If the whole line matches a known region, don't split by "e"
                if line.lower() in REGION_TO_DISTRITOS or line.lower() in REGION_TO_MUNICIPIOS:
                    parts.append(line)
                else:
                    for sub in re.split(r"\s+[eE]\s+", line):
                        s = sub.strip()
                        if s:
                            parts.append(s)

    for token in parts:
        token_lower = token.lower()

        # Check prefixes to skip
        if any(token_lower.startswith(p) for p in SKIP_PREFIXES):
            continue

        # Sub-region → specific municípios
        if token_lower in REGION_TO_MUNICIPIOS:
            mun_results.extend(REGION_TO_MUNICIPIOS[token_lower])
            continue

        # Region → distritos
        if token_lower in REGION_TO_DISTRITOS:
            dist_results.extend(REGION_TO_DISTRITOS[token_lower])
            continue

        # Manual map → municipality
        if token_lower in MANUAL_MAP:
            mapped = MANUAL_MAP[token_lower]
            if mapped is not None:
                mun_results.append(mapped)
            continue

        # Case-insensitive lookup → municipality
        if token_lower in lookup:
            mun_results.append(lookup[token_lower])
            continue

        warnings.append((token, raw))

    return mun_results, dist_results


def main():
    hierarchy = fetch_geo_hierarchy()
    lookup = build_lookup(hierarchy)

    # ── Build distrito lookup (name → codigoine) ─────────────────────────
    distrito_name_to_code = {
        d["nome"]: d["codigoine"] for d in hierarchy["distritos"].values()
    }
    # Build distrito records for output
    distrito_records = sorted(hierarchy["distritos"].values(), key=lambda d: d["codigoine"])

    # Read jornais.csv
    with open(JORNAIS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"\nRead {len(rows)} jornais from {JORNAIS_CSV.name}")

    # ── Parse municipio column ───────────────────────────────────────────
    referenced_municipios = set()
    all_warnings = []
    warning_counts = Counter()
    jornais_mun_map = {}    # row index → list of official mun names
    jornais_dist_map = {}   # row index → set of distrito names

    for i, row in enumerate(rows):
        raw_mun = (row.get("municipio") or "").strip()
        warnings = []
        mun_names, dist_names = parse_municipio_field(raw_mun, lookup, warnings)

        for token, _ in warnings:
            warning_counts[token] += 1
        all_warnings.extend(warnings)

        jornais_mun_map[i] = mun_names
        jornais_dist_map[i] = set(dist_names)
        referenced_municipios.update(mun_names)

    # Build municipio records for ALL municipalities (not just referenced ones)
    # so the map can show coverage for district-level jornais too
    mun_name_to_code = {}
    mun_records = []

    for _key, info in hierarchy["municipios"].items():
        mun_name_to_code[info["nome"]] = info["codigoine"]
        mun_records.append({
            "codigoine": info["codigoine"],
            "nome": info["nome"],
            "distrito_codigoine": info["distrito_code"],
        })
    # Deduplicate by codigoine (some names map to the same code)
    seen_codes = set()
    deduped = []
    for m in sorted(mun_records, key=lambda m: m["codigoine"]):
        if m["codigoine"] not in seen_codes:
            seen_codes.add(m["codigoine"])
            deduped.append(m)
    mun_records = deduped

    # ── Write geo_data.json ──────────────────────────────────────────────
    geo_data = {
        "distritos": [{"codigoine": d["codigoine"], "nome": d["nome"], "regiao": d["regiao"]} for d in distrito_records],
        "municipios": mun_records,
    }
    with open(GEO_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(geo_data, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(distrito_records)} distritos + {len(mun_records)} municipios to {GEO_OUTPUT.name}")

    # ── Build jornais.json ───────────────────────────────────────────────
    jornais_out = []
    for i, row in enumerate(rows):
        mun_names = jornais_mun_map[i]
        mun_codes = sorted(set(
            mun_name_to_code[m] for m in mun_names if m in mun_name_to_code
        ))

        # Distrito codes: from region-level entries + municipios' parent distritos + regiao CSV column
        dist_names = set(jornais_dist_map[i])
        for m in mun_names:
            info = hierarchy["municipios"].get(m.lower())
            if info:
                dist_names.add(info["distrito"])
        regiao_csv = (row.get("regiao") or "").strip()
        if regiao_csv and regiao_csv in REGIAO_CSV_TO_DISTRITOS:
            dist_names.update(REGIAO_CSV_TO_DISTRITOS[regiao_csv])
        dist_codes = sorted(set(
            distrito_name_to_code[d] for d in dist_names if d in distrito_name_to_code
        ))

        jornais_out.append({
            "nome": (row.get("nome") or "").strip(),
            "proprietario": (row.get("proprietario") or "").strip() or None,
            "estado": (row.get("estado") or "").strip() or None,
            "suporte": (row.get("suporte") or "").strip() or None,
            "data_inscricao": (row.get("data_inscricao") or "").strip() or None,
            "url": (row.get("url") or "").strip() or None,
            "municipio_codes": mun_codes,
            "distrito_codes": dist_codes,
            "periodicidade": (row.get("periodicidade") or "").strip() or None,
            "data_situacao": (row.get("data_situacao") or "").strip() or None,
            "erc": (row.get("erc") or "").strip() or None,
        })

    with open(JORNAIS_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(jornais_out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(jornais_out)} jornais to {JORNAIS_OUTPUT.name}")

    # ── Summary ──────────────────────────────────────────────────────────
    with_mun = sum(1 for j in jornais_out if j["municipio_codes"])
    with_dist = sum(1 for j in jornais_out if j["distrito_codes"])
    without_either = sum(1 for j in jornais_out if not j["municipio_codes"] and not j["distrito_codes"])

    print(f"\n{'─' * 50}")
    print(f"Jornais with município(s):   {with_mun:>5}")
    print(f"Jornais with distrito(s):    {with_dist:>5}")
    print(f"Jornais without either:      {without_either:>5}")
    print(f"Unique municípios used:      {len(mun_records):>5}")
    print(f"Unique distritos:            {len(distrito_records):>5}")

    # Distrito breakdown
    code_to_name = {d["codigoine"]: d["nome"] for d in distrito_records}
    dist_usage = Counter()
    for j in jornais_out:
        for dc in j["distrito_codes"]:
            dist_usage[dc] += 1
    print(f"\nDistritos by usage:")
    for dc, count in dist_usage.most_common():
        print(f"  {dc} {code_to_name.get(dc, '?'):36s} {count:>4}")

    if warning_counts:
        print(f"\n⚠ Unmatched município values ({len(warning_counts)} unique, {len(all_warnings)} total):")
        for token, count in warning_counts.most_common():
            print(f"  {token:40s} ×{count}")


if __name__ == "__main__":
    main()
