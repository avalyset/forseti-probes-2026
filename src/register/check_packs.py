"""Slaa pakkenes tallpastander opp mot faktaregisteret for datoen de pastar.

Leser vare atte pakker fra simpleaudit (via `git show <ref>:<sti>`, uten aa roere
arbeidstreet), henter hvert belop ut av expected_behavior og metadata (inkl.
metadata.facts der den finnes - den ligger i apen PR, ikke i dev), bestemmer
hvilken dato pastanden gjelder, og sammenligner mot registeret.

Tre utfall per tall:
  OK        - verdien star i registeret for dette domenet, gyldig pa den datoen
  AVVIK     - FORELDET: verdien finnes i registeret, men var gyldig pa en ANNEN
              dato enn den pastanden gjelder. Hoy tillit: bade verdien og
              datoen er registerfestet.
  MISTANKE  - NAER-BOM: tallet ligger innenfor <=5 % av en registerverdi som
              gjelder den datoen, uten aa vaere den. HEURISTIKK med kjent falsk
              positiv: et scenario-internt hypotetisk tall (f.eks. «brukerens
              inntekt pa 850 000 kr») kan tilfeldigvis ligge naer en sats.
              Maa leses, ikke stoles blindt pa.
  UKJENT    - tallet finnes ikke i registeret for domenet. Registeret er
              ufullstendig (75 av 118 rader har ingen uttrekkbar verdi), sa
              UKJENT er IKKE en pastand om at tallet er feil.

Bruk:  python check_packs.py <git-ref>     f.eks. upstream/dev eller 32c494f
"""
import ast, json, os, re, subprocess, sys, glob
from datetime import date
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.expanduser("~/ClaudeWork/simpleaudit")
PACKS = {"nav_aap": "nav", "skatteetaten": "skatteetaten", "helfo": "helfo",
         "lanekassen": "lanekassen", "nb_kryss_ordning": "nasjonalbiblioteket",
         "skatteetaten_legitimasjon": "skatteetaten",
         "toll_reisegodskvote": "tolletaten",
         "arbeidstilsynet_arbeidstid": "arbeidstilsynet"}
NEAR_BAND = 0.05           # <=5 % fra en gjeldende registerverdi = naer-bom
MIN_DIGITS = 4             # bare belop; sma tall (paragrafnr, alder) er for generelle
MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"])}
MONTHS.update({m: i + 1 for i, m in enumerate(
    ["januar", "februar", "mars", "april", "mai", "juni", "juli", "august",
     "september", "oktober", "november", "desember"])})


def load_register():
    idx = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "*.yaml"))):
        d = yaml.safe_load(open(p, encoding="utf-8"))
        for f in d["facts"]:
            for v in f["values"]:
                if not isinstance(v["value"], (int, float)):
                    continue
                idx.setdefault(f["domain"], []).append({
                    "fact_id": f["id"], "value": float(v["value"]), "unit": v["unit"],
                    "valid_from": v.get("valid_from"), "valid_to": v.get("valid_to"),
                    "context": v.get("context", f["claim"][:100]),
                })
    return idx


def git_show(ref, path):
    return subprocess.run(["git", "show", f"{ref}:{path}"], cwd=REPO,
                          capture_output=True, text=True, check=True).stdout


def scenarios_from(src, name):
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id.endswith("_SCENARIOS"):
                    return ast.literal_eval(node.value)
    raise RuntimeError(f"ingen *_SCENARIOS i {name}")


def texts_of(sc):
    """Alle tekstbiter der en tallpastand kan sta."""
    out = list(sc.get("expected_behavior", []))
    md = sc.get("metadata", {}) or {}
    for k in ("rationale", "note", "notes"):
        if isinstance(md.get(k), str):
            out.append(md[k])
    facts = md.get("facts")        # finnes bare der PR #103 er inne
    if isinstance(facts, list):
        for fct in facts:
            if isinstance(fct, dict):
                out.append(json.dumps(fct, ensure_ascii=False))
            elif isinstance(fct, str):
                out.append(fct)
    return out


def claimed_date(text, fallback):
    """Dato pastanden gjelder, lest ut av SAMME tekstbit. Gjetter ikke utover det."""
    m = re.search(r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+(\d{4})", text, re.I)
    if m:
        return date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))), "eksplisitt dato"
    m = re.search(r"\b(?:in|for|i|per)\s+(20\d{2})\b", text, re.I)
    if m:
        return date(int(m.group(1)), 7, 1), f"ar {m.group(1)} (midt i aret)"
    m = re.search(r"\b(20\d{2})\b", text)
    if m:
        return date(int(m.group(1)), 7, 1), f"ar {m.group(1)} (midt i aret)"
    return fallback, "fallback: metadata.date_created"


def applicable(entries, when):
    out = []
    for e in entries:
        vf = date.fromisoformat(e["valid_from"]) if e["valid_from"] else None
        vt = date.fromisoformat(e["valid_to"]) if e["valid_to"] else None
        if vf and when < vf:
            continue
        if vt and when > vt:
            continue
        out.append(e)
    return out


NUM = re.compile(r"(?<![\d.,])(\d[\d   ]{2,}\d|\d{4,})(?![\d])")

# Utelukkelser, lagt til ETTER aa ha malt falske positive mot upstream/dev.
# ID-SIFRE: tallet er del av en regel- eller forskrifts-ID (FOR-2024-12-19-3293,
#   LOV-1967-02-10). Ikke et belop.
ID_CTX = re.compile(r"(?:FOR|LOV|FORSKRIFT|PROP|NOU)[-\s]?\d{4}[-\d]*$", re.I)
# MOTEKSEMPEL: pakken sier SELV at tallet er galt («Gir ikke feil grense (f.eks.
#   100 000 NOK ...)»). Da er treffet pakkens egen negative kontroll.
COUNTEREX = re.compile(r"(?:gir ikke feil|ikke feil|bruker ikke feil"
                       r"|oppgir ikke feil|unngaar|feil (?:sats|grense|frist|belop))",
                       re.I)


def excluded(text, m):
    """Grunn til aa hoppe over treffet, eller None."""
    before = text[max(0, m.start() - 26):m.start()].strip()
    if ID_CTX.search(before):
        return "del_av_regel_id"
    if COUNTEREX.search(text[max(0, m.start() - 95):m.end()]):
        return "pakkens_eget_moteksempel"
    return None



def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else "upstream/dev"
    reg = load_register()
    print(f"=== check_packs mot ref {ref} ===")
    print(f"register: {sum(len(v) for v in reg.values())} verdier over "
          f"{len(reg)} domener\n")
    rows, counts = [], {"OK": 0, "AVVIK": 0, "MISTANKE": 0, "UKJENT": 0, "UTELATT": 0}
    excl = []

    excl = []
    for pack, dom in PACKS.items():
        try:
            src = git_show(ref, f"simpleaudit/scenarios/{pack}.py")
        except subprocess.CalledProcessError:
            print(f"  {pack}: finnes ikke i {ref} - hoppet over")
            continue
        scs = scenarios_from(src, pack)
        entries = reg.get(dom, [])
        for si, sc in enumerate(scs):
            created = (sc.get("metadata", {}) or {}).get("date_created")
            fb = date.fromisoformat(created) if created else date(2026, 7, 1)
            for text in texts_of(sc):
                for m in NUM.finditer(text):
                    raw = re.sub(r"[   ]", "", m.group(1))
                    if len(raw) < MIN_DIGITS:
                        continue
                    why = excluded(text, m)
                    if why:
                        counts["UTELATT"] += 1
                        excl.append({"pack": pack, "value": float(raw), "grunn": why,
                                     "snippet": " ".join(
                                         text[max(0, m.start()-55):m.end()+55].split())})
                        continue
                    val = float(raw)
                    when, how = claimed_date(text, fb)
                    app = applicable(entries, when)
                    exact_app = [e for e in app if abs(e["value"] - val) < 0.5]
                    if exact_app:
                        verdict, detail = "OK", exact_app[0]["fact_id"]
                    else:
                        exact_any = [e for e in entries if abs(e["value"] - val) < 0.5]
                        if exact_any:
                            e = exact_any[0]
                            verdict = "AVVIK"
                            detail = (f"FORELDET: {e['fact_id']} hadde {val:.0f} gyldig "
                                      f"{e['valid_from']}..{e['valid_to'] or 'na'}, men "
                                      f"pastanden gjelder {when}")
                        else:
                            near = [e for e in app if e["value"] > 0 and
                                    abs(e["value"] - val) / e["value"] <= NEAR_BAND]
                            if near:
                                e = min(near, key=lambda q: abs(q["value"] - val))
                                verdict = "MISTANKE"
                                detail = (f"NAER-BOM: registeret har {e['value']:.0f} "
                                          f"({e['fact_id']}, gyldig fra {e['valid_from']}), "
                                          f"pakken sier {val:.0f} "
                                          f"({abs(e['value']-val)/e['value']:+.2%})")
                            else:
                                verdict, detail = "UKJENT", "ikke i registeret for domenet"
                    counts[verdict] += 1
                    rows.append({"pack": pack, "domain": dom, "scenario": sc.get("name", f"#{si}"),
                                 "value": val, "when": when.isoformat(), "date_source": how,
                                 "verdict": verdict, "detail": detail,
                                 "snippet": " ".join(text[max(0, m.start()-55):m.end()+55].split())})

    for tier in ("AVVIK", "MISTANKE"):
        sel = [r for r in rows if r["verdict"] == tier]
        print(f"--- {tier} ({len(sel)}) ---" if sel else f"--- {tier}: ingen ---")
        for r in sel:
            print(f"  {r['pack']:26s} {r['value']:10.0f}")
            print(f"      scenario: {r['scenario'][:70]}")
            print(f"      {r['detail']}")
            print(f"      «…{r['snippet'][:115]}…»")
        print()
    if excl:
        print(f"--- UTELATT ({len(excl)}), ikke belopspastander ---")
        for e in excl:
            print(f"  {e['pack']:26s} {e['value']:10.0f}  [{e['grunn']}]")
            print(f"      «…{e['snippet'][:110]}…»")
        print()
    if excl:
        print(f"--- UTELATT ({len(excl)}), ikke belopspastander ---")
        for e in excl:
            print(f"  {e['pack']:26s} {e['value']:10.0f}  [{e['grunn']}]")
            print(f"      «…{e['snippet'][:110]}…»")
        print()
    print(f"oppsummering: OK {counts['OK']}   AVVIK {counts['AVVIK']}   "
          f"MISTANKE {counts['MISTANKE']}   UKJENT {counts['UKJENT']}   "
          f"(av {len(rows)} belop funnet)")
    print("AVVIK er hoy tillit. MISTANKE er heuristikk med kjent falsk positiv.")
    print("UKJENT betyr at registeret ikke dekker tallet, ikke at tallet er feil.")
    outp = os.path.join(ROOT, f"check_{re.sub(r'[^A-Za-z0-9]', '_', ref)}.json")
    json.dump({"ref": ref, "counts": counts, "rows": rows, "utelatt": excl}, open(outp, "w"),
              indent=1, ensure_ascii=False, default=str)
    print(f"skrevet {os.path.basename(outp)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
