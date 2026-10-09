"""4a: konverter klagefrist-tabellen fra NDVL-REG-0002 til registerrader.

Seksjonen «Kryss-domene: klagefrist varierer» er den eneste delen av
expected_facts.yaml som peker inn i registeret, og den peker pa prosa som
aldri ble konvertert. Tre av scenariofaktaene kan derfor ikke loses i dag.
"""
import os, re, sys
import yaml

REG = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.expanduser("~/dev/norpref/docs/NDVL-REG-0002_kildeverifisering.md")

# Hjemmel per etat, ordrett fra tabellen. Lovdata-ID fra lovkart.yaml.
HJEMMEL = {
    "NAV": ("ftrl. § 21-12", "lov/1997-02-28-19", "nav", "NAV-KLAGE-01"),
    "Skatteetaten": ("skfvl. § 13-4", "lov/2016-05-27-14", "skatteetaten", "SKATT-KLAGE-01"),
    "Lånekassen": ("fvl. § 29 (ingen lex specialis)", "lov/1967-02-10", "lanekassen", "LK-KLAGE-01"),
}
WEEKS = re.compile(r"(\d+)\s*uker")


def rows_from_register():
    lines = open(SRC, encoding="utf-8").read().splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("## Kryss-domene: klagefrist"))
    out = []
    for l in lines[i:i + 20]:
        if not l.startswith("|"):
            continue
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) < 3 or c[0] in ("Etat", "") or set(c[0]) <= set("- "):
            continue
        etat, frist, hj = c[0], c[1], c[2]
        if etat not in HJEMMEL:
            print(f"  UKJENT etat i tabellen: {etat!r} — hoppet over, ikke gjettet")
            continue
        basis, refid, domain, rid = HJEMMEL[etat]
        assert hj == basis, f"hjemmel avviker for {etat}: {hj!r} != {basis!r}"
        m = WEEKS.search(frist)
        assert m, f"fant ingen ukeverdi i {frist!r}"
        out.append({
            "id": rid, "domain": domain,
            "claim": f"{etat}: klagefrist {frist}",
            "legal_basis": basis,
            "register_status": "VERIFISERT verbatim",
            "review_trigger": "LOVENDRING",
            "review_by": None,
            "section": "Kryss-domene: klagefrist varierer",
            "values": [{"value": int(m.group(1)), "unit": "uker",
                        "valid_from": None, "valid_to": None,
                        "context": f"{etat} | {frist} | {hj}",
                        "sources": [{"url": f"https://lovdata.no/{refid}",
                                     "quote": None, "verified_at": None}]}],
            "flags": ["kildesitat_mangler_i_registeret", "review_by_mangler",
                      "konvertert_fra_kryss_domene_tabell"],
            "lovdata_refid": refid,
        })
    return out


def main():
    rows = rows_from_register()
    print(f"{len(rows)} klagefristrader lest fra NDVL-REG-0002")
    by_dom = {}
    for r in rows:
        by_dom.setdefault(r["domain"], []).append(r)
    for dom, rs in sorted(by_dom.items()):
        p = os.path.join(REG, "data", f"{dom}.yaml")
        d = yaml.safe_load(open(p, encoding="utf-8"))
        have = {f["id"] for f in d["facts"]}
        add = [r for r in rs if r["id"] not in have]
        if not add:
            print(f"  {dom}: allerede der, hopper over")
            continue
        d["facts"] += add
        yaml.safe_dump(d, open(p, "w", encoding="utf-8"),
                       allow_unicode=True, sort_keys=False, width=100)
        for r in add:
            print(f"  {dom}: + {r['id']}  {r['values'][0]['value']} uker  {r['legal_basis']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
