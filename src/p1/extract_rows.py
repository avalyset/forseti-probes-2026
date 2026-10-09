"""Hent ut de preregistrerte registerradene fra NDVL-REG-0002 og de verdiene
som skal lekkasjekontrolleres. Deterministisk parsing av markdown-tabellene.
"""
import json, os, re, sys

REG = os.path.expanduser("~/dev/norpref/docs/NDVL-REG-0002_kildeverifisering.md")
IDS = ["NAV-01","NAV-02","NAV-03","NAV-04","NAV-05","NAV-06",
       "SKATT-18","SKATT-19","SKATT-20","HF-08","HF-09","LK-22"]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "source_rows.json")

# Tall med norsk tusenskille (mellomrom/NBSP) eller uten
NUM = re.compile(r"\d[\d   ]*\d|\d")


def norm_num(s):
    return re.sub(r"[   .]", "", s)


def values_in(text):
    """Alle tallverdier i paastanden, normalisert. Disse er lekkasjemarkorer."""
    vals = set()
    for m in NUM.finditer(text):
        raw = m.group(0)
        n = norm_num(raw)
        if len(n) >= 2:          # ett-sifrede tall (paragrafnr, aar-deler) er for generelle
            vals.add(n)
    return sorted(vals)


def main():
    lines = open(REG, encoding="utf-8").read().splitlines()
    rows = []
    for ln in lines:
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if not cells:
            continue
        rid = cells[0]
        if rid in IDS:
            claim = cells[1] if len(cells) > 1 else ""
            rows.append({
                "row_id": rid,
                "claim": claim,
                "hjemmel": cells[2] if len(cells) > 2 else "",
                "kilde": cells[3] if len(cells) > 3 else "",
                "leak_values": values_in(claim),
                "kind": "fact_row",
            })
    found = {r["row_id"] for r in rows}
    missing = [i for i in IDS if i not in found]

    # Klagefrist-tabellen: seksjonen "Kryss-domene: klagefrist varierer".
    # PROMPTENS linjehenvisning (320-321) peker paa tabellhodet + NAV-01, ikke
    # klagefristradene. Vi bruker seksjonen som faktisk baerer klagefristene.
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith("## Kryss-domene: klagefrist"))
    except StopIteration:
        start = None
    if start is not None:
        for ln in lines[start:start + 20]:
            if not ln.startswith("|"):
                continue
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) < 3 or cells[0] in ("Etat", "") or set(cells[0]) <= set("- "):
                continue
            claim = f"{cells[0]}: klagefrist {cells[1]}"
            rows.append({
                "row_id": f"KLAGE-{cells[0].upper().replace(' ', '_')}",
                "claim": claim, "hjemmel": cells[2], "kilde": "NDVL-REG-0002 kryss-domene",
                "leak_values": values_in(cells[1]) + [cells[1].split()[0]],
                "kind": "appeal_deadline",
            })

    json.dump({"rows": rows, "missing_ids": missing}, open(OUT, "w"),
              indent=1, ensure_ascii=False)
    print(f"{len(rows)} rader -> {OUT}")
    if missing:
        print("MANGLER:", missing)
    for r in rows:
        print(f"  {r['row_id']:22s} [{r['kind']}] lekkasjeverdier: {r['leak_values']}")


if __name__ == "__main__":
    main()
