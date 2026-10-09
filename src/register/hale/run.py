"""Halen, ett lop.  python run.py --as-of 2026-06-01

Kjorer BARE rader som har passert kalenderdatoen sin. Ingen cron i denne
runden - datoen er et eksplisitt argument.

Feiler hoyt: manglende URL, 404, endret struktur (tom tekst), tomt resultat
-> sak. Aldri stille.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fetch as F            # noqa: E402
import diff as D             # noqa: E402
import extract as X          # noqa: E402
import propose as P          # noqa: E402

CAL = os.path.join(HERE, "calendar.yaml")


def due(row_id: str, as_of: dt.date, cal: dict) -> tuple[bool, str]:
    spec = (cal.get("rows") or {}).get(row_id)
    if not spec:
        return True, "ingen kalenderoppforing - kjores"
    d = dt.date(as_of.year, int(spec["month"]), int(spec["day"]))
    if as_of >= d:
        return True, f"passert {d.isoformat()}"
    return False, f"ikke passert {d.isoformat()} enna"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--rows", nargs="*", default=None)
    ap.add_argument("--no-fetch", action="store_true",
                    help="bruk snapshotene som alt ligger der")
    a = ap.parse_args(argv)
    as_of = dt.date.fromisoformat(a.as_of)
    cal = yaml.safe_load(open(CAL, encoding="utf-8"))
    facts = F.load_rows(a.rows)

    print(f"=== halen, as-of {as_of} ===")
    run_ids, skipped = [], []
    for rid in sorted(facts):
        ok, why = due(rid, as_of, cal)
        (run_ids if ok else skipped).append((rid, why))
    for rid, why in skipped:
        print(f"  {rid:9s} hoppet over: {why}")
    print(f"  {len(run_ids)} rader kjores, {len(skipped)} hoppet over\n")

    if not a.no_fetch:
        print("--- henter ---")
        F.main(["--rows"] + [r for r, _ in run_ids])
        print()

    print("--- diff og kandidater ---")
    forslag, saker, uendret = [], [], []
    for rid, _ in run_ids:
        snaps = F.latest_two(rid)
        if len(snaps) < 2:
            p = P.sak(rid, "no_previous_snapshot",
                      f"bare {len(snaps)} snapshot - ingenting aa diffe mot")
            saker.append({"row_id": rid, "kind": "no_previous_snapshot"})
            print(f"  {rid:9s} SAK: bare {len(snaps)} snapshot")
            continue
        new, old = snaps[0], snaps[1]
        if new["sha256"] == old["sha256"]:
            print(f"  {rid:9s} uendret (samme sha256)")
            uendret.append(rid)
            continue
        nb = open(new["path"], "rb").read()
        ob = open(old["path"], "rb").read()
        if not D.to_text(nb).strip():
            P.sak(rid, "empty_after_strip",
                  "siden ga tom tekst etter tagg-stripping - endret struktur?",
                  sha256=new["sha256"])
            saker.append({"row_id": rid, "kind": "empty_after_strip"})
            print(f"  {rid:9s} SAK: tom tekst etter stripping")
            continue
        added, _removed = D.changed_blocks(ob, nb)
        # Malbasert uttrekk mot HELE den nye teksten: registerets eget
        # verbatim-sitat er det presise monsteret. Faller det igjennom,
        # brukes keyword-naerhet pa de endrede blokkene.
        cands = X.template_candidates(D.to_text(nb), facts[rid])
        if not cands:
            for b in added:
                cands += X.candidates(b, facts[rid])
            for c in cands:
                c["via"] = "keyword"
        if not cands:
            P.sak(rid, "no_candidate",
                  f"{len(added)} endrede blokker, men ingen kandidatverdi med "
                  f"riktig enhet naer et nokkelord fra claim",
                  n_changed_blocks=len(added))
            saker.append({"row_id": rid, "kind": "no_candidate"})
            print(f"  {rid:9s} SAK: {len(added)} endrede blokker, 0 kandidater")
            continue
        best = cands[0]
        res = P.propose(facts[rid], best, new["final_url"])
        if res["kind"] == "forslag":
            forslag.append(res)
            print(f"  {rid:9s} FORSLAG {res['previous']:g} -> {res['value']:g} "
                  f"{res['unit']} ({res['change']:+.2%}), "
                  f"bekreftet av {res['supporting_rows']}")
        elif res["kind"] == "sak":
            saker.append(res)
            print(f"  {rid:9s} SAK: {res['value']:g} {res['unit']} - "
                  f"{'; '.join(res['reasons'])}")
        else:
            uendret.append(rid)
            print(f"  {rid:9s} uendret ({res['value']:g})")

    print(f"\n=== oppsummering ===")
    print(f"  forslag  {len(forslag)}")
    print(f"  saker    {len(saker)}")
    print(f"  uendret  {len(uendret)}")
    return {"forslag": forslag, "saker": saker, "uendret": uendret}


if __name__ == "__main__":
    main()
