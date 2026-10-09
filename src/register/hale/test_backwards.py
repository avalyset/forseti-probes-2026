"""Baklengs-test: finner halen G-endringen 130 160 -> 136 549, og INGEN andre?

To ekte snapshots av nav.no/grunnbelopet:
  for  = Wayback 2026-04-14 (G var 130 160; 136 549 finnes ikke pa siden)
  etter = levende side hentet 2026-10-09 (G er 136 549)

Kriteriet fra oppdraget, ordrett: «halen finner 130 160 -> 136 549 og
foreslar det; foreslar ingen andre verdier.»
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import diff as D        # noqa: E402
import extract as X     # noqa: E402
import fetch as F       # noqa: E402
import propose as P     # noqa: E402

BEFORE = os.path.join(HERE, "snapshots", "NAV-01", "backtest_2026-04-14.html")
AFTER = os.path.join(HERE, "snapshots", "NAV-01", "backtest_2026-10-09.html")


def main():
    fact = F.load_rows(["NAV-01"])["NAV-01"]
    facts_all = P.all_facts()
    old = open(BEFORE, "rb").read()
    new = open(AFTER, "rb").read()
    added, removed = D.changed_blocks(old, new)
    print(f"endrede blokker: {len(added)} lagt til / endret, {len(removed)} fjernet")

    # Malbasert uttrekk mot hele den nye teksten: registerets verbatim-sitat
    # er monsteret. Keyword-naerhet alene ga 190 kandidater, fordi siden
    # lister G tilbake til 1967 og hver historisk verdi ligger «NOK naer
    # grunnbelopet».
    cands = X.template_candidates(D.to_text(new), fact)
    print(f"kandidater (mal): {len(cands)}  -> {[c['value'] for c in cands]}")
    kw = []
    for b in added:
        kw += X.candidates(b, fact)
    print(f"til sammenligning, keyword-naerhet alene: {len(kw)} kandidater")
    for c in cands:
        print(f"  {c['value']:>10g} {c['unit']:8s} «{c['span'][:62]}»")

    # NAV-01 i registeret har allerede hele historikken, inkludert 136 549.
    # For en aerlig baklengs-test ma registeret se ut som det gjorde FOR
    # endringen: bare verdier gyldige til og med 2026-04-14.
    pre = dict(fact)
    pre["values"] = [v for v in fact["values"] if (v.get("valid_from") or "") <= "2026-04-14"]
    facts_pre = []
    for f in facts_all:
        g = dict(pre) if f["id"] == "NAV-01" else dict(f)
        if f["id"] != "NAV-01":
            g["values"] = [v for v in (f.get("values") or [])
                           if (v.get("valid_from") or "2000-01-01") <= "2026-04-14"]
        facts_pre.append(g)
    print(f"\nregisteret rullet tilbake til 2026-04-14: NAV-01 har "
          f"{[v['value'] for v in pre['values']]}")

    fails = []
    for label, allow in [("A: bokstavelig (verdien ma sta som VERDI i >=2 rader)", False),
                         ("B: operativ (verdien nevnt i >=2 raders verbatim claim)", True)]:
        print(f"\n--- port {label} ---")
        res = [P.propose(pre, c, "https://www.nav.no/grunnbelopet",
                         valid_from="2026-05-01", facts=facts_pre,
                         allow_claim_text=allow) for c in cands]
        forslag = [r for r in res if r["kind"] == "forslag"]
        saker = [r for r in res if r["kind"] == "sak"]
        for r in forslag:
            print(f"  FORSLAG {r['previous']:g} -> {r['value']:g} {r['unit']} "
                  f"({r['change']:+.2%}) bekreftet av {r['supporting_rows']}")
        for r in saker:
            print(f"  sak     {r['value']:g} {r['unit']}: {'; '.join(r['reasons'])}")
        hit = [r for r in forslag if r["value"] == 136549.0]
        ok_find = bool(hit) and hit[0]["previous"] == 130160.0
        ok_only = len(forslag) == 1
        print(f"  finner 130 160 -> 136 549 og foreslar det: {'JA' if ok_find else 'NEI'}")
        print(f"  foreslar ingen andre verdier:              "
              f"{'JA' if ok_only else f'NEI ({len(forslag)})'}")
        if allow and not (ok_find and ok_only):
            fails.append("port B oppfyller ikke kriteriet")

    print("\n=== KRITERIUM, ordrett: «halen finner 130 160 -> 136 549 og foreslar")
    print("    det; foreslar ingen andre verdier.» ===")
    print(f"  {'BESTATT under port B' if not fails else 'FEILET: ' + '; '.join(fails)}")
    print("\n  MERK: port A kan aldri fyre for en NY sats - en fersk verdi finnes")
    print("  per konstruksjon i null registerrader. Port B teller bekreftelse fra")
    print("  andre raders verbatim claim (NAV-02/03 sine kontrollregninger, fra")
    print("  nav.no/aap). I DENNE baklengs-testen er de claim-tekstene skrevet i")
    print("  oktober 2026, altsa ETTER april-kuttet - det er lekkasje fra framtiden,")
    print("  og port B er derfor ikke uavhengig validert her.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
