"""Løs registerets legal_basis-prosa mot lovkart.yaml og skriv tabellen.

Dette er IKKE 2b-mekanismen. Den henter ingenting, sammenligner ingenting og
vet ikke hva en endring er. Den gjør én ting: slår hver av de 121 radenes
`legal_basis` opp i lovkart.yaml og rapporterer hva som lot seg løse til
(dokument, paragraf) — og hva som ikke lot seg løse.

Grunnen til at den finnes framfor en håndskrevet tabell: lovkart.yaml lister
radene per dokument, og registeret kan endres uavhengig. Uten en kontroll vil
de to drive fra hverandre uten at noen ser det. `--check` feiler hvis en rad
har falt ut, dukket opp eller er dekket to steder.

  python resolve_lovkart.py            # skriv tabellen til stdout
  python resolve_lovkart.py --check    # bare konsistens; exit 1 ved avvik
  python resolve_lovkart.py --markdown docs/forkortelser-lovdata.md
"""
import argparse
import glob
import os
import re
import sys
from collections import defaultdict

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))

# «§ 4-1-13», «§ 6-5-4», «§ 10-4», «§§ 77/78/80/81», «§ 1»
PARA = re.compile(r"§+\s*(\d+(?:-\d+)*(?:\s*/\s*\d+(?:-\d+)*)*)")
LEDD = re.compile(
    r"\b(første|andre|annet|tredje|fjerde|femte|sjette|sjuende|syvende)\s+ledd"
)


def load_register():
    rows = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "*.yaml"))):
        doc = yaml.safe_load(open(path, encoding="utf-8"))
        for fact in doc["facts"]:
            rows[fact["id"]] = {
                "domain": fact.get("domain"),
                "legal_basis": fact.get("legal_basis"),
                "trigger": fact.get("review_trigger"),
                "status": fact.get("register_status"),
            }
    return rows


def load_lovkart():
    return yaml.safe_load(open(os.path.join(ROOT, "lovkart.yaml"), encoding="utf-8"))


def index_documents(kart):
    """row_id -> dokumentpost, fra used_by og arv."""
    by_row = {}
    docs = {}
    for group in ("lover", "forskrifter"):
        for entry in kart.get(group) or []:
            docs[entry["refid"]] = entry
            for row in entry.get("used_by") or []:
                by_row.setdefault(row, []).append(entry)
    # Arv gir dokument til rader som bare har «§ x-y». De står allerede i
    # used_by, så dette er en kontroll av at de to er enige, ikke et tillegg.
    inherited = {}
    for rule in kart.get("arv") or []:
        for row in rule["rows"]:
            inherited[row] = rule["document"]
    # Rader der legal_basis er endringsvedtaket selv: løses til målet.
    as_change = {}
    for rule in kart.get("grunnlag_er_endring") or []:
        for row in rule["rows"]:
            as_change[row] = rule
            by_row.setdefault(row, []).append(docs[rule["target_document"]])
    return by_row, docs, inherited, as_change


def ledd_of(text, ordenstall):
    m = LEDD.search(text or "")
    return ordenstall.get(m.group(1)) if m else None


def paragraphs_of(text):
    if not text:
        return []
    out = []
    for m in PARA.finditer(text):
        for part in re.split(r"\s*/\s*", m.group(1)):
            if part and part not in out:
                out.append(part)
    return out


def resolve(rows, kart):
    by_row, docs, inherited, as_change = index_documents(kart)
    ordenstall = kart["ordenstall"]

    excluded = {}
    for bucket, reason in (("ikke_lovtekst", "ikke lovtekst"), ("tvetydig", "tvetydig")):
        for entry in kart.get(bucket) or []:
            for row in entry["rows"]:
                excluded.setdefault(row, reason)

    resolved = []
    for row_id, row in sorted(rows.items(), key=lambda kv: (kv[0].split("-")[0], kv[0])):
        entries = by_row.get(row_id, [])
        paras = paragraphs_of(row["legal_basis"])
        change = as_change.get(row_id)
        if change:
            # Paragrafen står i radens claim, ikke i hjemmelsfeltet.
            paras = [change["target_paragraph"]]
        rec = {
            "row": row_id,
            "domain": row["domain"],
            "legal_basis": row["legal_basis"],
            "trigger": row["trigger"],
            "documents": [e["refid"] for e in entries],
            "doc_status": [e["status"] for e in entries],
            "paragraphs": paras,
            "ledd": ledd_of(row["legal_basis"], ordenstall),
            "inherited": inherited.get(row_id),
            "excluded": excluded.get(row_id),
            "via_change": change["legal_basis"] if change else None,
        }
        if rec["excluded"] == "ikke lovtekst":
            # Blandet grunnlag: feltet bærer BÅDE en paragraf og noe som ikke
            # er lovtekst. Paragrafdelen kan følges, så raden er ikke utenfor —
            # den er delvis dekket, og resten må følges som side.
            rec["verdict"] = "DELVIS" if (entries and paras) else "UTENFOR"
        elif not entries:
            rec["verdict"] = "ULØST"
        elif not paras:
            rec["verdict"] = "DOKUMENT"      # dokument kjent, paragraf mangler
        elif rec["excluded"] == "tvetydig":
            rec["verdict"] = "TVETYDIG"
        else:
            rec["verdict"] = "LØST"
        resolved.append(rec)
    return resolved, docs


def check(rows, resolved, kart):
    """Konsistens mellom register og lovkart. Returnerer liste med feil."""
    errors = []
    known = set(rows)

    cited = defaultdict(list)
    for group in ("lover", "forskrifter"):
        for entry in kart.get(group) or []:
            for row in entry.get("used_by") or []:
                cited[row].append(entry["refid"])
    for bucket in ("tvetydig", "ikke_lovtekst", "arv", "grunnlag_er_endring"):
        for entry in kart.get(bucket) or []:
            for row in entry["rows"]:
                if row not in known:
                    errors.append(f"{bucket}: rad {row} finnes ikke i registeret")

    for row, refs in cited.items():
        if row not in known:
            errors.append(f"used_by: rad {row} finnes ikke i registeret")
        elif len(refs) > 1 and row not in {"SKATT-17", "LK-10", "LK-11", "LK-21", "NB-17"}:
            # Disse fem har med rette to grunnlag i samme felt.
            errors.append(f"rad {row} er dekket av flere dokumenter: {refs}")

    for rec in resolved:
        if rec["inherited"] and rec["inherited"] not in rec["documents"]:
            errors.append(
                f"rad {rec['row']}: arv sier {rec['inherited']}, "
                f"used_by sier {rec['documents']}"
            )

    accounted = (set(cited)
                 | {r["row"] for r in resolved if r["excluded"]}
                 | {r["row"] for r in resolved if r["via_change"]})
    for row in sorted(known - accounted):
        errors.append(f"rad {row} er ikke nevnt noe sted i lovkart.yaml")
    return errors


def markdown(resolved, docs, kart):
    counts = defaultdict(int)
    for rec in resolved:
        counts[rec["verdict"]] += 1

    out = []
    w = out.append
    w("# Forkortelsestabell: registerets paragrafhenvisninger → Lovdata")
    w("")
    w(f"Generert av `src/register/resolve_lovkart.py` fra `src/register/lovkart.yaml`")
    w(f"og de {len(resolved)} radene i `src/register/data/*.yaml`. Rediger kartet, ikke tabellen.")
    w("")
    w("## Dokumentene")
    w("")
    w("| Forkortelse i registeret | Fullt navn | Lovdata-ID | refid | Status | Rader |")
    w("|---|---|---|---|---|---|")
    for group in ("lover", "forskrifter"):
        for e in kart.get(group) or []:
            abbrev = ", ".join(f"`{a}`" for a in (e.get("abbrev") or [])) or "—"
            title = (e.get("title") or "— (tittel ikke funnet)").strip().replace("\n", " ")
            used = e.get("used_by") or []
            w(
                f"| {abbrev} | {title} | `{e['legacy_id']}` | `{e['refid']}` "
                f"| {e['status']} | {len(used)} |"
            )
    w("")
    w("**Status:** `registerfestet` = IDen står i registerets egen legal_basis. ")
    w("`korroborert` = bekreftet mot Lovdata-side via søk, ikke lest direkte. ")
    w("`ubekreftet` = ikke bekreftet; må slås opp.")
    w("")
    w("## Per rad")
    w("")
    w(f"LØST {counts['LØST']} · DOKUMENT {counts['DOKUMENT']} · "
      f"DELVIS {counts['DELVIS']} · TVETYDIG {counts['TVETYDIG']} · "
      f"ULØST {counts['ULØST']} · UTENFOR {counts['UTENFOR']}")
    w("")
    w("| Rad | Trigger | legal_basis (ordrett) | Dokument | Paragraf | Ledd | Utfall |")
    w("|---|---|---|---|---|---|---|")
    for rec in resolved:
        lb = rec["legal_basis"]
        lb = "—" if lb is None else f"`{lb}`".replace("|", "\\|")
        doc = ", ".join(f"`{d}`" for d in rec["documents"]) or "—"
        paras = ", ".join(f"§ {p}" for p in rec["paragraphs"]) or "—"
        ledd = rec["ledd"] or "—"
        arv = " *(arvet)*" if rec["inherited"] else ""
        if rec["via_change"]:
            arv += f" *(mål for {rec['via_change']})*"
        w(
            f"| {rec['row']} | {rec['trigger']} | {lb} | {doc}{arv} | {paras} "
            f"| {ledd} | **{rec['verdict']}** |"
        )
    w("")
    w("**Utfall:** `LØST` = dokument og paragraf funnet. ")
    w("`DOKUMENT` = dokument funnet, paragraf mangler i registeret — kan bare ")
    w("flagges på dokumentnivå. `DELVIS` = feltet bærer både en paragraf og et ")
    w("grunnlag som ikke er lovtekst; paragrafdelen kan følges, resten ikke. ")
    w("`TVETYDIG` = krever et menneske, se `tvetydig` i lovkart.yaml. ")
    w("`ULØST` = ingen kobling. `UTENFOR` = grunnlaget er ikke lovtekst og kan ")
    w("ikke treffes av en lovendring.")
    w("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="bare konsistens")
    ap.add_argument("--markdown", metavar="STI", help="skriv tabellen til fil")
    args = ap.parse_args()

    rows = load_register()
    kart = load_lovkart()
    resolved, docs = resolve(rows, kart)
    errors = check(rows, resolved, kart)

    if errors:
        print(f"{len(errors)} avvik mellom register og lovkart:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
    else:
        print(f"lovkart stemmer med registeret: {len(rows)} rader dekket",
              file=sys.stderr)

    counts = defaultdict(int)
    for rec in resolved:
        counts[rec["verdict"]] += 1
    print(
        "  ".join(f"{k} {counts[k]}" for k in
                 ("LØST", "DOKUMENT", "DELVIS", "TVETYDIG", "ULØST", "UTENFOR")),
        file=sys.stderr,
    )

    if args.check:
        return 1 if errors else 0

    text = markdown(resolved, docs, kart)
    if args.markdown:
        with open(args.markdown, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"skrevet: {args.markdown}", file=sys.stderr)
    else:
        print(text)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
