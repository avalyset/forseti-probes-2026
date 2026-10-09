"""4b og 4c: LK-12 far forfallsdato, og pliktavleveringsradene far paragraf
der den kan belegges VERBATIM i lovteksten. Der den ikke kan: la sta, flagg.
"""
import os
import yaml

REG = os.path.dirname(os.path.abspath(__file__))
LOV = "https://lovdata.no/dokument/NL/lov/1989-06-09-32"
FOR = "https://lovdata.no/dokument/SF/forskrift/2018-07-01-1139"
SHA_LOV = "nl-19890609-032.xml i gjeldende-lover.tar.bz2 sha256 f7318fe7469f5111…"
SHA_FOR = "sf-20180701-1139.xml i gjeldende-sentrale-forskrifter.tar.bz2 sha256 36116e5cdfe7364b…"

# Lost med verbatim treff i konsolidert tekst, hentet fra NLOD-arkivet 2026-10-09.
RESOLVED = {
    "NB-17": ("pliktavleveringslova LOV-1989-06-09-32 § 4", "lov/1989-06-09-32", "§4",
              "Både fysiske og digitale dokument som er gjorde tilgjengelege for allmenta "
              "skal avleverast i inntil sju eksemplar.", LOV, SHA_LOV),
    "NB-18": ("forskrift FOR-2018-07-01-1139 § 8", "forskrift/2018-07-01-1139", "§8",
              "Er eit dokument produsert i Noreg, skal den som har produsert det levere "
              "tre eksemplar og utgjevaren fire.", FOR, SHA_FOR),
    "NB-21": ("pliktavleveringslova LOV-1989-06-09-32 § 4", "lov/1989-06-09-32", "§4",
              "Dokument laga i utlandet skal berre avleverast dersom det er laga for norsk "
              "utgjevar eller særskilt tilpassa allmenta i Noreg.", LOV, SHA_LOV),
    "NB-23": ("forskrift FOR-2018-07-01-1139 § 6", "forskrift/2018-07-01-1139", "§6",
              "Utgjevar og importør skal sende inn avleveringseksemplar når dokumentet vert "
              "gjort tilgjengeleg for allmenta, om ikkje noko anna er særskilt fastsett.",
              FOR, SHA_FOR),
}
# Soekt verbatim i begge dokument, ikke funnet. La sta.
UNRESOLVED = {
    "NB-15": "hjemmel er «—» i registeret; ISNI-tildeling er ikke lovregulert",
    "NB-19": "konflikten er nb.no-prosa; både forskrift § 8 og § 11 er kandidater — ikke entydig",
    "NB-20": "«opptrykk» finnes verbatim i hverken loven eller forskriften",
    "NB-22": "«bedriftsinterne» finnes verbatim i hverken loven eller forskriften",
}


def main():
    # --- 4b: LK-12 ---
    p = os.path.join(REG, "data", "lanekassen.yaml")
    d = yaml.safe_load(open(p, encoding="utf-8"))
    f = next(x for x in d["facts"] if x["id"] == "LK-12")
    before = f["review_by"]
    f["review_by"] = "2027-08"          # studiearet 2027/28 starter 1. august
    f["flags"] = sorted(set([x for x in f["flags"] if x != "review_by_mangler"]
                            + ["review_by_satt_til_studiearsstart_2b"]))
    yaml.safe_dump(d, open(p, "w", encoding="utf-8"),
                   allow_unicode=True, sort_keys=False, width=100)
    print(f"4b  LK-12 review_by: {before!r} -> {f['review_by']!r} (studieårsstart 2027/28)")

    # --- 4c: pliktavlevering ---
    p = os.path.join(REG, "data", "nasjonalbiblioteket.yaml")
    d = yaml.safe_load(open(p, encoding="utf-8"))
    n_res = n_flag = 0
    for x in d["facts"]:
        if x["id"] in RESOLVED:
            basis, refid, para, quote, url, prov = RESOLVED[x["id"]]
            old = x["legal_basis"]
            x["legal_basis"] = basis
            x["lovdata_refid"] = refid
            x["lovdata_paragraph"] = para
            x["paragraph_evidence"] = {"quote": quote, "url": url,
                                       "provenance": prov, "verified_at": "2026-10-09"}
            x["flags"] = sorted(set([y for y in x["flags"]
                                     if y != "legal_basis_mangler"]
                                    + ["paragraf_lost_2b_verbatim"]))
            n_res += 1
            print(f"4c  {x['id']}: {old[:34]!r} -> {basis}")
            print(f"        «{quote[:76]}…»")
        elif x["id"] in UNRESOLVED:
            x["flags"] = sorted(set(x["flags"] + ["paragraf_ikke_entydig_2b"]))
            x["paragraph_unresolved_reason"] = UNRESOLVED[x["id"]]
            n_flag += 1
    yaml.safe_dump(d, open(p, "w", encoding="utf-8"),
                   allow_unicode=True, sort_keys=False, width=100)
    print(f"\n4c  {n_res} løst med verbatim belegg, {n_flag} flagget uløst:")
    for k, v in UNRESOLVED.items():
        print(f"      {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
