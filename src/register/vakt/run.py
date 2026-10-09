"""Metningsvakt, ett lop.  python run.py --as-of 2026-10-09

Skriver en markdown-rapport med toppseksjon og de fire vaktene.
Ingen klokke: --as-of er pakrevd, og koden sporr aldri systemet hva dagen er.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks as C                                     # noqa: E402


def render(r) -> str:
    s, L = r["summary"], []
    a = L.append
    a(f"# Metningsvakt — as of {r['as_of']}\n")
    a(f"| | |\n|---|---|")
    a(f"| fakta i registeret | **{s['n_facts']}** |")
    a(f"| med minst én verdi | {s['with_value']} ({s['share_value']:.1%}) |")
    a(f"| med kildesitat | {s['with_quote']} ({s['share_quote']:.1%}) |")
    a(f"| utløpt review_by | **{s['expired']}** ({s['share_expired']:.1%}) |")
    fired = [v["name"] for v in (r["v1"], r["v2"], r["v3"], r["v4"]) if v["fired"]]
    a(f"\n**Vakter som fyrer: {len(fired)} av 4**"
      + (f" — {', '.join(fired)}" if fired else " — ingen"))

    v1 = r["v1"]
    a(f"\n## {v1['name']}\n")
    if v1["expired"]:
        a(f"{len(v1['expired'])} fakta har passert `review_by`.\n")
        a("| id | domene | review_by | dager over | trigger |\n|---|---|---|---|---|")
        for x in v1["expired"][:25]:
            a(f"| {x['id']} | {x['domain']} | {x['review_by']} | "
              f"**{x['days_overdue']}** | {x['trigger']} |")
        if len(v1["expired"]) > 25:
            a(f"\n…og {len(v1['expired'])-25} til.")
    else:
        a("Ingen utløpte fakta.")
    if v1["annual_without_review_by"]:
        a(f"\n**FEIL — {len(v1['annual_without_review_by'])} ÅRLIG-fakta uten "
          f"`review_by`.** En årlig sats uten forfallsdato kan ikke gå ut på dato, "
          f"og ser derfor evig frisk ut.\n")
        a("| id | domene | påstand |\n|---|---|---|")
        for x in v1["annual_without_review_by"]:
            a(f"| {x['id']} | {x['domain']} | {x['claim']} |")

    v2 = r["v2"]
    a(f"\n## {v2['name']}\n")
    if v2["per_pack"]:
        a(f"**{v2['total']}** tall i pakkenes `expected_behavior` finnes ikke i "
          f"registeret. Det er hullet som lot 130 030 stå.\n")
        a(f"Av {v2['total_raw']} UKJENT-rader fra `check_packs` er "
          f"{v2['years_excluded']} årstall (`for 2026`) og "
          f"{v2['phones_excluded']} telefonnumre (116 123, 23 32 70 00). Ingen av "
          f"dem er satser registeret skal dekke. De er skilt ut her, ikke "
          f"filtrert bort i `check_packs`.\n")
        a("| pakke | hull | årstall | telefon | eksempler |\n|---|---|---|---|---|")
        for x in v2["per_pack"]:
            ex = ", ".join(f"{e['value']:.0f}" for e in x["examples"])
            a(f"| {x['pack']} | **{x['n']}** | {x['n_years_excluded']} | "
              f"{x['n_phones_excluded']} | {ex} |")
    else:
        a("Registeret dekker hvert tall pakkene påstår.")

    v3 = r["v3"]
    a(f"\n## {v3['name']}\n")
    if v3["fired"]:
        if v3["last_fetch_failed"]:
            a(f"**{len(v3['last_fetch_failed'])} med mislykket siste henting:**\n")
            a("| id | url |\n|---|---|")
            for x in v3["last_fetch_failed"]:
                a(f"| {x['id']} | {x['url'][:62]} |")
        if v3["never_fetched"]:
            a(f"\n**{len(v3['never_fetched'])} aldri hentet:**\n")
            a("| id | url |\n|---|---|")
            for x in v3["never_fetched"][:20]:
                a(f"| {x['id']} | {x['url'][:62]} |")
            if len(v3["never_fetched"]) > 20:
                a(f"\n…og {len(v3['never_fetched'])-20} til.")
        if v3.get("not_a_url"):
            a(f"\n**{len(v3['not_a_url'])} har en kildereferanse som ikke er en "
              f"hentbar URL** (`korpus sha256 …`, `Vault lov/...xml`). De er "
              f"sporbare, men halen kan ikke GET-e dem, så de kan heller ikke "
              f"overvåkes.\n")
            a("| id | kilde |\n|---|---|")
            for x in v3["not_a_url"][:15]:
                a(f"| {x['id']} | {x['source']} |")
            if len(v3["not_a_url"]) > 15:
                a(f"\n…og {len(v3['not_a_url'])-15} til.")
        if v3["stale"]:
            a(f"\n**{len(v3['stale'])} eldre enn {v3['stale_days']} dager:**\n")
            a("| id | siste snapshot | dager |\n|---|---|---|")
            for x in v3["stale"][:20]:
                a(f"| {x['id']} | {x['last_snapshot']} | **{x['age_days']}** |")
            if len(v3["stale"]) > 20:
                a(f"\n…og {len(v3['stale'])-20} til.")
    else:
        a(f"Alle kilder hentet innen {v3['stale_days']} dager, siste henting OK.")

    v4 = r["v4"]
    a(f"\n## {v4['name']}\n")
    if v4["silent"]:
        a(f"{len(v4['silent'])} ÅRLIG-fakta der kalenderdatoen har passert uten at "
          f"halen har hentet. Stillhet er ikke det samme som uendret.\n")
        a("| id | forfall | siste snapshot | grunn |\n|---|---|---|---|")
        for x in v4["silent"]:
            a(f"| {x['id']} | {x['due'] or '—'} | {x['last_snapshot'] or '—'} | {x['why']} |")
    else:
        a("Ingen stille ÅRLIG-fakta.")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True, help="YYYY-MM-DD (ingen klokke i koden)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    as_of = dt.date.fromisoformat(a.as_of)
    r = C.run_all(as_of)
    md = render(r)
    out = a.out or os.path.join(HERE, "rapporter", f"vakt_{a.as_of}.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(md)
    print(md)
    print(f"[skrevet {os.path.relpath(out, HERE)}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
