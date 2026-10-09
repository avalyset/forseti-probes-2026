"""Baklengs-test: finner konsekvenskartet de fem kjente endringene i
lovkart.yaml under endringsvedtak, med riktige registerrader?

Kriteriet fra oppdraget: FOR-2025-12-17-2621 -> {HF-06, HF-09} dukker opp, og
de fire andre med expected_hit treffer. Treff/bom rapporteres per forventet.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import impact as I                                     # noqa: E402

LOVDATA = "/Volumes/Vault/forseti/lovdata"


def main():
    import yaml
    lovkart, by_ref, by_amend = I.load_lovkart()
    register, scen = I.load_register(), I.load_scenarios()
    rows = [json.loads(l) for l in open(os.path.join(LOVDATA, "parsed.jsonl"))]
    by_legacy = {r["legacy_id"]: r for r in rows if r.get("legacy_id")}

    expected = [e for e in lovkart.get("endringsvedtak") or [] if e.get("expected_hit")]
    print(f"{len(expected)} endringsvedtak med expected_hit\n")
    print(f"{'vedtak':24s} {'i arkivet':>10s} {'nivå':>9s} {'forventet':>22s} "
          f"{'funnet':>22s}  utfall")
    print("-" * 104)
    ok = 0
    for e in expected:
        lid = e["legacy_id"]
        d = by_legacy.get(lid)
        if d is None:
            print(f"{lid:24s} {'NEI':>10s} {'—':>9s} "
                  f"{','.join(e['expected_hit']):>22s} {'—':>22s}  BOM (ikke i 2025/2026)")
            continue
        hits = I.impact(d, by_ref, register, scen, by_amend)
        got = sorted({h["row"] for h in hits})
        lvl = "paragraf" if any(h["level"] == "paragraf" for h in hits) else "dokument"
        want = sorted(e["expected_hit"])
        hit = set(want) <= set(got)
        ok += hit
        print(f"{lid:24s} {'ja':>10s} {lvl:>9s} {','.join(want):>22s} "
              f"{','.join(got) or '—':>22s}  {'TREFF' if hit else 'BOM'}")

    print(f"\n{ok}/{len(expected)} forventede treff")
    key = next((e for e in expected if e["legacy_id"] == "FOR-2025-12-17-2621"), None)
    if key:
        d = by_legacy.get("FOR-2025-12-17-2621")
        got = sorted({h["row"] for h in I.impact(d, by_ref, register, scen, by_amend)}) if d else []
        crit = {"HF-06", "HF-09"} <= set(got)
        print(f"\nHOVEDKRITERIUM FOR-2025-12-17-2621 -> HF-06 + HF-09: "
              f"{'BESTÅTT' if crit else 'FEILET'}  (fant {got})")
        print("  Merk: treffet er på DOKUMENTNIVÅ. Vedtaket bærer ingen "
              "data-change-part,\n  så paragrafkjeden rekognoseringen beskrev "
              "(.../§8) finnes ikke i arkivet.")
    return 0 if ok == len(expected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
