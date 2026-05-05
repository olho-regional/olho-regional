"""
Scrape all Online and Imprensa entries from the ERC transparency portal and output to CSV.
https://portaltransparencia.erc.pt/ocs/?idOcs=Online
https://portaltransparencia.erc.pt/ocs/?idOcs=Imprensa
"""

import csv
import html
import re
import urllib.request
import ssl


def fetch_page(url: str) -> str:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=ctx) as resp:
        return resp.read().decode("utf-8")


def parse_entries(page_html: str) -> list[dict]:
    rows = re.findall(
        r'<tr class="border_bottom">(.*?)</tr>', page_html, re.DOTALL
    )
    entries = []
    for row in rows:
        tds = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if len(tds) < 4:
            continue

        # Column 0: designation (with link)
        link_match = re.search(r'href="([^"]+)"', tds[0])
        name = html.unescape(re.sub(r"<[^>]+>", "", tds[0]).strip())
        detail_path = html.unescape(link_match.group(1)) if link_match else ""

        # Column 1: type
        tipo = html.unescape(re.sub(r"<[^>]+>", "", tds[1]).strip())

        # Column 2: owning entity
        entidade = html.unescape(re.sub(r"<[^>]+>", "", tds[2]).strip())

        # Column 3: district
        distrito = html.unescape(re.sub(r"<[^>]+>", "", tds[3]).strip())

        entries.append(
            {
                "name": name,
                "type": tipo,
                "owner": entidade,
                "district": distrito,
                "detail_url": f"https://portaltransparencia.erc.pt{detail_path}"
                if detail_path
                else "",
            }
        )
    return entries


def main():
    urls = [
        "https://portaltransparencia.erc.pt/ocs/?idOcs=Online",
        "https://portaltransparencia.erc.pt/ocs/?idOcs=Imprensa",
    ]
    all_entries = []
    for url in urls:
        print(f"Fetching {url} ...")
        page = fetch_page(url)
        entries = parse_entries(page)
        print(f"  Found {len(entries)} entries")
        all_entries.extend(entries)
    print(f"Total: {len(all_entries)} entries")

    out_path = "erc-raw.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["name", "type", "owner", "district", "detail_url"]
        )
        writer.writeheader()
        writer.writerows(all_entries)
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
