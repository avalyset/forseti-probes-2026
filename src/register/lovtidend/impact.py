"""Konsekvenskart: endring i Lovtidend -> berorte registerrader -> scenarier.

To oppslagsniva, og forskjellen er malt, ikke antatt:

  DOKUMENT  changesToDocuments gir «forskrift/2007-06-28-814». Finnes i alle
            ar, i 93,6 % av kunngjoringene (malt pa 2025+2026).
  PARAGRAF  data-change-part gir «.../§8/ledd/3». Finnes i 6,4 %.

Rekognoseringen antok at paragrafnivaet var bredt tilgjengelig «fra 2023».
Det er det ikke. Selve baklengs-testens endring, FOR-2025-12-17-2621, baerer
INGEN change-part - bare dokumentnivaet. Kartet er derfor bygget pa
dokumentniva, med paragraf som presisering nar den finnes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.dirname(HERE)
LOVDATA = "/Volumes/Vault/forseti/lovdata"


def load_lovkart(path=None):
    import yaml
    d = yaml.safe_load(open(path or os.path.join(REG, "lovkart.yaml"), encoding="utf-8"))
    by_ref: Dict[str, Dict[str, Any]] = {}
    for key in ("lover", "forskrifter"):
        for e in d.get(key) or []:
            if e.get("refid"):
                by_ref[e["refid"]] = e
    # Rader hvis HJEMMEL er selve endringsvedtaket, ikke dokumentet det endrer.
    # LK-04 er fasiten for hva LOV-2026-06-19-60 gjor med utdanningsstotteloven
    # § 18; den naas ikke via used_by pa lov/2005-06-03-37. lovkart har en egen
    # struktur for dette - vi bruker den i stedet for aa la raden falle ut.
    by_amend: Dict[str, List[str]] = {}
    for e in d.get("grunnlag_er_endring") or []:
        if e.get("legal_basis"):
            by_amend.setdefault(e["legal_basis"], []).extend(e.get("rows") or [])
    return d, by_ref, by_amend


def load_register():
    import yaml, glob
    out = {}
    for p in sorted(glob.glob(os.path.join(REG, "data", "*.yaml"))):
        for f in yaml.safe_load(open(p, encoding="utf-8"))["facts"]:
            out[f["id"]] = f
    return out


def load_scenarios():
    """registerrad-ID -> scenarier, via expected_facts.yaml sine register-koblinger."""
    import yaml, re
    p = os.path.expanduser("~/ClaudeWork/decision-probe/factcheck/expected_facts.yaml")
    if not os.path.exists(p):
        return {}
    d = yaml.safe_load(open(p, encoding="utf-8"))
    out: Dict[str, List[str]] = {}
    for sc in d["scenarios"]:
        for f in sc["facts"]:
            reg = f.get("register")
            if not isinstance(reg, dict):
                continue
            ref = f"{reg.get('ref','')} {reg.get('text','')}"
            # NDVL-REG-0002 er dokumentnavnet, ikke en registerrad. Uten dette
            # unntaket blir selve registeret talt som en berort rad.
            for rid in re.findall(r"\b([A-ZÆØÅ]+(?:-[A-ZÆØÅ]+)?-\d+)\b", ref):
                if rid.startswith("NDVL-"):
                    continue
                out.setdefault(rid, []).append(f"{sc['id']} [{f['key']}]")
            # klagefrist-tabellen navngir etat, ikke rad-ID
            for etat, rid in (("NAV", "NAV-KLAGE-01"), ("Skatteetaten", "SKATT-KLAGE-01"),
                              ("Lånekassen", "LK-KLAGE-01")):
                if "klagefrist" in (reg.get("ref") or "").lower() and \
                   ref.strip().split("|")[0].strip().endswith(etat):
                    out.setdefault(rid, []).append(f"{sc['id']} [{f['key']}]")
    return {k: sorted(set(v)) for k, v in out.items()}


def impact(doc, by_ref, register, scen, by_amend=None):
    """Hvilke registerrader og scenarier beroeres av en kunngjoring?"""
    refs = set(doc.get("changes_documents") or [])
    paras: Dict[str, set] = {}
    for p in doc.get("change_parts") or []:
        refs.add(p["document"])
        if p.get("paragraph"):
            paras.setdefault(p["document"], set()).add(p["paragraph"])
    hits = []
    for ref in sorted(refs):
        e = by_ref.get(ref)
        if not e:
            continue
        for rid in e.get("used_by") or []:
            f = register.get(rid)
            hits.append({
                "ref": ref, "abbrev": (e.get("abbrev") or [None])[0],
                "row": rid,
                "paragraphs": sorted(paras.get(ref, [])) or None,
                "level": "paragraf" if paras.get(ref) else "dokument",
                "current_value": ([f"{v['value']} {v['unit']}" for v in (f.get("values") or [])]
                                  if f else None),
                "claim": ((f.get("claim") or "")[:90] if f else None),
                "scenarios": scen.get(rid, []),
            })
    # andre vei: rader hvis hjemmel ER dette vedtaket
    for rid in (by_amend or {}).get(doc.get("legacy_id") or "", []):
        if any(h["row"] == rid for h in hits):
            continue
        f = register.get(rid)
        hits.append({
            "ref": doc.get("legacy_id"), "abbrev": None, "row": rid,
            "paragraphs": None, "level": "hjemmel er vedtaket",
            "current_value": ([f"{v['value']} {v['unit']}" for v in (f.get("values") or [])]
                              if f else None),
            "claim": ((f.get("claim") or "")[:90] if f else None),
            "scenarios": scen.get(rid, []),
        })
    return sorted(hits, key=lambda h: h["row"])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed", default=os.path.join(LOVDATA, "parsed.jsonl"))
    ap.add_argument("--years", nargs="*", default=None)
    ap.add_argument("--out", default=os.path.join(HERE, "rapporter", "impact.md"))
    a = ap.parse_args(argv)
    lovkart, by_ref, by_amend = load_lovkart()
    register, scen = load_register(), load_scenarios()
    rows = [json.loads(l) for l in open(a.parsed)]
    if a.years:
        rows = [r for r in rows if any(f"/{y}/" in r["file"] for y in a.years)]

    found = []
    for d in rows:
        h = impact(d, by_ref, register, scen, by_amend)
        if h:
            found.append((d, h))

    L = [f"# Konsekvenskart — Lovtidend avd. I\n",
         f"{len(rows)} kunngjøringer lest. **{len(found)}** treffer registeret.\n",
         f"Oppslagsnivå: dokument (`changesToDocuments`, 93,6 % dekning) med paragraf "
         f"(`data-change-part`, 6,4 %) som presisering der den finnes.\n"]
    for d, h in found:
        L.append(f"\n## {d['legacy_id']} — {(d['title'] or '')[:80]}\n")
        L.append(f"I kraft {d['in_force']} · `{d['file']}`\n")
        L.append("| endrer | nivå | paragraf | rad | registerets verdi | scenarier |")
        L.append("|---|---|---|---|---|---|")
        for x in h:
            L.append(f"| {x['abbrev'] or x['ref']} | {x['level']} | "
                     f"{', '.join(x['paragraphs']) if x['paragraphs'] else '—'} | "
                     f"**{x['row']}** | {', '.join(x['current_value'] or []) or '—'} | "
                     f"{', '.join(x['scenarios']) or '—'} |")
    md = "\n".join(L) + "\n"
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(md)
    print(f"{len(rows)} kunngjøringer, {len(found)} treffer registeret")
    print(f"skrevet {os.path.relpath(a.out, REG)}")
    json.dump([{"legacy_id": d["legacy_id"], "hits": h} for d, h in found],
              open(a.out.replace(".md", ".json"), "w"), indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
